from flask import Flask, Response
from picamera2 import Picamera2
import time
import io
import numpy as np
from PIL import Image

app = Flask(__name__)

# Initialize the camera with maximum video resolution
camera = Picamera2()
camera_config = camera.create_video_configuration(main={"size": (1920, 1080)})  # Full HD
camera.configure(camera_config)
camera.start()
print(f"Camera resolution set to: {camera.capture_metadata()['ScalerCrop']}")

def process_frame(frame):
    """Convert frame to JPEG."""
    img = Image.fromarray(frame).convert('RGB')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)  # Adjust quality for bandwidth
    buffer.seek(0)
    return buffer.getvalue()

def generate_frames():
    while True:
        frame = camera.capture_array()
        jpeg_data = process_frame(frame)
        print(f"Frame size: {len(jpeg_data)} bytes")  # Debug
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data + b'\r\n')
        time.sleep(0.1)  # Keep 10 FPS target, though may slow down

@app.route('/')
def index():
    return "<h1>Camera Stream</h1><img src='/video_feed'>"

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    try:
        app.run(host='127.0.0.1', port=5000, threaded=True)
    finally:
        camera.stop()