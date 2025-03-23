from flask import Flask, Response
from picamera2 import Picamera2
import io

app = Flask(__name__)

# Initialize the camera
camera = Picamera2()
camera_config = camera.create_video_configuration(main={"size": (1920, 1080)}, encode="main")
camera.configure(camera_config)
camera.start()
print(f"Camera resolution: {camera.capture_metadata()['ScalerCrop']}")

def generate_frames():
    """Generate JPEG frames as fast as possible using hardware encoding."""
    stream = io.BytesIO()
    while True:
        # Capture directly to JPEG in memory
        stream.seek(0)
        camera.capture_file(stream, format='jpeg', quality=40)  # Hardware-accelerated JPEG
        jpeg_data = stream.getvalue()
        print(f"Frame size: {len(jpeg_data)} bytes")  # Debug
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data + b'\r\n')
        stream.seek(0)  # Reset for next frame
        stream.truncate()  # Clear buffer

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