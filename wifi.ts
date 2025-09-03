/**
 * Functions to operate Grove module.
 */
let debugmode = 1
//% weight=10 color=#9F79EE icon="\uf1b3" block="WiFi"
namespace WiFi {
    let isWifiConnected = false
    let isMqttConnected = false
    serial.setRxBufferSize(192)
    serial.setTxBufferSize(64)
    serial.redirect(SerialPin.C17, SerialPin.C16, BaudRate.BaudRate115200);

    export function sendATCmd(cmd: string) {
        led.toggle(4, 0)
        if (debugmode) {
            serial.redirectToUSB()
            basic.pause(50)
            serial.writeString("CMD:" + cmd + "\r\n")
            basic.pause(50)
            serial.redirect(SerialPin.C17, SerialPin.C16, BaudRate.BaudRate115200);
        }
        serial.writeString(cmd + "\r\n")
        led.toggle(4, 0)
    }
    export function waitAtResponse(target1: string, target2: string, target3: string, timeout: number) {
        let start = input.runningTime()
        let result = 0
        let received = ""

        while (input.runningTime() - start < timeout && result == 0) {
            let line = serial.readString()
            if (line.length > 0) {
                received += line + "\n"

                if (line.includes(target1)) {
                    result = 1
                    break
                }
                if (line.includes(target2)) {
                    result = 2
                    break
                }
                if (line.includes(target3)) {
                    result = 3
                    break
                }
            }
            basic.pause(100)
        }

        if (debugmode) {
            serial.redirectToUSB()
            basic.pause(50)
            serial.writeString("RCV:" + received + " (result:" + result + ")\r\n")
            basic.pause(50)
            serial.redirect(SerialPin.C17, SerialPin.C16, BaudRate.BaudRate115200);
        }

        return result
    }
    /**
     * Setup Uart WiFi to connect to  Wi-Fi
     */
    //% block="Setup Wifi|TX %txPin|RX %rxPin|Baud rate %baudrate|SSID = %ssid|Password = %passwd"
    //% group="UartWiFi"
    //% txPin.defl=SerialPin.C17
    //% rxPin.defl=SerialPin.C16
    //% baudRate.defl=BaudRate.BaudRate115200
    export function setupWifi(txPin: SerialPin, rxPin: SerialPin, baudRate: BaudRate, ssid: string, passwd: string) {
        isWifiConnected = false
        let result = 0
        serial.redirect(
            txPin,
            rxPin,
            baudRate
        )
        basic.pause(1000)
        sendATCmd('AT')
        result = waitAtResponse("OK", "ERROR", "FAIL", 500)
        sendATCmd('AT+CWMODE=1')
        result = waitAtResponse("OK", "ERROR", "FAIL", 500)
        sendATCmd(`AT+CWJAP="${ssid}","${passwd}"`)
        result = waitAtResponse("WIFI GOT IP", "ERROR", "FAIL", 5000)
        if (result == 1) {
            isWifiConnected = true
            basic.showString("WIFI OK", 70)
        } else {    
            basic.showString("WIFI Failed", 70)
        }
    }

    /**
     * Check if Uart WiFi is connected to Wifi
     */
    //% block="Wifi OK?"
    //% group="UartWiFi"
    export function wifiOK() {
        return isWifiConnected
    }
    
    /**
     * Reset ESP32 module to factory defaults
     */
    //% block="Reset Module to Factory Defaults"
    //% group="UartWiFi"
    export function resetModule() {

        sendATCmd('AT+RESTORE')
        let result = waitAtResponse("OK", "ERROR", "FAIL", 3000)

        if (result == 1) {
            // Reset global connection status
            isWifiConnected = false
            isMqttConnected = false

            basic.showString("Reset OK", 70)
            basic.pause(3000) // Give device time to restart
        } else {
            basic.showString("Reset Failed", 70)
        }
    }
    /**
     * Setup MQTT connection with broker
     */
    //% block="Setup MQTT|Broker %broker|Port %port|Client ID %clientId|Username %username|Password %password|Topic %topic"
    //% group="UartWiFi"
    //% port.defl=1883
    //% clientId.defl="esp32c3_device"
    //% topic.defl="test/topic"
    export function setupMQTT(broker: string, port: number, clientId: string, username: string, password: string, topic: string) {
        let result = 0
        if (isMqttConnected == false){
    
            // Configure MQTT user settings
            sendATCmd(`AT+MQTTUSERCFG=0,1,"${clientId}","${username}","${password}",0,0,""`)
            result = waitAtResponse("OK", "ERROR", "FAIL", 2000)
            if (result != 1) {
                basic.showString("User CFG Failed", 70)
                return
            }

            // Set MQTT broker connection
            sendATCmd(`AT+MQTTCONN=0,"${broker}",${port},1`)
            result = waitAtResponse("OK", "ERROR", "FAIL", 5000)
            if (result == 1) {
                isMqttConnected = true
                basic.showString("MQTT OK", 70)
            }
            else {    
                basic.showString("MQTT Failed", 70)
                return
            }
        }
        else{
            basic.showString("MQTT already setup")
        }
    }

    /**
     * Publish message to MQTT topic
     */
    //% block="Publish MQTT|Topic %topic|Message %message"
    //% group="UartWiFi"
    export function publishMQTT(topic: string, message: string) {
        if (!isMqttConnected) {
            basic.showString("Not Connected", 70)
            return
        }

        sendATCmd(`AT+MQTTPUB=0,"${topic}","${message}",1,0`)
        let result = waitAtResponse("OK", "ERROR", "FAIL", 2000)
        if (result == 1) {
            basic.showIcon(IconNames.Yes)
        } else {
            basic.showIcon(IconNames.No)
        }
    }

    /**
     * Disconnect from MQTT broker
     */
    //% block="Disconnect MQTT"
    //% group="UartWiFi"
    export function disconnectMQTT() {
        sendATCmd('AT+MQTTCLEAN=0')
        waitAtResponse("OK", "ERROR", "FAIL", 2000)
        isMqttConnected = false
        basic.showString("Disconnected", 70)
    }

    /**
     * Check if MQTT is connected
     */
    //% block="MQTT Connected"
    //% group="UartWiFi"
    export function isMQTTConnected(): boolean {
        return isMqttConnected
    }

}
