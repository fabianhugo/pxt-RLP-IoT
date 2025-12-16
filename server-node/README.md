# IoT Platform Server - Node.js/Express

Modern, high-performance IoT platform for Calliope Mini WiFi modules with real-time WebSocket support.

## ✨ Features

- 🚀 **High Performance** - Node.js async I/O handles many concurrent connections
- ⚡ **Real-time Updates** - WebSocket support for live sensor data streaming
- 📊 **REST API** - Complete HTTP API for sensor data and device control
- 💾 **SQLite Database** - Fast, reliable local data storage with WAL mode
- 🎨 **Modern Dashboard** - Responsive web interface with live updates
- 🔒 **CORS Enabled** - Ready for cross-origin requests
- 📈 **Indexed Queries** - Optimized database performance

## 🚀 Quick Start

### 1. Install Node.js

Make sure you have Node.js 14+ installed:
```bash
node --version
```

### 2. Install Dependencies

```bash
cd server-node
npm install
```

### 3. Start Server

```bash
npm start
```

Or with auto-reload during development:
```bash
npm run dev
```

The server will start on **http://localhost:5000**

### 4. Access Dashboard

Open your browser: **http://localhost:5000**

## 📡 API Endpoints

### Sensor Data

#### POST /api/sensor
Receive sensor data from devices.

**Request:**
```json
{
  "device_id": "Device001",
  "temperature": "25.3",
  "humidity": "60",
  "light": "450"
}
```

**Response:**
```json
{
  "status": "ok",
  "device_id": "Device001",
  "records_stored": 3
}
```

**Note:** `device_id` is optional. If not provided, the client IP will be used.

#### GET /api/sensor/:device_id
Get latest sensor readings for a device.

**Response:**
```json
{
  "temperature": 25.3,
  "humidity": 60,
  "light": 450,
  "timestamp": "2025-12-16 14:30:00"
}
```

### Device Commands

#### POST /api/command
Send a command to a device.

**Request:**
```json
{
  "device_id": "Device001",
  "command": "led_on",
  "value": "red"
}
```

**Response:**
```json
{
  "status": "ok",
  "message": "Command queued"
}
```

#### GET /api/command/:device_id
Get pending commands for a device (marks as executed).

**Response:**
```json
{
  "command": "led_on",
  "value": "red"
}
```

Or if no commands:
```json
{
  "status": "no_commands"
}
```

### Device Management

#### GET /api/devices
List all registered devices.

**Response:**
```json
[
  {
    "device_id": "Device001",
    "name": "Device001",
    "last_seen": "2025-12-16 14:30:00",
    "ip_address": "192.168.1.100"
  }
]
```

#### GET /api/history/:device_id/:sensor_type
Get historical data for a specific sensor.

**Query Parameters:**
- `limit` - Number of records (default: 100)

**Example:** `/api/history/Device001/temperature?limit=50`

**Response:**
```json
[
  {
    "value": 25.3,
    "timestamp": "2025-12-16 14:30:00"
  },
  {
    "value": 25.1,
    "timestamp": "2025-12-16 14:29:00"
  }
]
```

#### DELETE /api/data/:device_id
Delete all data for a specific device.

**Response:**
```json
{
  "status": "ok",
  "message": "Device data deleted"
}
```

### Server Info

#### GET /api/status
Get server status and statistics.

**Response:**
```json
{
  "status": "ok",
  "server": "IoT Platform - Node.js",
  "version": "1.0.0",
  "uptime": 3600,
  "devices": 5,
  "total_data_points": 1250,
  "websocket_clients": 2
}
```

## 🔌 WebSocket API

Connect to `ws://localhost:5000/api/ws` for real-time sensor data updates.

**Message Format (Incoming):**
```json
{
  "type": "sensor_data",
  "device_id": "Device001",
  "data": {
    "temperature": 25.3,
    "humidity": 60
  },
  "timestamp": "2025-12-16T14:30:00.000Z"
}
```

## 🎯 Usage Examples

### Calliope Mini (MakeCode)

Using the improved WiFi driver:

