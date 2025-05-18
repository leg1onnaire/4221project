# 📷 Intelligent Multi-Source Video Analytics & Streaming Platform

Bu proje; çoklu kamera yayını, gerçek zamanlı yapay zeka destekli kişi tespiti, RTSP/MJPEG akışı, MQTT olay bildirimi ve dinamik web tabanlı kontrol paneli sunar.

---

## 🚀 Özellikler

* 🔌 Çoklu webcam / IP kamera yayını
* 🧠 YOLOv5 ile kişi tespiti
* 🎥 GStreamer + RTSP yayını (annotated frame)
* 🌐 MJPEG akışı (web dashboard ve istemci için)
* 📡 MQTT ile kişi sayısı bildirimi
* 🖥️ Web tabanlı kontrol paneli (start/stop izleme)

---

## 📁 Dosya Yapısı

```
project/
├── main_server.py         # Tüm sistemi yöneten Flask + RTSP + MQTT sunucusu
├── yolo_detector.py       # YOLOv5 tabanlı tespit modülü
├── mqtt_module.py         # MQTT istemci sarmalayıcı
├── client_viewer.py       # OpenCV + MQTT ile izleme aracı
├── requirements.txt       # Gerekli Python bağımlılıkları
├── test_stream.sh         # Test bash scripti
└── README.md              # Bu doküman
```

---

## ⚙️ Kurulum

### 🐍 Python Paketleri

```bash
pip install -r requirements.txt
```

### 🧱 Sistem Paketleri (Ubuntu)

```bash
sudo apt update
sudo apt install -y \
    python3-gi \
    gir1.2-gst-rtsp-server-1.0 \
    gstreamer1.0-tools \
    mosquitto \
    mosquitto-clients
```

---

## ▶️ Kullanım

### 🔧 Sunucuyu Başlat

```bash
python3 main_server.py
```

### 🎦 Kamera Yayını Başlat

```bash
curl -X POST http://localhost:8000/stream/start \
     -H "Content-Type: application/json" \
     -d '{"id": "cam_hp", "url": 0}'
```

### 🌐 Web Panel

Tarayıcıda aç:

```
http://localhost:8000/dashboard
```

### 📺 RTSP İzleme (VLC)

```
rtsp://localhost:8554/annotated/cam_hp
```

### 🧪 Test Scripti

```bash
bash test_stream.sh
```

---

## 🧠 Notlar

* MJPEG akışı `/video/<cam_id>` endpoint'inden alınabilir.
* MQTT ile kişi sayısı şu topic'ten yayınlanır: `events/<cam_id>/person`
* Kameralar dinamik olarak eklenip çıkarılabilir.

---

## 🛠️ Gereksinimler

* Python 3.9+
* OpenCV, Flask, PyTorch, GStreamer, Paho MQTT

---



