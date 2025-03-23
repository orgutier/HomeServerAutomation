from flask import Flask, Response
from picamera2 import Picamera2
import time

app = Flask(__name__)

# Initialize the camera
camera = Picamera2()
camera_config = camera.create_video_configuration(main={"size": (640, 480)})  # Lower res for speed
camera.configure(camera_config)
camera.start()

def generate_frames():
    while True:
        # Capture frame as JPEG
        frame = camera.capture_array()
        # Convert to JPEG bytes
        _, buffer = camera.capture_buffer("jpeg")
        # Yield frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer + b'\r\n')
        time.sleep(0.1)  # Adjust delay for frame rate (10 FPS here)

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
    # Run the server on all interfaces, port 5000
    app.run(host='0.0.0.0', port=5000, threaded=True)