```typescript
// Connect to WiFi
WiFi.setupWifi("YourSSID", "YourPassword")

// Send sensor data
WiFi.sendSensorData("192.168.1.100", 5000, "/api/sensor", "temperature", "25.3")

// Check HTTP response
if (WiFi.isHttpSuccess()) {
    basic.showIcon(IconNames.Yes)
} else {
    basic.showNumber(WiFi.getLastHttpStatus())
}

// Get response body
let response = WiFi.getLastHttpBody()
```

### cURL Examples

**Send sensor data:**
```bash
curl -X POST http://localhost:5000/api/sensor \
  -H "Content-Type: application/json" \
  -d '{"device_id":"Device001","temperature":"25.3","humidity":"60"}'
```

**Get device data:**
```bash
curl http://localhost:5000/api/sensor/Device001
```

**Send command:**
```bash
curl -X POST http://localhost:5000/api/command \
  -H "Content-Type: application/json" \
  -d '{"device_id":"Device001","command":"led_on","value":"red"}'
```

**Check for pending commands:**
```bash
curl http://localhost:5000/api/command/Device001
```

### Python Client Example

```python
import requests
import json

# Send sensor data
data = {
    "device_id": "Device001",
    "temperature": "25.3",
    "humidity": "60"
}
response = requests.post('http://localhost:5000/api/sensor', json=data)
print(response.json())

# Get latest data
response = requests.get('http://localhost:5000/api/sensor/Device001')
print(response.json())
```

### JavaScript/Node.js Client Example

```javascript
const axios = require('axios');

// Send sensor data
async function sendSensorData() {
  const response = await axios.post('http://localhost:5000/api/sensor', {
    device_id: 'Device001',
    temperature: '25.3',
    humidity: '60'
  });
  console.log(response.data);
}

// WebSocket client
const WebSocket = require('ws');
const ws = new WebSocket('ws://localhost:5000/api/ws');

ws.on('message', (data) => {
  const message = JSON.parse(data);
  console.log('Received:', message);
});
```

## 🔧 Configuration

### Environment Variables

- `PORT` - Server port (default: 5000)
- `DB_PATH` - SQLite database file path (default: iot_data.db)

**Example:**
```bash
PORT=8080 DB_PATH=/data/iot.db npm start
```

### Database

The server uses SQLite with Write-Ahead Logging (WAL) for better concurrent performance. The database file is created automatically on first run.

**Location:** `iot_data.db` (in server-node directory)

To reset the database:
```bash
rm iot_data.db
npm start  # Will recreate automatically
```

## 🆚 Node.js vs Python Comparison

| Feature | Node.js (This) | Python (Flask) |
|---------|----------------|----------------|
| Async I/O | ✅ Native | ⚠️ Requires async libs |
| WebSockets | ✅ Built-in | ❌ Requires extension |
| Concurrent Connections | ✅ Excellent | ⚠️ Limited |
| Real-time Updates | ✅ Native | ⚠️ Polling needed |
| Memory Usage | ✅ Lower | ⚠️ Higher |
| Deployment | ✅ Easy (PM2) | ✅ Easy (gunicorn) |
| Learning Curve | JavaScript | Python |

## 📦 Dependencies

- **express** - Web framework
- **cors** - Cross-origin resource sharing
- **better-sqlite3** - Fast SQLite database
- **express-ws** - WebSocket support

## 🔒 Security Notes

For production deployment:
- Add authentication (JWT, API keys)
- Enable HTTPS/WSS
- Implement rate limiting
- Validate all inputs
- Use environment variables for sensitive data

## 🚢 Deployment

### Using PM2 (Recommended)

```bash
npm install -g pm2
pm2 start server.js --name iot-platform
pm2 save
pm2 startup
```

### Using systemd

Create `/etc/systemd/system/iot-platform.service`:
```ini
[Unit]
Description=IoT Platform Server
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/server-node
ExecStart=/usr/bin/node server.js
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable iot-platform
sudo systemctl start iot-platform
```

## 🐛 Troubleshooting

**Port already in use:**
```bash
# Change port
PORT=8080 npm start
```

**Database locked:**
- Ensure only one server instance is running
- Check file permissions

**WebSocket connection failed:**
- Check firewall settings
- Verify WebSocket support in proxy/load balancer

## 📝 License

MIT

## 🤝 Contributing

Improvements and bug reports welcome!

---

Made with ❤️ for Calliope Mini IoT Projects
