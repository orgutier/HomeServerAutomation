import argparse
from flask import Flask, Response, request, jsonify
from picamera2 import Picamera2
import cv2
import io
import time
import logging
import numpy as np
import psutil
import subprocess

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Start the Raspberry Pi Camera API server.')
parser.add_argument('-h', '--host', type=str, default='127.0.0.1', help='Host IP address (default: 127.0.0.1)')
parser.add_argument('-p', '--port', type=int, default=5000, help='Port number (default: 5000)')
args = parser.parse_args()

# Configuration
CONFIG = {
    "host": args.host,
    "port": args.port,
    "compress": 50,
    "resolution": (1920, 1080)
}

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
camera = Picamera2()
connected_users = []

# Monitor System


def get_cpu_temperature():
    try:
        temp_output = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
        return float(temp_output.replace("temp=", "").replace("'C\n", ""))
    except Exception as e:
        logger.error(f"Error getting CPU temperature: {e}")
        return None

def check_system():
    cpu_usage = psutil.cpu_percent()
    memory_info = psutil.virtual_memory()
    cpu_temp = get_cpu_temperature()

    if cpu_temp and cpu_temp > 80:
        logger.warning(f"High CPU Temperature: {cpu_temp}°C")

    if cpu_usage > 90:
        logger.warning(f"High CPU Usage: {cpu_usage}%")

    if memory_info.percent > 90:
        logger.warning(f"High Memory Usage: {memory_info.percent}%")

    return {
        "cpu_usage": cpu_usage,
        "memory_usage": memory_info.percent,
        "cpu_temperature": cpu_temp
    }

# Camera Setup

def configure_camera(mode='video', compress=50, resolution=(1920, 1080)):
    try:
        if mode == 'video':
            config = camera.create_video_configuration(main={'size': resolution}, encode='main')
        else:
            config = camera.create_still_configuration(main={'size': resolution})
        
        camera.configure(config)
        camera.set_controls({"FrameRate": 50})
        camera.start()
        logger.info(f"Camera configured for {mode} at {resolution} with {compress}% compression")
    except Exception as e:
        logger.error(f"Failed to configure camera: {e}")

# API Endpoints

@app.route('/get_video')
def get_video():
    compress = int(request.args.get('compress', CONFIG['compress']))
    resolution = tuple(map(int, request.args.get('resolution', '1920,1080').split(',')))
    configure_camera('video', compress, resolution)

    def generate_frames():
        while True:
            frame = camera.capture_array()
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), compress]
            _, jpeg_data = cv2.imencode('.jpg', frame, encode_param)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data.tobytes() + b'\r\n')
    
    connected_users.append(request.remote_addr)
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_photo')
def get_photo():
    compress = int(request.args.get('compress', 100))
    resolution_str = request.args.get('resolution', 'max')
    
    if resolution_str == 'max':
        resolution = camera.sensor_modes[0]['size']
    else:
        resolution = tuple(map(int, resolution_str.split(',')))
    
    configure_camera('photo', compress, resolution)
    frame = camera.capture_array()
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), compress]
    _, jpeg_data = cv2.imencode('.jpg', frame, encode_param)
    return Response(jpeg_data.tobytes(), content_type='image/jpeg')

@app.route('/get_status')
def get_status():
    status = check_system()
    return jsonify(status)

@app.route('/get_users')
def get_users():
    return jsonify({"connected_users": connected_users})

if __name__ == '__main__':
    try:
        logger.info(f"Starting Flask server on {CONFIG['host']}:{CONFIG['port']}...")
        app.run(host=CONFIG['host'], port=CONFIG['port'], threaded=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Server crashed: {e}")
    finally:
        camera.stop()
        logger.info("Camera stopped, server shutting down")
