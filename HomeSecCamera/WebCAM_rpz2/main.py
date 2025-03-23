from flask import Flask, Response, request, abort, jsonify
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from picamera2 import Picamera2
from cryptography.fernet import Fernet
import io

app = Flask(__name__)

# Configuration
TEMP_IMAGE_PATH = "/tmp/camera_image.jpg"  # Only used as fallback
SECRET_KEY = "your-secret-key-here"
USERNAME = "admin"
PASSWORD_HASH = generate_password_hash("your-strong-password")
# Encryption key (generate once and share with client securely)
ENCRYPTION_KEY = Fernet.generate_key()  # Run once, then hardcode the key
cipher = Fernet(ENCRYPTION_KEY)

# Initialize camera with lower resolution for speed
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

# Function to capture image directly to memory
def capture_image():
    try:
        output = io.BytesIO()
        camera.capture_file(output, format='jpeg')
        output.seek(0)
        return output.read()
    except Exception as e:
        print(f"Error capturing image: {str(e)}")
        return None

# Root route for clarity
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "message": "Welcome to the Raspberry Pi Camera Server",
        "endpoints": {
            "/get-image": "GET - Retrieve encrypted camera image (requires auth)",
            "/health": "GET - Check server status"
        }
    }), 200

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
    # Print encryption key on first run (save it for client)
    print("Encryption Key:", ENCRYPTION_KEY.decode())
    
    try:
        app.run(
            host='0.0.0.0',
            port=5000,
            threaded=True,
            debug=False  # Set to True for more detailed logs if needed
        )
    finally:
        camera.stop()