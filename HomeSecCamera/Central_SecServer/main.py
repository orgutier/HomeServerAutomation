import requests
import cv2
import numpy as np

LOCAL_PORT = 5001  # Adjust if your tunnel uses a different port
url = f"http://localhost:{LOCAL_PORT}/video_feed"

print(f"Connecting to {url}...")
response = requests.get(url, stream=True, timeout=10)
response.raise_for_status()
print("Connected successfully.")

bytes_data = bytes()
for chunk in response.iter_content(chunk_size=4096):
    bytes_data += chunk
    print(f"Buffer size: {len(bytes_data)} bytes")

    # Find frame boundaries
    header_end = bytes_data.find(b'\r\n\r\n')
    frame_end = bytes_data.find(b'--frame', header_end)

    if header_end != -1 and frame_end != -1:
        jpg_start = header_end + 4
        jpg = bytes_data[jpg_start:frame_end]
        print(f"Extracted frame: {len(jpg)} bytes")

        if len(jpg) > 0:
            img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                cv2.imshow("Camera Feed", img)
                print("Frame displayed")
            else:
                print("Failed to decode frame")
                # Show placeholder
                img = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(img, "Decode Failed", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                cv2.imshow("Camera Feed", img)
        bytes_data = bytes_data[frame_end:]

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
response.close()