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
#   hailortcli scan
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
#   hailortcli scan
# - Ensure it is detected as Hailo-8 and not Hailo-8L, as the Hailo-8 provides higher processing power.
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
#       device = hailort.Device("0000:01:00.0")
#       print("Hailo-8 device initialized.")
#   except Exception as e:
#       print(f"Failed to initialize Hailo-8 device: {e}")
#
# Step 3: Confirm Model Initialization
# - Ensure the model path is correct and the model is detected using:
#   try:
#       hef = hailort.HEF("./centerpose_regnetx_1.6gf_fpn.hef")
#       print(f"Model loaded: {hef}")
#   except Exception as e:
#       print(f"Failed to load model: {e}")
#
# Step 4: Debug with Detailed Logs
# - Enable additional logging to capture more details:
#   import logging
#   logging.basicConfig(level=logging.DEBUG)

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
            device = hailort.Device("0000:01:00.0")
            print("Hailo-8 device initialized.")
            hef = hailort.HEF("./centerpose_regnetx_1.6gf_fpn.hef")
            print(f"Model loaded: {hef}")
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
