#!/usr/bin/env python3
"""
Aimmy V2 Educational Edition - Production Server
Deployed for public API access
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import threading
import random

from flask import Flask, request, jsonify, render_template_string
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'aimmy-v2-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# Global state
detection_engine = None
is_detecting = False
detection_metrics = {
    "total_detections": 0,
    "last_detection_time": None,
    "average_processing_time": 0,
    "successful_targets": 0
}

# Store bridge data
bridge_processes = []

class DetectionEngine:
    def __init__(self):
        self.config = self.load_configuration()
        self.is_running = False
        self.detection_thread = None
        
    def load_configuration(self):
        """Load configuration from environment or defaults"""
        return {
            "ConfidenceThreshold": float(os.environ.get('CONFIDENCE_THRESHOLD', 0.5)),
            "MouseSensitivity": float(os.environ.get('MOUSE_SENSITIVITY', 1.0)),
            "DetectionInterval": int(os.environ.get('DETECTION_INTERVAL', 50)),
            "EnableESP": os.environ.get('ENABLE_ESP', 'true').lower() == 'true',
            "EnableAntiRecoil": os.environ.get('ENABLE_ANTI_RECOIL', 'false').lower() == 'true',
            "TargetProcess": os.environ.get('TARGET_PROCESS', ""),
            "FOV": int(os.environ.get('FOV', 100)),
            "EnableSmoothing": os.environ.get('ENABLE_SMOOTHING', 'true').lower() == 'true',
            "SmoothingStrength": int(os.environ.get('SMOOTHING_STRENGTH', 5)),
            "EnableTriggerBot": os.environ.get('ENABLE_TRIGGER_BOT', 'false').lower() == 'true',
            "TriggerDelay": int(os.environ.get('TRIGGER_DELAY', 50)),
            "ModelPath": os.environ.get('MODEL_PATH', "Models/yolov8n.onnx"),
            "EnableDebugMode": os.environ.get('ENABLE_DEBUG_MODE', 'true').lower() == 'true'
        }
    
    def save_configuration(self, config):
        """Save configuration (in production, this would update environment variables)"""
        self.config = {**self.config, **config}
        logger.info("Configuration updated")
    
    def start_detection(self):
        """Start the detection loop"""
        if self.is_running:
            return {"success": False, "message": "Detection already running"}
        
        self.is_running = True
        self.detection_thread = threading.Thread(target=self._detection_loop)
        self.detection_thread.daemon = True
        self.detection_thread.start()
        
        logger.info("Detection started")
        return {"success": True, "message": "Detection started successfully"}
    
    def stop_detection(self):
        """Stop the detection loop"""
        if not self.is_running:
            return {"success": False, "message": "Detection not running"}
        
        self.is_running = False
        if self.detection_thread:
            self.detection_thread.join(timeout=1)
        
        logger.info("Detection stopped")
        return {"success": True, "message": "Detection stopped successfully"}
    
    def _detection_loop(self):
        """Main detection loop (educational simulation)"""
        while self.is_running:
            try:
                start_time = time.time()
                
                # Simulate detection processing
                detections = self._simulate_detection()
                
                # Calculate processing time
                processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Update metrics
                global detection_metrics
                detection_metrics["total_detections"] += len(detections)
                detection_metrics["last_detection_time"] = datetime.now().isoformat()
                detection_metrics["average_processing_time"] = processing_time
                
                # Select best target
                best_target = None
                if detections:
                    best_target = max(detections, key=lambda x: x["confidence"])
                    if best_target["confidence"] > self.config["ConfidenceThreshold"]:
                        detection_metrics["successful_targets"] += 1
                
                # Emit real-time update
                detection_data = {
                    "detections": detections,
                    "best_target": best_target,
                    "processing_time": processing_time,
                    "screenshot_size": {"width": 1920, "height": 1080},
                    "timestamp": datetime.now().isoformat()
                }
                
                socketio.emit('detection_update', detection_data)
                
                # Sleep for detection interval
                time.sleep(self.config["DetectionInterval"] / 1000.0)
                
            except Exception as e:
                logger.error(f"Detection loop error: {e}")
                time.sleep(0.1)
    
    def _simulate_detection(self):
        """Simulate AI detection results for educational purposes"""
        detections = []
        
        # 30% chance of detecting something
        if random.random() < 0.3:
            num_detections = random.randint(1, 3)
            
            for _ in range(num_detections):
                detection = {
                    "label": "person",
                    "confidence": 0.75 + random.random() * 0.25,
                    "bounding_box": {
                        "x": random.randint(100, 1400),
                        "y": random.randint(100, 800),
                        "width": 100 + random.randint(0, 100),
                        "height": 150 + random.randint(0, 100)
                    }
                }
                
                # Add center point
                detection["center"] = {
                    "x": detection["bounding_box"]["x"] + detection["bounding_box"]["width"] // 2,
                    "y": detection["bounding_box"]["y"] + detection["bounding_box"]["height"] // 2
                }
                
                detections.append(detection)
        
        return detections

# Web Interface HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aimmy V2 - Educational Edition</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; }
        .status-indicator { display: flex; gap: 10px; align-items: center; }
        .metric-card { background: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 20px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2rem; font-weight: bold; color: #007bff; }
        .metric-label { font-size: 0.9rem; color: #6c757d; margin-top: 5px; }
        .debug-log { background: #1e1e1e; color: #d4d4d4; padding: 15px; border-radius: 5px; height: 200px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 0.9rem; }
        .log-entry { margin-bottom: 5px; }
        .log-success { color: #4caf50; }
        .log-error { color: #f44747; }
        .log-info { color: #4ec9b0; }
        #detectionCanvas { border: 1px solid #dee2e6; border-radius: 5px; background: #000; width: 100%; height: 400px; }
        .process-list { max-height: 200px; overflow-y: auto; }
        .process-item { display: flex; justify-content: space-between; align-items: center; padding: 8px; border-bottom: 1px solid #eee; cursor: pointer; }
        .process-item:hover { background-color: #f8f9fa; }
        .process-item.selected { background-color: #007bff; color: white; }
        .api-info { background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .api-url { font-family: 'Courier New', monospace; background: #f5f5f5; padding: 5px; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row bg-dark text-white p-3">
            <div class="col-md-6">
                <h1><i class="fas fa-crosshairs"></i> Aimmy V2 - Educational Edition</h1>
                <p class="mb-0">AI-Powered Object Detection System</p>
            </div>
            <div class="col-md-6 text-end">
                <div class="status-indicator">
                    <span id="connectionStatus" class="badge bg-success">Connected</span>
                    <span id="detectionStatus" class="badge bg-secondary">Stopped</span>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-12">
                <div class="api-info">
                    <h5><i class="fas fa-info-circle"></i> API Information</h5>
                    <p><strong>Bridge Application Endpoint:</strong></p>
                    <p class="api-url">POST {{ request.host_url }}api/processes</p>
                    <p><small>Use this URL in your bridge application to send process data.</small></p>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-4">
                <div class="card mt-3">
                    <div class="card-header"><h5><i class="fas fa-cog"></i> Control Panel</h5></div>
                    <div class="card-body">
                        <div class="d-grid gap-2">
                            <button id="startBtn" class="btn btn-success"><i class="fas fa-play"></i> Start Detection</button>
                            <button id="stopBtn" class="btn btn-danger"><i class="fas fa-stop"></i> Stop Detection</button>
                        </div>
                    </div>
                </div>

                <div class="card mt-3">
                    <div class="card-header"><h5><i class="fas fa-sliders-h"></i> Configuration</h5></div>
                    <div class="card-body">
                        <div class="mb-3">
                            <label class="form-label">Confidence Threshold</label>
                            <input type="range" class="form-range" id="confidenceSlider" min="0.1" max="1" step="0.1" value="0.5">
                            <span id="confidenceValue">0.5</span>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Detection Interval (ms)</label>
                            <input type="range" class="form-range" id="intervalSlider" min="10" max="200" step="10" value="50">
                            <span id="intervalValue">50ms</span>
                        </div>
                        <button id="saveConfigBtn" class="btn btn-primary"><i class="fas fa-save"></i> Save Configuration</button>
                    </div>
                </div>

                <div class="card mt-3">
                    <div class="card-header"><h5><i class="fas fa-server"></i> Bridge Data</h5></div>
                    <div class="card-body">
                        <div class="mb-2">
                            <small class="text-muted">Processes from Bridge: <span id="bridgeProcessCount">0</span></small>
                        </div>
                        <div id="bridgeProcessList" class="process-list"></div>
                    </div>
                </div>
            </div>

            <div class="col-md-8">
                <div class="card mt-3">
                    <div class="card-header"><h5><i class="fas fa-chart-line"></i> Performance Metrics</h5></div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-3">
                                <div class="metric-card">
                                    <div class="metric-value" id="totalDetections">0</div>
                                    <div class="metric-label">Total Detections</div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="metric-card">
                                    <div class="metric-value" id="processingTime">0ms</div>
                                    <div class="metric-label">Processing Time</div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="metric-card">
                                    <div class="metric-value" id="detectionRate">0/s</div>
                                    <div class="metric-label">Detection Rate</div>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="metric-card">
                                    <div class="metric-value" id="bridgeStatus">Offline</div>
                                    <div class="metric-label">Bridge Status</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card mt-3">
                    <div class="card-header"><h5><i class="fas fa-eye"></i> Detection Visualization</h5></div>
                    <div class="card-body">
                        <canvas id="detectionCanvas" width="640" height="480"></canvas>
                    </div>
                </div>

                <div class="card mt-3">
                    <div class="card-header">
                        <h5><i class="fas fa-terminal"></i> Debug Log</h5>
                        <button id="clearLogBtn" class="btn btn-sm btn-outline-secondary float-end">Clear</button>
                    </div>
                    <div class="card-body">
                        <div id="debugLog" class="debug-log"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <script>
        const socket = io();
        let currentConfig = {};
        let lastBridgeUpdate = null;
        
        socket.on('connect', function() {
            addLogEntry('Connected to Aimmy Detection System', 'success');
        });
        
        socket.on('bridge_update', function(data) {
            updateBridgeStatus(data);
        });
        
        socket.on('detection_update', function(data) {
            updateDetectionVisualization(data);
            updatePerformanceMetrics(data);
        });
        
        document.getElementById('startBtn').addEventListener('click', async function() {
            const response = await fetch('/api/detection/start', { method: 'POST' });
            const result = await response.json();
            if (result.success) {
                document.getElementById('detectionStatus').textContent = 'Running';
                document.getElementById('detectionStatus').className = 'badge bg-success';
                addLogEntry('Detection started successfully', 'success');
            } else {
                addLogEntry('Failed to start detection: ' + result.message, 'error');
            }
        });
        
        document.getElementById('stopBtn').addEventListener('click', async function() {
            const response = await fetch('/api/detection/stop', { method: 'POST' });
            const result = await response.json();
            if (result.success) {
                document.getElementById('detectionStatus').textContent = 'Stopped';
                document.getElementById('detectionStatus').className = 'badge bg-secondary';
                addLogEntry('Detection stopped successfully', 'success');
            } else {
                addLogEntry('Failed to stop detection: ' + result.message, 'error');
            }
        });
        
        document.getElementById('saveConfigBtn').addEventListener('click', async function() {
            const config = {
                ConfidenceThreshold: parseFloat(document.getElementById('confidenceSlider').value),
                DetectionInterval: parseInt(document.getElementById('intervalSlider').value)
            };
            
            const response = await fetch('/api/configuration', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            
            if (response.ok) {
                addLogEntry('Configuration saved successfully', 'success');
            } else {
                addLogEntry('Failed to save configuration', 'error');
            }
        });
        
        document.getElementById('clearLogBtn').addEventListener('click', function() {
            document.getElementById('debugLog').innerHTML = '';
        });
        
        document.getElementById('confidenceSlider').addEventListener('input', function() {
            document.getElementById('confidenceValue').textContent = this.value;
        });
        
        document.getElementById('intervalSlider').addEventListener('input', function() {
            document.getElementById('intervalValue').textContent = this.value + 'ms';
        });
        
        function updateBridgeStatus(data) {
            const bridgeStatus = document.getElementById('bridgeStatus');
            const bridgeProcessCount = document.getElementById('bridgeProcessCount');
            const bridgeProcessList = document.getElementById('bridgeProcessList');
            
            if (data && data.processes) {
                bridgeStatus.textContent = 'Online';
                bridgeStatus.style.color = '#28a745';
                bridgeProcessCount.textContent = data.processes.length;
                lastBridgeUpdate = new Date();
                
                // Update bridge process list
                bridgeProcessList.innerHTML = '';
                data.processes.slice(0, 5).forEach(process => {
                    const item = document.createElement('div');
                    item.className = 'process-item';
                    item.innerHTML = `
                        <div>
                            <div class="process-name">${process.ProcessName || process.name || 'Unknown'}</div>
                            <div class="process-id">PID: ${process.ProcessId || process.pid || 'N/A'}</div>
                        </div>
                    `;
                    bridgeProcessList.appendChild(item);
                });
                
                addLogEntry(`Bridge data received: ${data.processes.length} processes`, 'info');
            }
        }
        
        function updateDetectionVisualization(data) {
            const canvas = document.getElementById('detectionCanvas');
            const ctx = canvas.getContext('2d');
            
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#000';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            if (data.detections) {
                data.detections.forEach(detection => {
                    const x = (detection.bounding_box.x / data.screenshot_size.width) * canvas.width;
                    const y = (detection.bounding_box.y / data.screenshot_size.height) * canvas.height;
                    const width = (detection.bounding_box.width / data.screenshot_size.width) * canvas.width;
                    const height = (detection.bounding_box.height / data.screenshot_size.height) * canvas.height;
                    
                    ctx.strokeStyle = '#00ff00';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(x, y, width, height);
                    
                    ctx.fillStyle = '#00ff00';
                    ctx.font = '12px Arial';
                    ctx.fillText(`${detection.label} (${(detection.confidence * 100).toFixed(0)}%)`, x, y - 5);
                });
            }
            
            // Draw crosshair
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            ctx.strokeStyle = '#ff0000';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(centerX - 10, centerY);
            ctx.lineTo(centerX + 10, centerY);
            ctx.moveTo(centerX, centerY - 10);
            ctx.lineTo(centerX, centerY + 10);
            ctx.stroke();
        }
        
        function updatePerformanceMetrics(data) {
            document.getElementById('processingTime').textContent = data.processing_time.toFixed(1) + 'ms';
            document.getElementById('totalDetections').textContent = data.detections ? data.detections.length : 0;
            document.getElementById('detectionRate').textContent = data.detections ? data.detections.length : 0;
        }
        
        function addLogEntry(message, type = 'info') {
            const logContainer = document.getElementById('debugLog');
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${type}`;
            
            const timestamp = new Date().toLocaleTimeString();
            logEntry.innerHTML = `[${timestamp}] ${message}`;
            
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }
        
        // Check bridge connection status
        setInterval(() => {
            const bridgeStatus = document.getElementById('bridgeStatus');
            if (lastBridgeUpdate && (new Date() - lastBridgeUpdate) > 10000) {
                bridgeStatus.textContent = 'Offline';
                bridgeStatus.style.color = '#dc3545';
            }
        }, 5000);
        
        // Initial log
        addLogEntry('Aimmy V2 Educational Edition initialized', 'info');
        addLogEntry('Waiting for bridge connection...', 'info');
    </script>
</body>
</html>
"""

