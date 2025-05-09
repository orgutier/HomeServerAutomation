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
parser.add_argument('--host', type=str, default='127.0.0.1', help='Host IP address (default: 127.0.0.1)')
parser.add_argument('-p', '--port', type=int, default=5000, help='Port number (default: 5000)')
args = parser.parse_args()

# Configuration
CONFIG = {
    "host": args.host,
    "port": args.port,
    "compress": 50,
    "resolution": (1920, 1080),
    "max_temp": 85, # Max temperature in Celsius
    "high_usage_threshold": 90 # CPU or memory usage percentage
}

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
camera = Picamera2()
connected_users = []
current_mode = None

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

    if cpu_temp and cpu_temp > CONFIG['max_temp']:
        logger.error(f"Critical: CPU Temperature exceeded {CONFIG['max_temp']}°C. Stopping camera.")
        camera.stop()
        return {"error": "CPU Overheated. Camera has been stopped."}

    if cpu_usage > CONFIG['high_usage_threshold'] or memory_info.percent > CONFIG['high_usage_threshold']:
        logger.warning(f"High resource usage detected: CPU {cpu_usage}% / Memory {memory_info.percent}%")

    return {
        "cpu_usage": cpu_usage,
        "memory_usage": memory_info.percent,
        "cpu_temperature": cpu_temp
    }

# Camera Setup

def configure_camera(mode='video', compress=50, resolution=(1920, 1080)):
    global current_mode

    if current_mode == mode:
        logger.info(f"Camera is already in {mode} mode.")
        return

    try:
        camera.stop()
        if mode == 'video':
            config = camera.create_video_configuration(main={'size': resolution}, encode='main')
        else:
            config = camera.create_still_configuration(main={'size': resolution})
        
        camera.configure(config)
        camera.set_controls({"FrameRate": 30}) # Lower FPS to prevent crashes
        camera.start()
        current_mode = mode
        logger.info(f"Camera reconfigured to {mode} at {resolution} with {compress}% compression")
    except Exception as e:
        logger.error(f"Failed to configure camera: {e}")

# API Endpoints

@app.route('/get_video')
def get_video():
    global current_mode
    if current_mode == 'photo':
        return "Cannot start video while photo mode is active. Stop photo mode first.", 400

    system_status = check_system()
    if 'error' in system_status:
        return jsonify(system_status), 500

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
    global current_mode
    if current_mode == 'video':
        return "Cannot take photo while video mode is active. Stop video mode first.", 400

    system_status = check_system()
    if 'error' in system_status:
        return jsonify(system_status), 500

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
