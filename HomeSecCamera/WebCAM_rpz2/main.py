from flask import Flask, Response
from picamera2 import Picamera2
import io
import numpy as np
from PIL import Image

app = Flask(__name__)

# Initialize the camera
camera = Picamera2()
camera_config = camera.create_video_configuration(main={"size": (1920, 1080)})
camera.configure(camera_config)
camera.start()
print(f"Camera resolution: {camera.capture_metadata()['ScalerCrop']}")

def process_frame(frame):
    """Convert frame to compressed JPEG."""
    img = Image.fromarray(frame).convert('RGB')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=40, optimize=True)  # Tune quality
    buffer.seek(0)
    return buffer.getvalue()

def generate_frames():
    while True:
        frame = camera.capture_array()
        jpeg_data = process_frame(frame)
        print(f"Frame size: {len(jpeg_data)} bytes")
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data + b'\r\n')

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