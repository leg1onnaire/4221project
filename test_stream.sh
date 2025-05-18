#!/bin/bash

# 🚀 Test script for camera stream

echo "> Starting test stream..."
curl -X POST http://localhost:8000/stream/start \
     -H "Content-Type: application/json" \
     -d '{"id": "cam_test", "url": 0}'

sleep 5

echo "> Checking status..."
curl http://localhost:8000/status

sleep 5

echo "> Stopping stream..."
curl -X POST http://localhost:8000/stream/stop \
     -H "Content-Type: application/json" \
     -d '{"id": "cam_test"}'

echo "> Done."
