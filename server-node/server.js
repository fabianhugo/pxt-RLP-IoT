#!/usr/bin/env node
/**
 * IoT Platform Server for Calliope Mini - Node.js/Express Implementation
 * Provides REST API endpoints for sensor data collection and device control
 */

const express = require('express');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();
const expressWs = require('express-ws');
const path = require('path');
const fs = require('fs');

const app = express();
const wsInstance = expressWs(app);
const PORT = process.env.PORT || 5000;
const DB_PATH = process.env.DB_PATH || 'iot_data.db';

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Initialize Database
const db = new sqlite3.Database(DB_PATH);
db.run('PRAGMA journal_mode = WAL');

// Create tables if they don't exist
function initDatabase() {
    db.serialize(() => {
        // Sensor data table
        db.run(`
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                sensor_type TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        `);

        // Device commands table
        db.run(`
            CREATE TABLE IF NOT EXISTS device_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                command TEXT NOT NULL,
                value TEXT,
                executed INTEGER DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        `);

        // Device registry
        db.run(`
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                name TEXT,
                last_seen DATETIME,
                ip_address TEXT
            )
        `);

        // Create indexes for better performance
        db.run(`CREATE INDEX IF NOT EXISTS idx_sensor_device_timestamp 
                 ON sensor_data(device_id, timestamp DESC)`);
        
        db.run(`CREATE INDEX IF NOT EXISTS idx_sensor_device_type 
                 ON sensor_data(device_id, sensor_type, timestamp DESC)`);
        
        db.run(`CREATE INDEX IF NOT EXISTS idx_commands_device_executed 
                 ON device_commands(device_id, executed, timestamp ASC)`);

        console.log('✓ Database initialized');
    });
}

initDatabase();

// WebSocket connections for real-time updates
const wsClients = new Set();

// Broadcast sensor data to all connected WebSocket clients
function broadcastSensorData(deviceId, data) {
    const message = JSON.stringify({
        type: 'sensor_data',
        device_id: deviceId,
        data: data,
        timestamp: new Date().toISOString()
    });

    wsClients.forEach(ws => {
        if (ws.readyState === 1) { // OPEN
            ws.send(message);
        }
    });
}

// ==================== API Endpoints ====================

/**
 * Home - Serve Dashboard
 */
app.get('/', (req, res) => {
    const dashboardPath = path.join(__dirname, 'dashboard.html');
    if (fs.existsSync(dashboardPath)) {
        res.sendFile(dashboardPath);
    } else {
        res.send('<h1>IoT Platform Server</h1><p>Dashboard file not found. See /api/status for server info.</p>');
    }
});

/**
 * Server Status
 */
app.get('/api/status', (req, res) => {
    db.get('SELECT COUNT(*) as count FROM devices', (err, deviceCount) => {
        if (err) return res.status(500).json({ status: 'error', message: err.message });
        
        db.get('SELECT COUNT(*) as count FROM sensor_data', (err, dataCount) => {
            if (err) return res.status(500).json({ status: 'error', message: err.message });
            
            res.json({
                status: 'ok',
                server: 'IoT Platform - Node.js',
                version: '1.0.0',
                uptime: process.uptime(),
                devices: deviceCount.count,
                total_data_points: dataCount.count,
                websocket_clients: wsClients.size
            });
        });
    });
});

/**
 * POST /api/sensor - Receive sensor data from devices
 * Expected JSON: {"temperature": "25.3"} or {"device_id": "Device001", "temperature": "25.3"}
 */
app.post('/api/sensor', (req, res) => {
    const data = req.body;
    const clientIp = req.ip || req.connection.remoteAddress;
    const deviceId = data.device_id || clientIp;

    // Update device registry
    db.run(`INSERT OR REPLACE INTO devices (device_id, last_seen, ip_address)
            VALUES (?, datetime('now'), ?)`, [deviceId, clientIp], (err) => {
        if (err) {
            return res.status(400).json({ status: 'error', message: err.message });
        }

        // Store all sensor readings
        let storedCount = 0;
        const sensorData = {};
        const entries = Object.entries(data).filter(([key]) => key !== 'device_id');

        if (entries.length === 0) {
            return res.json({ status: 'ok', device_id: deviceId, records_stored: 0 });
        }

        entries.forEach(([key, value], index) => {
            const numericValue = parseFloat(value) || 0;
            
            db.run(`INSERT INTO sensor_data (device_id, sensor_type, value)
                    VALUES (?, ?, ?)`, [deviceId, key, numericValue], (err) => {
                if (err) {
                    console.error('Error inserting sensor data:', err);
                } else {
                    sensorData[key] = numericValue;
                    storedCount++;
                }

                // After last insert, send response
                if (index === entries.length - 1) {
                    // Broadcast to WebSocket clients
                    broadcastSensorData(deviceId, sensorData);

                    res.json({
                        status: 'ok',
                        device_id: deviceId,
                        records_stored: storedCount
                    });
                }
            });
        });
    });
});

/**
 * GET /api/sensor/:device_id - Get latest sensor data for a device
 * Returns: {"temperature": 25.3, "humidity": 60, "timestamp": "..."}
 */
app.get('/api/sensor/:device_id', (req, res) => {
    const { device_id } = req.params;

    // Get latest value for each sensor type
    db.all(`SELECT sensor_type, value, timestamp 
            FROM sensor_data 
            WHERE device_id = ?
            AND timestamp = (
                SELECT MAX(timestamp) 
                FROM sensor_data AS sd2 
                WHERE sd2.device_id = sensor_data.device_id 
                AND sd2.sensor_type = sensor_data.sensor_type
            )`, [device_id], (err, results) => {
        if (err) {
            return res.status(400).json({ status: 'error', message: err.message });
        }

        if (results.length === 0) {
            return res.status(404).json({ status: 'no_data' });
        }

        // Format response
        const data = {};
        results.forEach(row => {
            data[row.sensor_type] = row.value;
        });
        data.timestamp = results[0].timestamp;

        res.json(data);
    });
});

