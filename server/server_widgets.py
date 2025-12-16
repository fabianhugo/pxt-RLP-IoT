#!/usr/bin/env python3
"""
Enhanced IoT Platform Server with Draggable Widgets
Provides REST API endpoints and customizable dashboard
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
    """Receive sensor data from devices"""
    try:
        data = request.json
        client_ip = request.remote_addr
        
        device_id = data.get('device_id', client_ip)
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO devices (device_id, last_seen, ip_address)
                     VALUES (?, CURRENT_TIMESTAMP, ?)''', (device_id, client_ip))
        
        stored_count = 0
        for key, value in data.items():
            if key != 'device_id':
                try:
                    numeric_value = float(value)
                    c.execute('''INSERT INTO sensor_data (device_id, sensor_type, value)
                                 VALUES (?, ?, ?)''', (device_id, key, numeric_value))
                    stored_count += 1
                except ValueError:
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
    """Get latest sensor data for a device"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
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
        
        data = {sensor_type: value for sensor_type, value, _ in results}
        data['timestamp'] = results[0][2] if results else None
        
        return jsonify(data), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/api/command/<device_id>', methods=['GET'])
def get_commands(device_id):
    """Get pending commands for a device"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''SELECT id, command, value 
                     FROM device_commands 
                     WHERE device_id = ? AND executed = 0
                     ORDER BY timestamp ASC
                     LIMIT 1''', (device_id,))
        
        result = c.fetchone()
        
        if result:
            cmd_id, command, value = result
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
    """Send command to device"""
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
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
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
            color: #667eea;
        }
        .gauge-label {
            color: #999;
            font-size: 1.1em;
            margin-top: -10px;
        }
        
        /* Text Widget */
        .text-widget-content {
            font-size: 3em;
            font-weight: bold;
            color: #667eea;
            text-align: center;
            padding: 30px 10px;
        }
        .text-widget-label {
            text-align: center;
            color: #999;
            font-size: 1em;
        }
        
        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal.active {
            display: flex;
        }
        .modal-content {
            background: white;
            border-radius: 15px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>🌐 IoT Platform Dashboard</h1>
        
        <!-- Toolbar -->
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
    </div>

    <script>
        let widgets = [];
        let charts = {};
        let widgetIdCounter = 0;
        let currentWidgetType = '';
        let devices = [];
        
        // Load widgets from localStorage
        function loadWidgetsFromStorage() {
            const stored = localStorage.getItem('iot_widgets');
            if (stored) {
                widgets = JSON.parse(stored);
                widgetIdCounter = Math.max(...widgets.map(w => w.id), 0) + 1;
                widgets.forEach(w => renderWidget(w));
            }
        }
        
        // Save widgets to localStorage
        function saveWidgetsToStorage() {
            localStorage.setItem('iot_widgets', JSON.stringify(widgets));
        }
        
        // Load devices
        async function loadDevices() {
            try {
                const response = await fetch('/api/devices');
                devices = await response.json();
                
                const select = document.getElementById('widgetDevice');
                if (select) {
                    select.innerHTML = '<option value="">Select device...</option>' +
                        devices.map(d => `<option value="${d.device_id}">${d.name}</option>`).join('');
                }
            } catch (error) {
                console.error('Error loading devices:', error);
            }
        }
        
        // Show add widget modal
        function showAddWidget(type) {
            currentWidgetType = type;
            document.getElementById('modalTitle').textContent = 
                type === 'chart' ? 'Add Chart Widget' :
                type === 'gauge' ? 'Add Gauge Widget' : 'Add Text Widget';
            
            // Show unit field for gauge and text
            document.getElementById('unitGroup').style.display = 
                (type === 'gauge' || type === 'text') ? 'block' : 'none';
            
            document.getElementById('addWidgetModal').classList.add('active');
        }
        
        function closeModal() {
            document.getElementById('addWidgetModal').classList.remove('active');
            document.getElementById('widgetTitle').value = '';
            document.getElementById('widgetSensor').value = '';
            document.getElementById('widgetUnit').value = '';
        }
        
        // Add new widget
        function addWidget() {
            const title = document.getElementById('widgetTitle').value;
            const deviceId = document.getElementById('widgetDevice').value;
            const sensor = document.getElementById('widgetSensor').value;
            const unit = document.getElementById('widgetUnit').value;
            
            if (!title || !deviceId || !sensor) {
                alert('Please fill all required fields');
                return;
            }
            
            const widget = {
                id: widgetIdCounter++,
                type: currentWidgetType,
                title: title,
                deviceId: deviceId,
                sensor: sensor,
                unit: unit || '',
                data: []
            };
            
            widgets.push(widget);
            renderWidget(widget);
            saveWidgetsToStorage();
            closeModal();
        }
        
        // Render widget
        function renderWidget(widget) {
            const grid = document.getElementById('widgetGrid');
            const widgetDiv = document.createElement('div');
            widgetDiv.className = 'widget';
            widgetDiv.id = `widget-${widget.id}`;
            widgetDiv.draggable = true;
            
            if (widget.type === 'chart') {
                widgetDiv.classList.add('chart-widget');
                widgetDiv.innerHTML = `
                    <div class="widget-header">
                        <div class="widget-title">${widget.title}</div>
                        <div class="widget-controls">
                            <button class="widget-btn delete" onclick="deleteWidget(${widget.id})">🗑️</button>
                        </div>
                    </div>
                    <canvas id="chart-${widget.id}"></canvas>
                `;
                grid.appendChild(widgetDiv);
                
                // Create chart
                const ctx = document.getElementById(`chart-${widget.id}`).getContext('2d');
                charts[widget.id] = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: [],
                        datasets: [{
                            label: widget.sensor,
                            data: [],
                            borderColor: '#667eea',
                            backgroundColor: 'rgba(102, 126, 234, 0.1)',
                            tension: 0.4,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: { beginAtZero: false }
                        }
                    }
                });
            } else if (widget.type === 'gauge') {
                widgetDiv.innerHTML = `
                    <div class="widget-header">
                        <div class="widget-title">${widget.title}</div>
                        <div class="widget-controls">
                            <button class="widget-btn delete" onclick="deleteWidget(${widget.id})">🗑️</button>
                        </div>
                    </div>
                    <div class="gauge-widget">
                        <div class="gauge-container">
                            <svg class="gauge-svg" width="200" height="200">
                                <circle cx="100" cy="100" r="80" fill="none" stroke="#f0f0f0" stroke-width="20"/>
                                <circle id="gauge-fill-${widget.id}" cx="100" cy="100" r="80" fill="none" 
                                        stroke="#667eea" stroke-width="20" stroke-dasharray="502.4" 
                                        stroke-dashoffset="502.4" stroke-linecap="round"/>
                            </svg>
                            <div class="gauge-value" id="gauge-value-${widget.id}">-</div>
                        </div>
                        <div class="gauge-label">${widget.unit}</div>
                    </div>
                `;
                grid.appendChild(widgetDiv);
            } else if (widget.type === 'text') {
                widgetDiv.innerHTML = `
                    <div class="widget-header">
                        <div class="widget-title">${widget.title}</div>
                        <div class="widget-controls">
                            <button class="widget-btn delete" onclick="deleteWidget(${widget.id})">🗑️</button>
                        </div>
                    </div>
                    <div class="text-widget-content" id="text-value-${widget.id}">-</div>
                    <div class="text-widget-label">${widget.unit}</div>
                `;
                grid.appendChild(widgetDiv);
            }
            
            setupDragAndDrop(widgetDiv);
        }
        
        // Delete widget
        function deleteWidget(widgetId) {
            if (!confirm('Delete this widget?')) return;
            
            widgets = widgets.filter(w => w.id !== widgetId);
            document.getElementById(`widget-${widgetId}`)?.remove();
            
            if (charts[widgetId]) {
                charts[widgetId].destroy();
                delete charts[widgetId];
            }
            
            saveWidgetsToStorage();
        }
        
        // Clear all widgets
        function clearAllWidgets() {
            if (!confirm('Delete all widgets?')) return;
            
            widgets = [];
            document.getElementById('widgetGrid').innerHTML = '';
            Object.values(charts).forEach(chart => chart.destroy());
            charts = {};
            saveWidgetsToStorage();
        }
        
        // Update widgets with live data
        async function updateWidgets() {
            for (const widget of widgets) {
                try {
                    const response = await fetch(`/api/sensor/${widget.deviceId}`);
                    if (response.ok) {
                        const data = await response.json();
                        const value = parseFloat(data[widget.sensor]);
                        
                        if (!isNaN(value)) {
                            if (widget.type === 'chart') {
                                updateChart(widget.id, value);
                            } else if (widget.type === 'gauge') {
                                updateGauge(widget.id, value);
                            } else if (widget.type === 'text') {
                                updateText(widget.id, value);
                            }
                        }
                    }
                } catch (error) {
                    console.error(`Error updating widget ${widget.id}:`, error);
                }
            }
        }
        
        // Update chart
        function updateChart(widgetId, value) {
            const chart = charts[widgetId];
            if (!chart) return;
            
            const now = new Date().toLocaleTimeString();
            
            chart.data.labels.push(now);
            chart.data.datasets[0].data.push(value);
            
            // Keep last 20 points
            if (chart.data.labels.length > 20) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
            }
            
            chart.update('none');
        }
        
        // Update gauge
        function updateGauge(widgetId, value) {
            const valueEl = document.getElementById(`gauge-value-${widgetId}`);
            const fillEl = document.getElementById(`gauge-fill-${widgetId}`);
            
            if (valueEl) valueEl.textContent = value.toFixed(1);
            
            if (fillEl) {
                // Assume 0-100 range, adjust as needed
                const percentage = Math.min(Math.max(value, 0), 100) / 100;
                const circumference = 502.4;
                const offset = circumference * (1 - percentage);
                fillEl.style.strokeDashoffset = offset;
            }
        }
        
        // Update text widget
        function updateText(widgetId, value) {
            const valueEl = document.getElementById(`text-value-${widgetId}`);
            if (valueEl) valueEl.textContent = value.toFixed(1);
        }
        
        // Drag and drop
        function setupDragAndDrop(element) {
            element.addEventListener('dragstart', () => {
                element.classList.add('dragging');
            });
            
            element.addEventListener('dragend', () => {
                element.classList.remove('dragging');
            });
        }
        
        // Initialize
        loadDevices();
        loadWidgetsFromStorage();
        
        // Auto-refresh
        setInterval(() => {
            if (document.getElementById('autoRefresh').checked) {
                updateWidgets();
                loadDevices();
            }
        }, 2000);
        
        // Initial update
        setTimeout(updateWidgets, 500);
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("🚀 IoT Platform Server with Widgets Starting...")
    print("📊 Dashboard: http://localhost:5000")
    print("📡 API Endpoint: http://localhost:5000/api/sensor")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
