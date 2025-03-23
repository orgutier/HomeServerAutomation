from flask import Flask, Response
from picamera2 import Picamera2
import io
import time
import logging

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
    """Generate JPEG frames sustainably for indefinite runtime."""
    stream = io.BytesIO()
    frame_counter = 0
    last_log_time = time.time()

    while True:
        try:
            # Capture directly to JPEG in memory
            stream.seek(0)
            camera.capture_file(stream, format='jpeg')  # Hardware-accelerated JPEG
            jpeg_data = stream.getvalue()
            frame_size = len(jpeg_data)

            # Yield frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data + b'\r\n')

            # Reset stream to prevent memory growth
            stream.seek(0)
            stream.truncate(0)

            # Periodic logging to monitor health
            frame_counter += 1
            current_time = time.time()
            if current_time - last_log_time >= 60:  # Log every minute
                logger.info(f"Sent {frame_counter} frames, last frame size: {frame_size} bytes")
                frame_counter = 0
                last_log_time = current_time

        except Exception as e:
            logger.error(f"Error in frame generation: {e}")
            # Attempt to recover by restarting capture
            time.sleep(1)  # Brief pause to avoid tight loop
            continue

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
        app.run(host='127.0.0.1', port=5000, threaded=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Server crashed: {e}")
    finally:
        camera.stop()
        logger.info("Camera stopped, server shutting down")