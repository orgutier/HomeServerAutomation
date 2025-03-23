from flask import Flask, Response, request, abort, jsonify, send_from_directory
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from picamera2 import Picamera2
from cryptography.fernet import Fernet
import io

app = Flask(__name__)

# Configuration
SECRET_KEY = "your-secret-key-here"
USERNAME = "admin"
PASSWORD_HASH = generate_password_hash("your-strong-password")
ENCRYPTION_KEY = Fernet.generate_key()  # Save this for client
cipher = Fernet(ENCRYPTION_KEY)

# Initialize camera
camera = Picamera2()
camera_config = camera.create_still_configuration(main={"size": (640, 480)})
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

# Function to capture image
def capture_image():
    try:
        output = io.BytesIO()
        camera.capture_file(output, format='jpeg')
        output.seek(0)
        return output.read()
    except Exception as e:
        print(f"Error capturing image: {str(e)}")
        return None

# Serve the HTML viewer
@app.route('/', methods=['GET'])
def root():
    return send_from_directory('.', 'viewer.html')

# API endpoint to serve encrypted image
@app.route('/get-image', methods=['GET'])
@require_auth
def serve_image():
    try:
        image_data = capture_image()
        if image_data is None:
            abort(500, "Failed to capture image from camera")
        
        encrypted_data = cipher.encrypt(image_data)
        return Response(
            encrypted_data,
            mimetype='application/octet-stream',
            headers={'X-Encrypted': 'true'}
        )
    except Exception as e:
        abort(500, f"Server error: {str(e)}")

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "ok"}, 200

if __name__ == '__main__':
    print("Encryption Key:", ENCRYPTION_KEY.decode())
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            threaded=True,
            debug=False
        )
    finally:
        camera.stop()