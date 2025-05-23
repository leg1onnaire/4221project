# === Intelligent Multi-Source Video Analytics & Streaming Platform ===
# main_server.py

import cv2
import threading
import time
import torch
import numpy as np
import warnings
import json
import paho.mqtt.client as mqtt
from flask import Flask, Response, request, jsonify
from yolo_detector import YOLODetector

# RTSP için gerekli
import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GLib

Gst.init(None)

warnings.filterwarnings("ignore", category=FutureWarning)

# ========== GLOBALS ==========
detector = YOLODetector()
streams = {}
latest_frames = {}
mqtt_client = None

# ========== RTSP SERVER ==========
class RTSPMediaFactory(GstRtspServer.RTSPMediaFactory):
    def __init__(self, cam_id):
        super().__init__()
        self.cam_id = cam_id
        self.launch_string = (
            'appsrc name=source is-live=true block=true format=time do-timestamp=true caps="video/x-raw,format=BGR,width=640,height=480,framerate=30/1" ! '
            'videoconvert ! x264enc tune=zerolatency bitrate=512 speed-preset=superfast ! rtph264pay config-interval=1 name=pay0 pt=96'
        )
        self.set_launch(self.launch_string)
        self.set_shared(True)
        self.frame = None
        self.source = None

    def do_configure(self, rtsp_media):
        self.source = rtsp_media.get_element().get_child_by_name("source")
        self.source.connect("need-data", self.on_need_data)

    def on_need_data(self, src, length):
        if self.frame is None:
            return
        frame = cv2.resize(self.frame, (640, 480))
        data = frame.tobytes()
        buf = Gst.Buffer.new_allocate(None, len(data), None)
        buf.fill(0, data)
        timestamp = Gst.util_uint64_scale(Gst.util_get_timestamp(), 1, Gst.SECOND)
        buf.pts = buf.dts = timestamp
        buf.duration = Gst.util_uint64_scale_int(1, Gst.SECOND, 30)
        retval = src.emit("push-buffer", buf)
        if retval != Gst.FlowReturn.OK:
            print(f"[RTSP] Flow error: {retval}")

class RTSPServer:
    def __init__(self, port=8554):
        self.server = GstRtspServer.RTSPServer()
        self.server.set_service(str(port))
        self.mounts = self.server.get_mount_points()
        self.factories = {}
        self.loop = GLib.MainLoop()
        self.thread = threading.Thread(target=self.loop.run)

    def start(self):
        self.server.attach(None)
        self.thread.start()
        print("[RTSP] Server started at rtsp://localhost:8554/")

    def add_stream(self, cam_id):
        factory = RTSPMediaFactory(cam_id)
        self.factories[cam_id] = factory
        path = f"/annotated/{cam_id}"
        self.mounts.add_factory(path, factory)
        print(f"[RTSP] Stream available at rtsp://localhost:8554{path}")

    def push_frame(self, cam_id, frame):
        if cam_id in self.factories:
            self.factories[cam_id].frame = frame

rtsp_server = RTSPServer()
rtsp_server.start()

# ========== VIDEO INGESTION + ANALYTICS ==========
class StreamWorker(threading.Thread):
    def __init__(self, cam_id, source_url):
        super().__init__()
        self.cam_id = cam_id
        self.source_url = source_url
        self.running = False

    def run(self):
        cap = cv2.VideoCapture(self.source_url)
        if not cap.isOpened():
            print(f"[ERROR] Cannot open {self.source_url}")
            return

        self.running = True
        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue

            annotated, people = detector.detect(frame)
            latest_frames[self.cam_id] = annotated

            if mqtt_client:
                topic = f"events/{self.cam_id}/person"
                msg = json.dumps({"count": people})
                mqtt_client.publish(topic, msg)

            rtsp_server.push_frame(self.cam_id, annotated)

        cap.release()

    def stop(self):
        self.running = False

# ========== STREAMING SERVER (MJPEG via Flask) ==========
app = Flask(__name__)

@app.route("/video/<cam_id>")
def video(cam_id):
    def gen():
        while True:
            frame = latest_frames.get(cam_id)
            if frame is not None:
                _, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.05)
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/dashboard")
def dashboard():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>📷 Camera Control Dashboard</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f4f4f4; padding: 20px; }
        h1 { text-align: center; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }
        .card { background: white; padding: 10px; border-radius: 10px; box-shadow: 0 0 8px rgba(0,0,0,0.1); }
        video, img { width: 100%; border-radius: 6px; }
        button { margin: 5px 0; width: 48%; padding: 8px; }
      </style>
    </head>
    <body>
      <h1>🎥 Intelligent Camera Stream Dashboard</h1>
      <div class="grid" id="cameraGrid"></div>

      <script>
        const cameras = ["cam_hp", "cam2", "cam3"]

        function createCameraCard(cam_id) {
          const card = document.createElement("div")
          card.className = "card"
          card.innerHTML = `
            <h3>${cam_id}</h3>
            <img id="img_${cam_id}" src="/video/${cam_id}" />
            <div>
              <button onclick="startStream('${cam_id}')">Start</button>
              <button onclick="stopStream('${cam_id}')">Stop</button>
            </div>
            <p id="status_${cam_id}">Not running</p>
          `
          return card
        }

        async function startStream(cam_id) {
          const res = await fetch("/stream/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: cam_id, url: 0 })
          });
          const json = await res.json()
          document.getElementById(`status_${cam_id}`).innerText = json.status || "Started"
        }

        async function stopStream(cam_id) {
          const res = await fetch("/stream/stop", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: cam_id })
          });
          const json = await res.json()
          document.getElementById(`status_${cam_id}`).innerText = json.status || "Stopped"
        }

        cameras.forEach(cam_id => {
          document.getElementById("cameraGrid").appendChild(createCameraCard(cam_id))
        });
      </script>
    </body>
    </html>
    '''

# ========== REST API ==========
@app.route("/stream/start", methods=["POST"])
def start_stream():
    data = request.json
    cam_id = data.get("id")
    url = data.get("url")

    if cam_id in streams:
        return jsonify({"status": "already running"})

    rtsp_server.add_stream(cam_id)

    worker = StreamWorker(cam_id, url)
    worker.start()
    streams[cam_id] = worker
    return jsonify({"status": f"started {cam_id}"})

@app.route("/stream/stop", methods=["POST"])
def stop_stream():
    data = request.json
    cam_id = data.get("id")

    worker = streams.pop(cam_id, None)
    if worker:
        worker.stop()
        return jsonify({"status": f"stopped {cam_id}"})
    return jsonify({"status": "not running"})

@app.route("/status")
def status():
    return jsonify({"active_streams": list(streams.keys())})

# ========== MQTT INTEGRATION ==========
def setup_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.loop_start()

# ========== ENTRY POINT ==========
if __name__ == '__main__':
    setup_mqtt()
    app.run(host='0.0.0.0', port=8000, threaded=True)
