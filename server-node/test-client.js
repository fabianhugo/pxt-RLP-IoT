#!/usr/bin/env node
/**
 * Test client to verify server functionality
 */

const axios = require('axios');

const BASE_URL = process.env.BASE_URL || 'http://localhost:5000';
const DEVICE_ID = 'TestDevice001';

async function testServer() {
    console.log('🧪 Testing IoT Platform Server...\n');

    try {
        // Test 1: Server Status
        console.log('1️⃣ Testing server status...');
        const statusRes = await axios.get(`${BASE_URL}/api/status`);
        console.log('✅ Server status:', statusRes.data.status);
        console.log(`   Devices: ${statusRes.data.devices}, Data points: ${statusRes.data.total_data_points}\n`);

        // Test 2: Send Sensor Data
        console.log('2️⃣ Sending sensor data...');
        const sensorData = {
            device_id: DEVICE_ID,
            temperature: (20 + Math.random() * 10).toFixed(1),
            humidity: (50 + Math.random() * 20).toFixed(1),
            light: Math.floor(Math.random() * 1000)
        };
        const sendRes = await axios.post(`${BASE_URL}/api/sensor`, sensorData);
        console.log('✅ Data sent:', sendRes.data);
        console.log('   Sensor data:', sensorData, '\n');

        // Wait a bit for data to be stored
        await new Promise(resolve => setTimeout(resolve, 500));

        // Test 3: Get Sensor Data
        console.log('3️⃣ Retrieving sensor data...');
        const getRes = await axios.get(`${BASE_URL}/api/sensor/${DEVICE_ID}`);
        console.log('✅ Retrieved data:', getRes.data, '\n');

        // Test 4: Send Command
        console.log('4️⃣ Sending command...');
        const command = {
            device_id: DEVICE_ID,
            command: 'led_on',
            value: 'blue'
        };
        const cmdRes = await axios.post(`${BASE_URL}/api/command`, command);
        console.log('✅ Command sent:', cmdRes.data, '\n');

        // Test 5: Get Pending Commands
        console.log('5️⃣ Getting pending commands...');
        const cmdGetRes = await axios.get(`${BASE_URL}/api/command/${DEVICE_ID}`);
        console.log('✅ Pending command:', cmdGetRes.data, '\n');

        // Test 6: List All Devices
        console.log('6️⃣ Listing all devices...');
        const devicesRes = await axios.get(`${BASE_URL}/api/devices`);
        console.log(`✅ Found ${devicesRes.data.length} device(s)`);
        devicesRes.data.forEach(device => {
            console.log(`   - ${device.device_id} (${device.ip_address})`);
        });
        console.log();

        // Test 7: Get History
        console.log('7️⃣ Getting temperature history...');
        const historyRes = await axios.get(`${BASE_URL}/api/history/${DEVICE_ID}/temperature?limit=5`);
        console.log(`✅ Retrieved ${historyRes.data.length} history record(s)`);
        historyRes.data.forEach((record, i) => {
            console.log(`   ${i+1}. ${record.value}°C at ${record.timestamp}`);
        });
        console.log();

        console.log('🎉 All tests passed!');

    } catch (error) {
        if (error.response) {
            console.error('❌ Test failed:', error.response.status, error.response.data);
        } else {
            console.error('❌ Test failed:', error.message);
        }
        process.exit(1);
    }
}

// Run tests
testServer();
