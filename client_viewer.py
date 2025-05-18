import cv2
import paho.mqtt.client as mqtt
import requests
import json
import threading
import argparse

# ========== MQTT CALLBACK ==========
def on_connect(client, userdata, flags, rc):
    print("[MQTT] Connected with result code ", rc)
    topic = f"events/{userdata['cam_id']}/person"
    client.subscribe(topic)
    print(f"[MQTT] Subscribed to topic: {topic}")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"[MQTT] {msg.topic} → {payload}")

# ========== VIDEO VIEWER FUNCTION ==========
def view_stream(url):
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        print("[ERROR] Cannot open video stream")
        return

    print("[INFO] Press 'q' to quit the stream window.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow("Stream Viewer", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()

# ========== MAIN LAUNCHER ==========
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cam_id", default="cam_hp", help="Camera ID")
    parser.add_argument("--source", default="0", help="Camera source (int or rtsp URL)")
    parser.add_argument("--mode", choices=["mjpeg", "rtsp"], default="mjpeg")
    args = parser.parse_args()

    # Start stream via API
    payload = {"id": args.cam_id, "url": int(args.source) if args.source.isdigit() else args.source}
    try:
        res = requests.post("http://localhost:8000/stream/start", json=payload)
        print("[API]", res.json())
    except Exception as e:
        print("[ERROR] Could not start stream via API:", e)

    # MQTT Setup
    mqtt_client = mqtt.Client(userdata={"cam_id": args.cam_id})
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect("localhost", 1883, 60)

    mqtt_thread = threading.Thread(target=mqtt_client.loop_forever)
    mqtt_thread.daemon = True
    mqtt_thread.start()

    # Stream Viewer
    if args.mode == "mjpeg":
        view_stream(f"http://localhost:8000/video/{args.cam_id}")
    elif args.mode == "rtsp":
        view_stream(f"rtsp://localhost:8554/annotated/{args.cam_id}")

if __name__ == "__main__":
    main()