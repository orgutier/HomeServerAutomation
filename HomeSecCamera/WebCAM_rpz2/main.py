from flask import Flask, send_file, request, abort
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import base64

app = Flask(__name__)

# Configuration
IMAGE_PATH = "/path/to/your/image.jpg"  # Replace with actual image path
SECRET_KEY = "your-secret-key-here"     # Replace with a strong secret key
USERNAME = "admin"
PASSWORD_HASH = generate_password_hash("your-strong-password")  # Replace with your password

# Basic authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != USERNAME or not check_password_hash(PASSWORD_HASH, auth.password):
            abort(401, "Authentication required")
        return f(*args, **kwargs)
    return decorated

# API endpoint to serve the image
@app.route('/get-image', methods=['GET'])
@require_auth
def serve_image():
    try:
        if not os.path.exists(IMAGE_PATH):
            abort(404, "Image not found")
        
        # Determine the MIME type based on file extension
        ext = os.path.splitext(IMAGE_PATH)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif'
        }
        mime_type = mime_types.get(ext, 'application/octet-stream')
        
        return send_file(
            IMAGE_PATH,
            mimetype=mime_type,
            as_attachment=False
        )
    except Exception as e:
        abort(500, f"Server error: {str(e)}")

# Optional: Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return {"status": "ok"}, 200

if __name__ == '__main__':
    # Run with SSL for security (generate self-signed cert if needed)
    ssl_context = ('cert.pem', 'key.pem')  # Replace with your SSL certificates
    
    # For development, you can use 'adhoc' SSL context (not for production)
    # ssl_context = 'adhoc'
    
    app.run(
        host='0.0.0.0',           # Accessible from any IP
        port=5000,               # Default port
        ssl_context=ssl_context, # Enable HTTPS
        threaded=True,           # Handle multiple requests
        debug=False              # Set to False in production
    )