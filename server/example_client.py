#!/usr/bin/env python3
"""
Example client to test the IoT Platform Server
Simulates a Calliope Mini device sending sensor data
"""

import requests
import time
import random
import json

# Server configuration
SERVER_URL = "http://localhost:5000"
DEVICE_ID = "TestDevice001"

def send_sensor_data(temperature, humidity, light):
    """Send sensor data to the server"""
    url = f"{SERVER_URL}/api/sensor"
    data = {
        "device_id": DEVICE_ID,
        "temperature": temperature,
        "humidity": humidity,
        "light": light
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"✓ Sent data: Temp={temperature}°C, Humidity={humidity}%, Light={light}")
        print(f"  Response: {response.json()}")
    except Exception as e:
        print(f"✗ Error sending data: {e}")

def get_commands():
    """Check for pending commands"""
    url = f"{SERVER_URL}/api/command/{DEVICE_ID}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            command = response.json()
            print(f"📨 Command received: {command['command']} = {command.get('value', '')}")
            return command
        elif response.status_code == 404:
            print("  No pending commands")
        return None
    except Exception as e:
        print(f"✗ Error getting commands: {e}")
        return None

def main():
    print(f"🚀 Starting IoT Client Simulator")
    print(f"📡 Server: {SERVER_URL}")
    print(f"🏷️  Device ID: {DEVICE_ID}")
    print("\nPress Ctrl+C to stop\n")
    
    cycle = 0
    
    try:
        while True:
            cycle += 1
            print(f"\n--- Cycle {cycle} ---")
            
            # Simulate sensor readings
            temperature = round(20 + random.uniform(-5, 10), 1)
            humidity = round(50 + random.uniform(-20, 30), 1)
            light = random.randint(0, 255)
            
            # Send data
            send_sensor_data(temperature, humidity, light)
            
            # Check for commands
            get_commands()
            
            # Wait before next cycle
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n👋 Client stopped")

if __name__ == "__main__":
    main()
