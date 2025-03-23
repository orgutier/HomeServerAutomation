from flask import Flask, Response, request
from picamera2 import Picamera2
import time
import io
import numpy as np
from PIL import Image

app = Flask(__name__)

# Initialize the camera
camera = Picamera2()
camera_config = camera.create_video_configuration(main={"size": (640, 480)})
camera.configure(camera_config)
camera.start()

# Global variable to track mode
current_mode = "infrared"  # Default to infrared

def process_frame(frame, mode):
    """Process the frame based on the mode."""
    img = Image.fromarray(frame).convert('RGB')
    
    if mode == "normal":
        img_array = np.array(img)
        img_array[:,:,0] = np.clip(img_array[:,:,0] * 0.8, 0, 255)  # Reduce red
        img_array[:,:,1] = np.clip(img_array[:,:,1] * 1.1, 0, 255)  # Boost green
        img = Image.fromarray(img_array)
    
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.getvalue()

def generate_frames():
    global current_mode
    while True:
        frame = camera.capture_array()
        jpeg_data = process_frame(frame, current_mode)
        print(f"Generated frame of {len(jpeg_data)} bytes")  # Debug output
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data + b'\r\n')
        time.sleep(0.1)  # 10 FPS

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html><head><title>Raspberry Pi Infrared Camera Stream</title></head>
    <body><h1>Infrared Camera Stream</h1><img src="/video_feed" width="640" height="480"></body>
    </html>
    """

@app.route('/video_feed')
def video_feed():
    print("Client connected to /video_feed")  # Debug output
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/set_mode', methods=['POST'])
def set_mode():
    global current_mode
    data = request.get_json()
    if data and 'mode' in data:
        current_mode = data['mode']
    return '', 204

if __name__ == '__main__':
    try:
        app.run(host='127.0.0.1', port=5000, threaded=True)
    finally:
        camera.stop()