# Routes
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/detection/start', methods=['POST'])
def start_detection():
    global detection_engine
    if not detection_engine:
        detection_engine = DetectionEngine()
    
    result = detection_engine.start_detection()
    return jsonify(result)

@app.route('/api/detection/stop', methods=['POST'])
def stop_detection():
    global detection_engine
    if detection_engine:
        result = detection_engine.stop_detection()
        return jsonify(result)
    return jsonify({"success": False, "message": "Detection engine not initialized"})

@app.route('/api/configuration', methods=['GET', 'POST'])
def configuration():
    global detection_engine
    if not detection_engine:
        detection_engine = DetectionEngine()
    
    if request.method == 'POST':
        config = request.json
        try:
            detection_engine.save_configuration(config)
            return jsonify({"success": True, "message": "Configuration saved successfully"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400
    
    return jsonify(detection_engine.config)

@app.route('/api/processes', methods=['GET', 'POST'])
def processes():
    global bridge_processes
    
    if request.method == 'POST':
        # Handle POST request from bridge application
        try:
            data = request.json
            bridge_processes = data if isinstance(data, list) else []
            
            logger.info(f"Received processes from bridge: {len(bridge_processes)} processes")
            
            # Emit bridge update to connected clients
            socketio.emit('bridge_update', {
                'processes': bridge_processes,
                'timestamp': datetime.now().isoformat(),
                'count': len(bridge_processes)
            })
            
            return jsonify({
                "success": True, 
                "message": "Processes received successfully",
                "count": len(bridge_processes)
            })
        except Exception as e:
            logger.error(f"Error processing bridge data: {e}")
            return jsonify({"success": False, "message": str(e)}), 400
    
    # Handle GET request - return bridge processes
    return jsonify(bridge_processes)

@app.route('/api/status', methods=['GET'])
def status():
    global detection_engine, detection_metrics, bridge_processes
    return jsonify({
        "is_running": detection_engine.is_running if detection_engine else False,
        "metrics": detection_metrics,
        "configuration": detection_engine.config if detection_engine else {},
        "bridge_processes": len(bridge_processes),
        "bridge_connected": len(bridge_processes) > 0
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Aimmy V2 Educational Edition"
    })

if __name__ == '__main__':
    # Initialize detection engine
    detection_engine = DetectionEngine()
    
    logger.info("=== Aimmy V2 Educational Edition - Production ===")
    logger.info("AI-Powered Object Detection System")
    logger.info("Ready to receive bridge connections")
    
    # Start the server
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
