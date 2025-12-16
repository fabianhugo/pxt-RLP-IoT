#!/usr/bin/env python3
"""
Simple IoT Platform Server for Calliope Mini WiFi Modules
Provides REST API endpoints for sensor data collection and device control
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Database setup
DB_PATH = 'iot_data.db'

def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Sensor data table
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  device_id TEXT NOT NULL,
                  sensor_type TEXT NOT NULL,
                  value REAL NOT NULL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Device commands table
    c.execute('''CREATE TABLE IF NOT EXISTS device_commands
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  device_id TEXT NOT NULL,
                  command TEXT NOT NULL,
                  value TEXT,
                  executed INTEGER DEFAULT 0,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # Device registry
    c.execute('''CREATE TABLE IF NOT EXISTS devices
                 (device_id TEXT PRIMARY KEY,
                  name TEXT,
                  last_seen DATETIME,
                  ip_address TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# ==================== API Endpoints ====================

@app.route('/')
def home():
    """Serve dashboard"""
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/sensor', methods=['POST'])
def receive_sensor_data():
    """
    Receive sensor data from devices
    Expected JSON: {"temperature": "25.3"} or {"humidity": "60"}
    Or with device_id: {"device_id": "Device001", "temperature": "25.3"}
    """
    try:
        data = request.json
        client_ip = request.remote_addr
        
        # Extract device_id if provided, otherwise use IP
        device_id = data.get('device_id', client_ip)
        
        # Update device registry
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO devices (device_id, last_seen, ip_address)
                     VALUES (?, CURRENT_TIMESTAMP, ?)''', (device_id, client_ip))
        
        # Store all sensor readings
        stored_count = 0
        for key, value in data.items():
            if key != 'device_id':  # Skip device_id field
                try:
                    # Try to convert to float for numeric values
                    numeric_value = float(value)
                    c.execute('''INSERT INTO sensor_data (device_id, sensor_type, value)
                                 VALUES (?, ?, ?)''', (device_id, key, numeric_value))
                    stored_count += 1
                except ValueError:
                    # Store as string representation
                    c.execute('''INSERT INTO sensor_data (device_id, sensor_type, value)
                                 VALUES (?, ?, ?)''', (device_id, key, 0))
                    stored_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "ok",
            "device_id": device_id,
            "records_stored": stored_count
        }), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/sensor/<device_id>', methods=['GET'])
def get_sensor_data(device_id):
    """
    Get latest sensor data for a device
    Returns: {"temperature": "25.3", "humidity": "60", "timestamp": "..."}
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get latest value for each sensor type
        c.execute('''SELECT sensor_type, value, timestamp 
                     FROM sensor_data 
                     WHERE device_id = ?
                     AND timestamp = (
                         SELECT MAX(timestamp) 
                         FROM sensor_data AS sd2 
                         WHERE sd2.device_id = sensor_data.device_id 
                         AND sd2.sensor_type = sensor_data.sensor_type
                     )''', (device_id,))
        
        results = c.fetchall()
        conn.close()
        
        if not results:
            return jsonify({"status": "no_data"}), 404
        
        # Format response
        data = {sensor_type: value for sensor_type, value, _ in results}
        data['timestamp'] = results[0][2] if results else None
        
        return jsonify(data), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/command/<device_id>', methods=['GET'])
def get_commands(device_id):
    """
    Get pending commands for a device
    Returns: {"command": "led_on", "value": "red"}
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get oldest unexecuted command
        c.execute('''SELECT id, command, value 
                     FROM device_commands 
                     WHERE device_id = ? AND executed = 0
                     ORDER BY timestamp ASC
                     LIMIT 1''', (device_id,))
        
        result = c.fetchone()
        
        if result:
            cmd_id, command, value = result
            # Mark as executed
            c.execute('UPDATE device_commands SET executed = 1 WHERE id = ?', (cmd_id,))
            conn.commit()
            conn.close()
            
            return jsonify({
                "command": command,
                "value": value or ""
            }), 200
        else:
            conn.close()
            return jsonify({"status": "no_commands"}), 404
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/command', methods=['POST'])
def send_command():
    """
    Send command to device
    Expected JSON: {"device_id": "Device001", "command": "led_on", "value": "red"}
    """
    try:
        data = request.json
        device_id = data.get('device_id')
        command = data.get('command')
        value = data.get('value', '')
        
        if not device_id or not command:
            return jsonify({"status": "error", "message": "device_id and command required"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO device_commands (device_id, command, value)
                     VALUES (?, ?, ?)''', (device_id, command, value))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "ok", "message": "Command queued"}), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/devices', methods=['GET'])
def get_devices():
    """Get list of all registered devices"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT device_id, name, last_seen, ip_address FROM devices
                     ORDER BY last_seen DESC''')
        
        devices = []
        for row in c.fetchall():
            devices.append({
                "device_id": row[0],
                "name": row[1] or row[0],
                "last_seen": row[2],
                "ip_address": row[3]
            })
        
        conn.close()
        return jsonify(devices), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/history/<device_id>/<sensor_type>', methods=['GET'])
def get_history(device_id, sensor_type):
    """Get historical data for a specific sensor"""
    try:
        limit = request.args.get('limit', 100, type=int)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT value, timestamp FROM sensor_data
                     WHERE device_id = ? AND sensor_type = ?
                     ORDER BY timestamp DESC
                     LIMIT ?''', (device_id, sensor_type, limit))
        
        data = [{"value": row[0], "timestamp": row[1]} for row in c.fetchall()]
        conn.close()
        
        return jsonify(data), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


