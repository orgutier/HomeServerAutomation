import requests
import cv2
import numpy as np
import time
import threading
import queue

try:
    import hailort
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False

try:
    from openvino.runtime import Core
    OPENVINO_AVAILABLE = True
except ImportError:
    OPENVINO_AVAILABLE = False

LOCAL_PORT = 5001  # Your SSH tunnel port
url = f"http://localhost:{LOCAL_PORT}/video_feed"

frame_queue = queue.Queue(maxsize=10)

# Detect compute resource
def detect_compute_resource():
    compute_resource = "CPU"  # Default fallback
    accelerator = None

    # Check for Hailo-8
    if HAILO_AVAILABLE:
        try:
            device = hailort.get_default_device()
            hef = hailort.HEF("/path/to/retinaface_mobilnet_v1.hef")  # Adjust path
            network_group = hef.configure(device)[0]
            vstream_info = hef.get_input_vstream_infos()[0]
            input_shape = (vstream_info.shape.height, vstream_info.shape.width, 3)
            infer_context = device.create_infer_context(network_group)
            input_vstream = infer_context.get_input_vstream(vstream_info.name)
            output_vstream = infer_context.get_output_vstreams()[0]
            compute_resource = "Hailo-8"
            accelerator = (infer_context, input_vstream, output_vstream, input_shape)
            print("Using Hailo-8 for face detection")
        except Exception as e:
            print(f"Hailo-8 setup failed: {e}")

    # Check for NPU (e.g., Intel NPU via OpenVINO)
    if compute_resource == "CPU" and OPENVINO_AVAILABLE:
        try:
            ie = Core()
            devices = ie.available_devices
            if "NPU" in devices:
                model = ie.read_model("/path/to/face-detection-retail-0004.xml")  # Adjust path
                compiled_model = ie.compile_model(model, "NPU")
                compute_resource = "NPU"
                accelerator = compiled_model
                print("Using NPU for face detection")
        except Exception as e:
            print(f"NPU setup failed: {e}")

    # Check for GPU (via OpenCV CUDA)
    if compute_resource == "CPU":
        try:
            if cv2.cuda.getCudaEnabledDeviceCount() > 0:
                compute_resource = "GPU"
                net = cv2.dnn.readNetFromONNX("/path/to/face-detection.onnx")  # Adjust path
                net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                accelerator = net
                print("Using GPU for face detection")
        except Exception as e:
            print(f"GPU setup failed: {e}")

    # CPU fallback with Haar Cascade
    if compute_resource == "CPU":
        try:
            face_cascade = cv2.CascadeClassifier('lbpcascade_frontalface.xml')
            if not face_cascade.empty():
                accelerator = face_cascade
                print("Using CPU with Haar Cascade for face detection")
            else:
                print("Haar Cascade not found, skipping face detection")
                accelerator = None
        except Exception as e:
            print(f"CPU Haar setup failed: {e}, skipping face detection")
            accelerator = None

    return compute_resource, accelerator

# Initialize compute resource
compute_resource, accelerator = detect_compute_resource()

# Video Fetching Thread
def fetch_frames():
    print(f"Connecting to {url}...")
    try:
        response = requests.get(url, stream=True, timeout=5)
        response.raise_for_status()
        print("Connected to stream.")
    except requests.RequestException as e:
        print(f"Connection failed: {e}")
        return

    bytes_data = bytes()
    while True:
        try:
            chunk = response.raw.read(8192)
            if not chunk:
                break
            bytes_data += chunk

            header_end = bytes_data.find(b'\r\n\r\n')
            frame_end = bytes_data.find(b'--frame', header_end)

            if header_end != -1 and frame_end != -1:
                jpg = bytes_data[header_end + 4:frame_end]
                img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is not None and img.size > 0:
                    if not frame_queue.full():
                        frame_queue.put(img)
                bytes_data = bytes_data[frame_end:]
        except Exception as e:
            print(f"Error fetching frames: {e}")

# Callback to close window using button
def close_window(*args):
    print("Close button pressed. Exiting...")
    cv2.destroyAllWindows()
    exit(0)

cv2.namedWindow("Camera Feed", cv2.WINDOW_AUTOSIZE)


# Frame Processing Thread
def process_frames():
    prev_time = time.time()
    frame_count = 0
    fps = 0

    while True:
        try:
            if frame_queue.empty():
                time.sleep(0.01)
                continue

            img = frame_queue.get()
            start_calc_time = time.time()

            # Perform face detection
            if compute_resource == "CPU" and accelerator:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = accelerator.detectMultiScale(gray, 1.1, 4)
                for (x, y, w, h) in faces:
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

            calc_fps = 1 / (time.time() - start_calc_time)

            # Display FPS
            frame_count += 1
            curr_time = time.time()
            if curr_time - prev_time >= 1.0:
                fps = frame_count / (curr_time - prev_time)
                frame_count = 0
                prev_time = curr_time

            cv2.putText(img, f"FPS: {fps:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(img, f"Press 'Q' to Quit", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(img, f"Calc FPS: {calc_fps:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.imshow("Camera Feed", img)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        except Exception as e:
            print(f"Error during frame processing: {e}")

# Start Threads
threading.Thread(target=fetch_frames, daemon=True).start()
process_frames()
cv2.destroyAllWindows()
