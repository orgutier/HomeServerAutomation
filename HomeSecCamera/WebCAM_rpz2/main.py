import requests
import cv2
import numpy as np
import time
try:
    import hailort
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False

LOCAL_PORT = 5001  # Your SSH tunnel port
url = f"http://localhost:{LOCAL_PORT}/video_feed"

# Hailo-8 setup
USE_HAILO = False
if HAILO_AVAILABLE:
    try:
        device = hailort.get_default_device()
        hef = hailort.HEF("/path/to/retinaface_mobilnet_v1.hef")  # Adjust path
        network_group = hef.configure(device)[0]
        vstream_info = hef.get_input_vstream_infos()[0]
        input_shape = (vstream_info.shape.height, vstream_info.shape.width, 3)  # e.g., 256x256
        infer_context = device.create_infer_context(network_group)
        input_vstream = infer_context.get_input_vstream(vstream_info.name)
        output_vstream = infer_context.get_output_vstreams()[0]
        USE_HAILO = True
        print("Using Hailo-8 for face detection")
    except Exception as e:
        print(f"Hailo-8 setup failed: {e}, falling back to CPU")

# CPU fallback
USE_HAAR = False
if not USE_HAILO:
    try:
        face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        if not face_cascade.empty():
            USE_HAAR = True
            print("Using CPU with Haar Cascade")
        else:
            print("Haar Cascade not found, skipping face detection")
    except Exception as e:
        print(f"Haar setup failed: {e}, skipping face detection")

# Connect to stream
print(f"Connecting to {url}...")
try:
    response = requests.get(url, stream=True, timeout=5)
    response.raise_for_status()
    print("Connected to stream.")
except requests.RequestException as e:
    print(f"Connection failed: {e}")
    exit(1)

# FPS tracking
prev_time = time.time()
frame_count = 0
fps = 0
max_tops = 26.0  # Hailo-8 max TOPS

bytes_data = bytes()
while True:
    chunk = response.raw.read(8192)
    if not chunk:
        break
    bytes_data += chunk

    header_end = bytes_data.find(b'\r\n\r\n')
    frame_end = bytes_data.find(b'--frame', header_end)

    if header_end != -1 and frame_end != -1:
        jpg = bytes_data[header_end + 4:frame_end]
        if len(jpg) > 0:
            img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                # Face detection
                if USE_HAILO:
                    hailo_input = cv2.resize(img, (input_shape[1], input_shape[0])).astype(np.float32) / 255.0
                    input_vstream.write(hailo_input.tobytes())
                    infer_context.run()
                    detections = output_vstream.read()
                    scale_x = 1920 / input_shape[1]
                    scale_y = 1080 / input_shape[0]
                    for i in range(0, len(detections), 15):  # Adjust stride
                        conf = detections[i + 4]
                        if conf > 0.5:
                            x1, y1, x2, y2 = map(int, [detections[i+j] * (scale_x if j % 2 == 0 else scale_y) for j in range(4)])
                            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                elif USE_HAAR:
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                    for (x, y, w, h) in faces:
                        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # FPS calculation
                frame_count += 1
                curr_time = time.time()
                if curr_time - prev_time >= 1.0:
                    fps = frame_count / (curr_time - prev_time)
                    frame_count = 0
                    prev_time = curr_time

                # Neural usage (simulated)
                neural_usage = min((fps / (50 if USE_HAILO else 20)) * 100, 100)

                # Overlay info
                cv2.putText(img, f"FPS: {fps:.1f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(img, f"Neural: {neural_usage:.1f}%", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                cv2.imshow("Camera Feed", img)
            else:
                print("Failed to decode frame")
        bytes_data = bytes_data[frame_end:]

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
response.close()