# ==================== Dashboard HTML ====================

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>IoT Platform Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        h1 {
            color: white;
            text-align: center;
            margin-bottom: 20px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        /* Toolbar */
        .toolbar {
            background: white;
            border-radius: 15px;
            padding: 15px 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }
        .toolbar button {
            padding: 10px 20px;
            margin: 0;
        }
        .toolbar label {
            margin: 0 10px 0 20px;
            font-weight: 500;
        }
        
        /* Widget Grid */
        .widget-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        /* Widget Base */
        .widget {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            position: relative;
            cursor: move;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .widget.dragging {
            opacity: 0.5;
            transform: scale(0.95);
        }
        .widget:hover {
            box-shadow: 0 15px 40px rgba(0,0,0,0.3);
        }
        
        .widget-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            cursor: move;
            padding-bottom: 10px;
            border-bottom: 2px solid #f0f0f0;
        }
        .widget-title {
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }
        .widget-controls {
            display: flex;
            gap: 5px;
        }
        .widget-btn {
            background: #f0f0f0;
            border: none;
            width: 28px;
            height: 28px;
            border-radius: 6px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
            padding: 0;
            font-size: 16px;
        }
        .widget-btn:hover {
            background: #e0e0e0;
            transform: none;
        }
        .widget-btn.delete:hover {
            background: #ff5252;
            color: white;
        }
        
        /* Chart Widget */
        .chart-widget canvas {
            max-height: 250px;
        }
        
        /* Gauge Widget */
        .gauge-widget {
            text-align: center;
        }
        .gauge-container {
            position: relative;
            width: 200px;
            height: 200px;
            margin: 20px auto;
        }
        .gauge-svg {
            transform: rotate(-90deg);
        }
        .gauge-value {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 2.5em;
            font-weight: bold;
         !-- Toolbar -->
        <div class="toolbar">
            <button onclick="showAddWidget('chart')">📊 Add Chart</button>
            <button onclick="showAddWidget('gauge')">🎯 Add Gauge</button>
            <button onclick="showAddWidget('text')">📝 Add Text</button>
            <button onclick="clearAllWidgets()" class="secondary">🗑️ Clear All</button>
            <label style="margin-left: auto;">Auto-refresh:</label>
            <input type="checkbox" id="autoRefresh" checked style="width: auto;">
        </div>
        
        <!-- Widget Grid -->
        <div class="widget-grid" id="widgetGrid">
            <!-- Widgets will be added here dynamically -->
        </div>
    </div>

    <!-- Add Widget Modal -->
    <div class="modal" id="addWidgetModal">
        <div class="modal-content">
            <h2 id="modalTitle">Add Widget</h2>
            <div class="form-group">
                <label>Widget Title</label>
                <input type="text" id="widgetTitle" placeholder="e.g., Temperature Monitor">
            </div>
            <div class="form-group">
                <label>Device ID</label>
                <select id="widgetDevice">
                    <option value="">Select device...</option>
                </select>
            </div>
            <div class="form-group">
                <label>Sensor Type</label>
                <input type="text" id="widgetSensor" placeholder="e.g., temperature, humidity">
            </div>
            <div class="form-group" id="unitGroup" style="display: none;">
                <label>Unit</label>
                <input type="text" id="widgetUnit" placeholder="e.g., °C, %">
            </div>
            <button onclick="addWidget()">Add Widget</button>
            <button onclick="closeModal()" class="secondary">Cancel</button>
        </div>
    </div
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .modal-content h2 {
            margin-bottom: 20px;
            color: #667eea;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 500;
        }
        input, select {
            width: 100%;
            padding: 10px;
            border: 2px solid #eee;
            border-radius: 8px;
            font-size: 1em;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: scale(1.05);
        }
        button.secondary {
            background: #999;
            margin-left: 10px;
        }
        
        .status-online {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #4caf50;
            border-radius: 50%;
            margin-right: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 IoT Platform Dashboard</h1>
        
        <div class="stats" id="stats">
            <div class="card">
                <h3>📱 Active Devices</h3>
                <div class="sensor-value" id="deviceCount">-</div>
                <div class="sensor-label">Connected</div>
            </div>
            <div class="card">
                <h3>📊 Total Readings</h3>
                <div class="sensor-value" id="readingCount">-</div>
                <div class="sensor-label">Last 24h</div>
            </div>
            <div class="card">
                <h3>⚡ Status</h3>
                <div class="sensor-value">Online</div>
                <div class="sensor-label">Server Running</div>
            </div>
        </div>

        <div class="device-list">
            <h3>📟 Connected Devices</h3>
            <div id="deviceList">Loading...</div>
        </div>

        <div class="control-panel">
            <h3>🎮 Send Command</h3>
            <div class="form-group">
                <label>Device ID</label>
                <select id="deviceSelect">
                    <option value="">Select device...</option>
                </select>
            </div>
            <div class="form-group">
                <label>Command</label>
                <input type="text" id="commandInput" placeholder="e.g., led_on, display_text">
            </div>
            <div class="form-group">
                <label>Value (optional)</label>
                <input type="text" id="valueInput" placeholder="e.g., red, Hello">
            </div>
            <button onclick="sendCommand()">Send Command</button>
        </div>
    </div>

    <button class="refresh-btn" onclick="loadData()">🔄</button>

    <script>
        async function loadData() {
            try {
                // Load devices
                const response = await fetch('/api/devices');
                const devices = await response.json();
                
                document.getElementById('deviceCount').textContent = devices.length;
                
                const deviceList = document.getElementById('deviceList');
                const deviceSelect = document.getElementById('deviceSelect');
                
                if (devices.length === 0) {
                    deviceList.innerHTML = '<p style="text-align:center; color:#999;">No devices connected yet</p>';
                } else {
                    // Load sensor data for each device
                    const devicesWithData = await Promise.all(devices.map(async device => {
                        try {
                            const sensorResponse = await fetch(`/api/sensor/${device.device_id}`);
                            if (sensorResponse.ok) {
                                const sensorData = await sensorResponse.json();
                                return { ...device, sensorData };
                            }
                        } catch (e) {
                            console.log(`No data for ${device.device_id}`);
                        }
                        return { ...device, sensorData: null };
                    }));
                    
                    deviceList.innerHTML = devicesWithData.map(device => {
                        let sensorDisplay = '';
                        if (device.sensorData) {
                            const sensors = Object.keys(device.sensorData)
                                .filter(key => key !== 'timestamp')
                                .map(key => `<span style="color:#667eea; font-weight:bold;">${key}:</span> ${device.sensorData[key]}`)
                                .join(' | ');
                            sensorDisplay = `<br><small>${sensors}</small>`;
                        }
                        
                        return `
                            <div class="device-item">
                                <div>
                                    <span class="status-online"></span>
                                    <span class="device-name">${device.name}</span>
                                    <br>
                                    <small style="color:#999;">${device.ip_address}</small>
                                    ${sensorDisplay}
                                </div>
                                <div class="device-time">${new Date(device.last_seen).toLocaleTimeString()}</div>
                            </div>
                        `;
                    }).join('');
                    
                    // Update device select
                    deviceSelect.innerHTML = '<option value="">Select device...</option>' +
                        devices.map(d => `<option value="${d.device_id}">${d.name}</option>`).join('');
                }
                
            } catch (error) {
                console.error('Error loading data:', error);
            }
        }

        async function sendCommand() {
            const deviceId = document.getElementById('deviceSelect').value;
            const command = document.getElementById('commandInput').value;
            const value = document.getElementById('valueInput').value;
            
            if (!deviceId || !command) {
                alert('Please select device and enter command');
                return;
            }
            
            try {
                const response = await fetch('/api/command', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({device_id: deviceId, command, value})
                });
                
                const result = await response.json();
                alert(result.message || 'Command sent!');
                
                document.getElementById('commandInput').value = '';
                document.getElementById('valueInput').value = '';
                
            } catch (error) {
                alert('Error sending command: ' + error.message);
            }
        }

        // Auto-refresh every 5 seconds
        setInterval(loadData, 5000);
        loadData();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("🚀 IoT Platform Server Starting...")
    print("📊 Dashboard: http://localhost:5000")
    print("📡 API Endpoint: http://localhost:5000/api/sensor")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
