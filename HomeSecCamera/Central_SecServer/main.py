# Verify if the HEF model exists before checking network groups
            import os
            if not os.path.isfile('./centerpose_regnetx_1.6gf_fpn.hef'):
                raise FileNotFoundError("HEF model file not found at './centerpose_regnetx_1.6gf_fpn.hef'")
            else:
                print("HEF model file detected.")
            
            # Check if network groups are available
            network_groups = device.loaded_network_groups
            if not network_groups:
                print("No network groups available. Proceeding without model.")
            else:
                network_group = network_groups[0]
                print("Hailo-8 network group loaded.")
            network_group = network_groups[0]
            print("Hailo-8 network group loaded.")
            
            print("Hailo-8 setup complete.")
            compute_resource = "Hailo-8"
            accelerator = network_group
        except Exception as e:
            print(f"Hailo-8 setup failed: {e}")
            import traceback
            traceback.print_exc()
            print("Attempting to get more information using hailortcli...")
            import subprocess
            try:
                result = subprocess.run(['hailortcli', 'scan'], capture_output=True, text=True)
                print("Hailortcli Scan Output:")
                print(result.stdout)
                print(result.stderr)
            except Exception as cli_error:
                print(f"Failed to run hailortcli: {cli_error}")

    return compute_resource, accelerator

# Initialize compute resource
compute_resource, accelerator = detect_compute_resource()

# Ensure Hailo-8 is used if available
if compute_resource != "Hailo-8":
    print("Warning: Hailo-8 is not being used. Falling back to CPU.")
    print("Check error logs above for more information.")

# Stream and display video

def get_frames():
    try:
        response = requests.get(url, stream=True)
        for chunk in response.iter_content(chunk_size=8192):
            frame_queue.put(chunk)
    except Exception as e:
        print(f"Error in video stream: {e}")

def display_video():
    buffer = b""
    while True:
        try:
            buffer += frame_queue.get()
            start = buffer.find(b"\xff\xd8")
            end = buffer.find(b"\xff\xd9")
            if start != -1 and end != -1:
                jpg = buffer[start:end + 2]
                buffer = buffer[end + 2:]
                image = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if image is not None:
                    cv2.putText(image, f"Compute: {compute_resource}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    cv2.imshow("Video Stream", image)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except Exception as e:
            print(f"Error displaying frame: {e}")

cv2.destroyAllWindows()
threading.Thread(target=get_frames, daemon=True).start()
display_video()
