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
# - Ensure the Hailo Python runtime (hailort) is installed:
#   pip3 install hailort
#
# Step 4: Verify Hailo-8 Detection
# - Confirm that Hailo-8 is detected using:
#   hailort-cli device-info
# - If hailort-cli is not found, follow these steps:
#   1. Check if the SDK is installed correctly:
#      ls /usr/local/bin/hailort-cli
#   2. Ensure the path is available in your environment:
#      echo $PATH
#   3. Add it to the path if not present:
#      export PATH=$PATH:/usr/local/bin
#   4. To make this permanent, add to ~/.bashrc or ~/.profile:
#      echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc
#      source ~/.bashrc
#   5. Check for other commands:
#      hailo-cli, hailoctl, or hailo --help
#   6. If none of the above work, reinstall the SDK:
#      sudo dpkg -i /path/to/hailo*.deb
#      sudo apt-get install -f
# - Confirm that Hailo-8 is detected using:
#   hailort-cli device-info
# - Ensure it is detected as Hailo-8 and not Hailo-8L, as the Hailo-8 provides higher processing power.

# - Confirm that Hailo-8 is detected using:
#   hailort-cli device-info
#
# Step 5: Install or Convert Models
# - Download precompiled Hailo models or convert existing ONNX models to .hef format using:
#   hailo_model_compiler -i model.onnx -o model.hef
#
# Step 6: Update Model Path
# - Update the path in the code to the correct .hef model file:
#   hef = hailort.HEF("/path/to/retinaface_mobilnet_v1.hef")
#
# Step 7: Run the Operation Server
# - Run the code using:
#   python3 main.py
#
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
            hef = hailort.HEF("/path/to/retinaface_mobilnet_v1.hef")
            network_group = hef.configure(device)[0]
            vstream_info = network_group.get_input_vstream_infos()[0]
            input_shape = (vstream_info.shape.height, vstream_info.shape.width, 3)
            infer_context = device.create_infer_context(network_group)
            input_vstream = infer_context.get_input_vstream(vstream_info.name)
            output_vstream = infer_context.get_output_vstreams()[0]
            compute_resource = "Hailo-8"
            accelerator = (infer_context, input_vstream, output_vstream, input_shape)
            print("Using Hailo-8 for face detection")
        except Exception as e:
            print(f"Hailo-8 setup failed: {e}")

    return compute_resource, accelerator

# Initialize compute resource
compute_resource, accelerator = detect_compute_resource()

# Ensure Hailo-8 is used if available
if compute_resource != "Hailo-8":
    print("Warning: Hailo-8 is not being used. Falling back to CPU.")