/**
 * GET /api/command/:device_id - Get pending commands for a device
 * Returns: {"command": "led_on", "value": "red"}
 */
app.get('/api/command/:device_id', (req, res) => {
    const { device_id } = req.params;

    // Get oldest unexecuted command
    db.get(`SELECT id, command, value 
            FROM device_commands 
            WHERE device_id = ? AND executed = 0
            ORDER BY timestamp ASC
            LIMIT 1`, [device_id], (err, result) => {
        if (err) {
            return res.status(400).json({ status: 'error', message: err.message });
        }

        if (result) {
            // Mark as executed
            db.run('UPDATE device_commands SET executed = 1 WHERE id = ?', [result.id], (err) => {
                if (err) {
                    return res.status(400).json({ status: 'error', message: err.message });
                }

                res.json({
                    command: result.command,
                    value: result.value || ''
                });
            });
        } else {
            res.status(404).json({ status: 'no_commands' });
        }
    });
});

/**
 * POST /api/command - Send command to device
 * Expected JSON: {"device_id": "Device001", "command": "led_on", "value": "red"}
 */
app.post('/api/command', (req, res) => {
    const { device_id, command, value } = req.body;

    if (!device_id || !command) {
        return res.status(400).json({
            status: 'error',
            message: 'device_id and command required'
        });
    }

    db.run(`INSERT INTO device_commands (device_id, command, value)
            VALUES (?, ?, ?)`, [device_id, command, value || ''], (err) => {
        if (err) {
            return res.status(400).json({ status: 'error', message: err.message });
        }

        res.json({
            status: 'ok',
            message: 'Command queued'
        });
    });
});

/**
 * GET /api/devices - Get list of all registered devices
 */
app.get('/api/devices', (req, res) => {
    db.all(`SELECT device_id, name, last_seen, ip_address 
            FROM devices
            ORDER BY last_seen DESC`, [], (err, rows) => {
        if (err) {
            return res.status(400).json({ status: 'error', message: err.message });
        }

        const devices = rows.map(row => ({
            device_id: row.device_id,
            name: row.name || row.device_id,
            last_seen: row.last_seen,
            ip_address: row.ip_address
        }));

        res.json(devices);
    });
});

/**
 * GET /api/history/:device_id/:sensor_type - Get historical data for a specific sensor
 */
app.get('/api/history/:device_id/:sensor_type', (req, res) => {
    const { device_id, sensor_type } = req.params;
    const limit = parseInt(req.query.limit) || 100;

    db.all(`SELECT value, timestamp 
            FROM sensor_data
            WHERE device_id = ? AND sensor_type = ?
            ORDER BY timestamp DESC
            LIMIT ?`, [device_id, sensor_type, limit], (err, rows) => {
        if (err) {
            return res.status(400).json({ status: 'error', message: err.message });
        }

        const data = rows.map(row => ({
            value: row.value,
            timestamp: row.timestamp
        }));

        res.json(data);
    });
});

/**
 * DELETE /api/data/:device_id - Delete all data for a device
 */
app.delete('/api/data/:device_id', (req, res) => {
    const { device_id } = req.params;

    db.serialize(() => {
        db.run('DELETE FROM sensor_data WHERE device_id = ?', [device_id]);
        db.run('DELETE FROM device_commands WHERE device_id = ?', [device_id]);
        db.run('DELETE FROM devices WHERE device_id = ?', [device_id], (err) => {
            if (err) {
                return res.status(400).json({ status: 'error', message: err.message });
            }

            res.json({
                status: 'ok',
                message: 'Device data deleted'
            });
        });
    });
});

// ==================== WebSocket Endpoint ====================

/**
 * WebSocket endpoint for real-time updates
 */
app.ws('/api/ws', (ws, req) => {
    console.log('WebSocket client connected');
    wsClients.add(ws);

    ws.on('message', (msg) => {
        try {
            const data = JSON.parse(msg);
            console.log('WebSocket received:', data);
            // Handle client messages if needed
        } catch (err) {
            console.error('WebSocket message error:', err);
        }
    });

    ws.on('close', () => {
        console.log('WebSocket client disconnected');
        wsClients.delete(ws);
    });

    // Send welcome message
    ws.send(JSON.stringify({
        type: 'connected',
        message: 'Connected to IoT Platform WebSocket'
    }));
});

// ==================== Error Handling ====================

app.use((err, req, res, next) => {
    console.error('Server error:', err);
    res.status(500).json({
        status: 'error',
        message: 'Internal server error'
    });
});

// ==================== Start Server ====================

app.listen(PORT, () => {
    console.log(`
╔═══════════════════════════════════════════════════════════╗
║         IoT Platform Server - Node.js/Express             ║
║                                                           ║
║  Server running on: http://localhost:${PORT}                ║
║  WebSocket endpoint: ws://localhost:${PORT}/api/ws          ║
║                                                           ║
║  API Endpoints:                                           ║
║  • POST   /api/sensor         - Receive sensor data      ║
║  • GET    /api/sensor/:id     - Get device data          ║
║  • POST   /api/command        - Send command             ║
║  • GET    /api/command/:id    - Get pending commands     ║
║  • GET    /api/devices        - List all devices         ║
║  • GET    /api/history/:id/:type - Get sensor history    ║
║  • GET    /api/status         - Server status            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    `);
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\nShutting down gracefully...');
    db.close();
    process.exit(0);
});
