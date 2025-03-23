from flask import Flask, send_from_directory
import os

app = Flask(__name__)

IMAGE_DIR = "static"
IMAGE_NAME = "photo.jpg"  # Change this to your image file name

@app.route("/")
def index():
    return f'<img src="/image" style="max-width:100%; height:auto;">'

@app.route("/image")
def serve_image():
    return send_from_directory(IMAGE_DIR, IMAGE_NAME)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
