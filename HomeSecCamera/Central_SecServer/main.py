# Hailo-8 Configuration Guide
# Follow these steps to configure and use the Hailo-8 on your Raspberry Pi:
#
# Step 1: Install Hailo SDK
# - Direct link to download: https://hailo.ai/developer-zone/software-downloads/
# - Go to https://hailo.ai/ and download the Hailo SDK for Raspberry Pi.
# - Transfer the downloaded SDK to the Raspberry Pi using scp or a USB drive.
# - Install the SDK using the following command:
#   sudo dpkg -i hailo*.deb
#
# Step 2: Install Required Packages
# - Update your package list and install necessary dependencies:
#   sudo apt-get update
#   sudo apt-get install -y python3-pip libopencv-dev
#
# Step 3: Install Python Libraries
# - Ensure the Hailo Python runtime (hailo_platform) is installed:
#   pip3 install hailo_platform
#
# Step 4: Verify Hailo-8 Detection
# - Confirm that Hailo-8 is detected using:
#   hailortcli scan
#
# Troubleshooting Steps
# If Hailo-8 is not being used and you see the error "Warning: Hailo-8 is not being used. Falling back to CPU.":
#
# Step 1: Confirm Device Detection
# - Ensure the device is detected using:
#   hailortcli scan
#
# Step 2: Verify Device Initialization in the Code
# - Add error logging to check if the device is accessible:
#   try:
#       device = hailo_platform.Device()
#       print("Hailo-8 device initialized using hailo_platform.")
#   except Exception as e:
#       print(f"Failed to initialize Hailo-8 device: {e}")

import requests
import cv2
import numpy as np
import time
import threading
import queue

try:
    import hailo_platform as hailort
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
            device = hailort.Device()
            print("Hailo-8 device initialized.")
            hef = hailort.HEF("./centerpose_regnetx_1.6gf_fpn.hef")
            print(f"Model loaded: {hef}")
            # Load the HEF model onto the device using the control method
            print("Loading model to Hailo-8...")
            device.control('load_network', str(hef))
            print("Model loaded to device.")
            
            # Access the network group
            network_groups = device.loaded_network_groups
            if not network_groups:
                raise RuntimeError("Failed to load network group. Ensure the model is valid and compatible with Hailo-8.")
            network_group = network_groups[0]
            print("Hailo-8 network group loaded.")
            print("Hailo-8 network group loaded.")
            print("Activating network group...")
            network_group.control('activate')
            print("Hailo-8 network group activated.")
            compute_resource = "Hailo-8"
            accelerator = network_group
        except Exception as e:
            print(f"Hailo-8 setup failed: {e}")
            import traceback
            traceback.print_exc()
            print("Attempting to get more information using hailortcli...")
            import subprocess
            try:
                result = subprocess.run(['hailortcli', 'scan'], capture_output=True, text=True)
                print("Hailortcli Scan Output:")
                print(result.stdout)
                print(result.stderr)
            except Exception as cli_error:
                print(f"Failed to run hailortcli: {cli_error}")
            import traceback
            traceback.print_exc()

    return compute_resource, accelerator

# Initialize compute resource
compute_resource, accelerator = detect_compute_resource()

# Ensure Hailo-8 is used if available
if compute_resource != "Hailo-8":
    print("Warning: Hailo-8 is not being used. Falling back to CPU.")
    print("Check error logs above for more information.")

# Stream and display video

def get_frames():
    try:
        response = requests.get(url, stream=True)
        for chunk in response.iter_content(chunk_size=8192):
            frame_queue.put(chunk)
    except Exception as e:
        print(f"Error in video stream: {e}")

def display_video():
    buffer = b""
    while True:
        try:
            buffer += frame_queue.get()
            start = buffer.find(b"\xff\xd8")
            end = buffer.find(b"\xff\xd9")
            if start != -1 and end != -1:
                jpg = buffer[start:end + 2]
                buffer = buffer[end + 2:]
                image = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if image is not None:
                    cv2.putText(image, f"Compute: {compute_resource}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow("Video Stream", image)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except Exception as e:
            print(f"Error displaying frame: {e}")

cv2.destroyAllWindows()
threading.Thread(target=get_frames, daemon=True).start()
display_video()
