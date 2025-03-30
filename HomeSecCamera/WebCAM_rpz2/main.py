from flask import Flask, Response
from picamera2 import Picamera2, MappedArray
import io
import time
import logging
import numpy as np
import cv2

# Optional: Install psutil for memory management
# sudo apt-get install python3-psutil
import psutil

# Set up logging for debugging crashes
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable swap memory to prevent memory errors on Raspberry Pi Zero 2
# sudo dphys-swapfile swapoff
# sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=1024 or higher (e.g., 2048 for 2GB)
# sudo dphys-swapfile setup
# sudo dphys-swapfile swapon

# Monitor memory and CPU usage using htop
# sudo apt-get install htop
# htop

# Initialize the camera for still image capture at 1 FPS with wide view
try:
    camera = Picamera2()
    camera_config = camera.create_still_configuration(main={'size': (4608, 2592)})
    camera.configure(camera_config)

    # Set frame rate using set_controls
    camera.set_controls({"FrameRate": 1})

    camera.start()
    logger.info(f"Camera started with resolution: {camera_config['main']['size']}")
except Exception as e:
    logger.error(f"Camera initialization failed: {e}")
    raise

def check_memory():
    memory_info = psutil.virtual_memory()
    if memory_info.percent > 90:
        logger.warning(f"High memory usage detected: {memory_info.percent}%")
        return True
    return False

def generate_frames():
    while True:
        try:
            # Capture image directly into memory
            frame = camera.capture_array()

            # Compress the image to JPEG format in memory
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]  # Adjust quality as needed
            _, jpeg_data = cv2.imencode('.jpg', frame, encode_param)

            # Yield the frame to the web client
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data.tobytes() + b'\r\n')

            # Check memory usage
            if check_memory():
                logger.warning("High memory usage detected.")

            # Wait for 1 second before capturing the next frame
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error in frame generation: {e}")
            time.sleep(1)  # Pause to prevent excessive errors

@app.route('/')
def index():
    return "<h1>Camera Stream</h1><img src='/video_feed'>"

@app.route('/video_feed')
def video_feed():
    try:
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        logger.error(f"Video feed error: {e}")
        return Response(status=500)

if __name__ == '__main__':
    try:
        logger.info("Starting Flask server...")
        app.run(host='0.0.0.0', port=5000, threaded=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Server crashed: {e}")
    finally:
        camera.stop()
        logger.info("Camera stopped, server shutting down")
