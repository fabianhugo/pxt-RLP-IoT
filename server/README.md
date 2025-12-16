# IoT Platform Server for Calliope Mini

A lightweight, self-hosted IoT platform for collecting sensor data and controlling devices via TCP/IP.

## Features

- 📊 **REST API** for sensor data collection
- 🎮 **Command control** system for remote device control
- 📈 **Real-time dashboard** with device monitoring
- 💾 **SQLite database** for data persistence
- 🌐 **Multi-device support** with automatic registration
- 📱 **Responsive web interface**

## Quick Start

### 1. Install Dependencies

```bash
cd server
pip install -r requirements.txt
```

Or install manually:
```bash
pip install Flask flask-cors
```

### 2. Start Server

```bash
python server.py
```

The server will start on `http://localhost:5000`

### 3. Access Dashboard

Open your browser: `http://localhost:5000`

## API Endpoints

### Send Sensor Data (POST)
```
POST /api/sensor
Content-Type: application/json

{
  "device_id": "Device001",
  "temperature": "25.3",
  "humidity": "60"
}
```

### Get Latest Sensor Data (GET)
```
GET /api/sensor/{device_id}

Response:
{
  "temperature": "25.3",
  "humidity": "60",
  "timestamp": "2025-12-16 14:30:00"
}
```

### Send Command to Device (POST)
```
POST /api/command
Content-Type: application/json

{
  "device_id": "Device001",
  "command": "led_on",
  "value": "red"
}
```

### Get Pending Commands (GET)
```
GET /api/command/{device_id}

Response:
{
  "command": "led_on",
  "value": "red"
}
```

### List All Devices (GET)
```
GET /api/devices

Response: [
  {
    "device_id": "Device001",
    "name": "Device001",
    "last_seen": "2025-12-16 14:30:00",
    "ip_address": "192.168.1.100"
  }
]
```

### Get Sensor History (GET)
```
GET /api/history/{device_id}/{sensor_type}?limit=100

Response: [
  {"value": 25.3, "timestamp": "2025-12-16 14:30:00"},
  {"value": 25.1, "timestamp": "2025-12-16 14:29:00"}
]
```

## Using with Calliope Mini

### Example 1: Send Temperature Data

```typescript
// In MakeCode, use these blocks:

// Connect to WiFi
WiFi.setupWifi("YOUR_SSID", "YOUR_PASSWORD")

// Send sensor data
input.onButtonPressed(Button.A, function () {
    let temp = input.temperature()
    WiFi.sendSensorData(
        "192.168.1.100",  // Your server IP
        5000,              // Port
        "/api/sensor",
        "temperature",
        "" + temp
    )
})
```

### Example 2: Full JSON POST

```typescript
basic.forever(function () {
    let temp = input.temperature()
    let light = input.lightLevel()
    
    let jsonData = "{\"device_id\":\"Device001\",\"temperature\":\"" + temp + "\",\"light\":\"" + light + "\"}"
    
    WiFi.httpPOST(
        "192.168.1.100",
        5000,
        "/api/sensor",
        jsonData
    )
    
    basic.pause(10000)  // Send every 10 seconds
})
```

### Example 3: Receive Commands

```typescript
basic.forever(function () {
    WiFi.httpGET(
        "192.168.1.100",
        5000,
        "/api/command/Device001"
    )
    
    let response = WiFi.getLastTCPData()
    
    if (response.includes("led_on")) {
        // Turn on LED
        basic.showIcon(IconNames.Heart)
    } else if (response.includes("led_off")) {
        // Turn off LED
        basic.clearScreen()
    }
    
    basic.pause(5000)  // Check every 5 seconds
})
```

## Network Setup

### Running on Local Network

1. Find your computer's IP address:
   - **Linux/Mac**: `ip addr` or `ifconfig`
   - **Windows**: `ipconfig`

2. Use this IP in your Calliope blocks instead of `localhost`

3. Make sure firewall allows port 5000

### Running on Internet (with port forwarding)

1. Forward port 5000 on your router
2. Use your public IP or domain name
3. Consider using HTTPS/SSL in production

### Running on Raspberry Pi

```bash
# Install Python and pip
sudo apt update
sudo apt install python3 python3-pip

# Install dependencies
pip3 install Flask flask-cors

# Run server
python3 server.py
```

Server will be accessible at `http://<raspberry-pi-ip>:5000`

## Database

Data is stored in `iot_data.db` (SQLite) with three tables:

- **sensor_data**: All sensor readings with timestamps
- **device_commands**: Command queue for devices
- **devices**: Registered devices and their status

## Customization

### Change Port

Edit `server.py` line 371:
```python
app.run(host='0.0.0.0', port=YOUR_PORT, debug=True)
```

### Add Authentication

Add basic auth to protect endpoints:
```python
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    return username == "admin" and password == "secret"

@app.route('/api/sensor', methods=['POST'])
@auth.login_required
def receive_sensor_data():
    # ...
```

### Add HTTPS

Use a reverse proxy like nginx, or run with SSL:
```python
app.run(host='0.0.0.0', port=5000, 
        ssl_context=('cert.pem', 'key.pem'))
```

## Troubleshooting

**Device not appearing in dashboard?**
- Check if data is being received: look at server console logs
- Verify IP address and port are correct
- Check firewall settings

**"Connection refused" error?**
- Make sure server is running
- Verify you're using correct IP (not localhost from Calliope)
- Check if port 5000 is available

**Data not saving?**
- Check write permissions for `iot_data.db`
- Verify JSON format is correct
- Check server console for error messages

## Production Deployment

For production use, consider:

1. **Use a production WSGI server** (Gunicorn, uWSGI)
2. **Add authentication** and API keys
3. **Use HTTPS** for secure communication
4. **Set up proper logging** and monitoring
5. **Use PostgreSQL** instead of SQLite for better performance
6. **Add rate limiting** to prevent abuse
7. **Deploy on cloud** (Heroku, DigitalOcean, AWS)

## License

MIT License - See LICENSE file for details
