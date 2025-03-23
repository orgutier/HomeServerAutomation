from flask import Flask, Response
from picamera2 import Picamera2
import time
import io

app = Flask(__name__)

# Initialize the camera
camera = Picamera2()
camera_config = camera.create_video_configuration(main={"size": (640, 480)})  # Lower res for speed
camera.configure(camera_config)
camera.start()

def generate_frames():
    while True:
        # Capture frame as a numpy array (raw data)
        frame = camera.capture_array()
        
        # Convert to JPEG in memory
        buffer = io.BytesIO()
        camera.capture_file(buffer, format='jpeg')  # Use capture_file to encode to JPEG
        buffer.seek(0)
        jpeg_data = buffer.getvalue()
        
        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data + b'\r\n')
        
        time.sleep(0.1)  # 10 FPS, adjust as needed

@app.route('/')
def index():
    # Simple HTML page to display the video stream
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Raspberry Pi Infrared Camera Stream</title></head>
    <body>
        <h1>Infrared Camera Stream</h1>
        <img src="/video_feed" width="640" height="480">
    </body>
    </html>
    """

@app.route('/video_feed')
def video_feed():
    # Stream the MJPEG video
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True)
    finally:
        camera.stop()  # Ensure camera stops when script exits