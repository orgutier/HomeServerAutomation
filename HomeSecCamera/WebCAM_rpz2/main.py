import http.server
import socketserver

# Set the port (default is 8000; change if needed)
PORT = 8000

# Define a simple HTML page
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Raspberry Pi LAN Website</title>
</head>
<body>
    <h1>Hello from Raspberry Pi!</h1>
    <p>This is a simple website hosted on your Pi.</p>
</body>
</html>
"""

# Create a custom handler to serve the HTML
class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

# Set up the server
Handler = CustomHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving website at http://{get_ip()}:8000")
    httpd.serve_forever()

# Function to get the Pi's IP address
def get_ip():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip