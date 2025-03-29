from flask import Flask, Response
from picamera2 import Picamera2, MappedArray
import io
import time
import logging
import numpy as np
import cv2

# Set up logging for debugging crashes
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize the camera
try:
    camera = Picamera2()
    camera_config = camera.create_video_configuration(main={"size": (1920, 1080)}, encode="main")
    camera.configure(camera_config)
    camera.start()
    logger.info(f"Camera started with resolution: {camera.capture_metadata()['ScalerCrop']}")
except Exception as e:
    logger.error(f"Camera initialization failed: {e}")
    raise

def generate_frames():
    frame_counter = 0
    last_log_time = time.time()
    
    while True:
        try:
            # Capture image using hardware acceleration
            frame = camera.capture_array()  # Captures directly as numpy array
            
            # Convert to smaller size with better compression
            resized_frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_AREA)
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]  # Compress with JPEG at 60% quality
            _, jpeg_data = cv2.imencode('.jpg', resized_frame, encode_param)

            # Yield frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data.tobytes() + b'\r\n')

            # Periodic logging to monitor health
            frame_counter += 1
            current_time = time.time()
            if current_time - last_log_time >= 60:
                logger.info(f"Sent {frame_counter} frames, average frame size: {len(jpeg_data)} bytes")
                frame_counter = 0
                last_log_time = current_time

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
