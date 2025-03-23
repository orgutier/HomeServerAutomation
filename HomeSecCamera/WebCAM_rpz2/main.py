from flask import Flask, send_file, request, abort
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import io
from picamera2 import Picamera2  # Updated for latest Raspberry Pi camera support
import time

app = Flask(__name__)

# Configuration
TEMP_IMAGE_PATH = "/tmp/camera_image.jpg"  # Temporary storage for captured image
SECRET_KEY = "your-secret-key-here"       # Replace with a strong secret key
USERNAME = "admin"
PASSWORD_HASH = generate_password_hash("your-strong-password")  # Replace with your password

# Initialize camera
camera = Picamera2()
camera_config = camera.create_still_configuration()
camera.configure(camera_config)
camera.start()

# Basic authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != USERNAME or not check_password_hash(PASSWORD_HASH, auth.password):
            abort(401, "Authentication required")
        return f(*args, **kwargs)
    return decorated

# Function to capture fresh image
def capture_image():
    try:
        # Capture image to temporary file
        camera.capture_file(TEMP_IMAGE_PATH)
        time.sleep(0.1)  # Small delay to ensure file is written
        return True
    except Exception as e:
        print(f"Error capturing image: {str(e)}")
        return False

# API endpoint to serve the latest camera image
@app.route('/get-image', methods=['GET'])
@require_auth
def serve_image():
    try:
        # Capture fresh image
        if not capture_image():
            abort(500, "Failed to capture image from camera")
        
        if not os.path.exists(TEMP_IMAGE_PATH):
            abort(404, "Image capture failed")
        
        # Serve the image directly from file
        return send_file(
            TEMP_IMAGE_PATH,
            mimetype='image/jpeg',
            as_attachment=False
        )
    except Exception as e:
        abort(500, f"Server error: {str(e)}")
    finally:
        # Clean up temporary file
        if os.path.exists(TEMP_IMAGE_PATH):
            os.remove(TEMP_IMAGE_PATH)

# Optional: Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "ok"}, 200

if __name__ == '__main__':
    # Ensure tmp directory exists
    os.makedirs(os.path.dirname(TEMP_IMAGE_PATH), exist_ok=True)
    
    # Run with SSL for security
    ssl_context = ('cert.pem', 'key.pem')  # Replace with your SSL certificates
    
    # For development, you can use 'adhoc' SSL context (not for production)
    # ssl_context = 'adhoc'
    
    try:
        app.run(
            host='0.0.0.0',           # Accessible from any IP
            port=5000,               # Default port
            ssl_context=ssl_context, # Enable HTTPS
            threaded=True,           # Handle multiple requests
            debug=False              # Set to False in production
        )
    finally:
        # Cleanup on shutdown
        camera.stop()
        if os.path.exists(TEMP_IMAGE_PATH):
            os.remove(TEMP_IMAGE_PATH)