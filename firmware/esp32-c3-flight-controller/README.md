# ESP32-C3 Flight Controller Firmware

Complete flight controller firmware for ESP32-C3 based quadcopter drones with swarm capabilities.

## 🚁 Features

### Flight Control
- **500 Hz control loop** - Fast, responsive flight
- **Stabilize mode** - Angle-based stabilization
- **Altitude hold** - Maintain height (requires barometer)
- **Position hold** - GPS-based position lock
- **Autonomous mode** - Swarm control integration

### Sensors
- **MPU6050/MPU9250 IMU** - 6-axis gyro + accel
- **Complementary filter** - Attitude estimation
- **Optional barometer** - Altitude sensing
- **Battery monitoring** - Low voltage warning

### Communication
- **WiFi** - Ground station link
- **ESP-NOW** - Inter-drone communication (future)
- **UDP telemetry** - Real-time data streaming
- **Command protocol** - Remote control

### Safety
- **Arm/disarm** - Motor safety interlocks
- **Battery monitoring** - Auto-land on low voltage
- **Watchdog** - Auto-disarm if loop fails
- **Geofencing** - Stay within boundaries

## 📋 Hardware Requirements

### Required Components
- **ESP32-C3 Mini** development board
- **MPU6050** or **MPU9250** IMU (I2C)
- **4x ESCs** (Electronic Speed Controllers) - 20A+ recommended
- **4x Brushless motors** - 2204-2206 size typical
- **4x Propellers** - 5-6 inch
- **LiPo battery** - 3S (11.1V) or 4S (14.8V), 1300-2200mAh
- **Power distribution board** or **PDB**
- **Frame** - 210-250mm quadcopter frame

### Optional Components
- **BMP280/BMP388** barometer - Altitude hold
- **GPS module** - Position hold
- **Telemetry radio** - Long-range control
- **FPV camera** - First-person view

## 📐 Wiring Diagram

```
ESP32-C3 Mini Connections:
═══════════════════════════════════

GPIO 2  →  ESC 1 Signal (Front-Left Motor)
GPIO 3  →  ESC 2 Signal (Front-Right Motor)
GPIO 4  →  ESC 3 Signal (Back-Right Motor)
GPIO 5  →  ESC 4 Signal (Back-Left Motor)

GPIO 6  →  I2C SDA (MPU6050)
GPIO 7  →  I2C SCL (MPU6050)

GPIO 8  →  Battery Voltage (via voltage divider)

3.3V    →  MPU6050 VCC
GND     →  MPU6050 GND, ESC GND

Battery (+) → PDB → ESCs → Motors
Battery (-) → PDB GND → ESP32 GND
```

### Voltage Divider for Battery Monitor
```
Battery+ ──[10kΩ]──┬──[3.3kΩ]── GND
                   │
                   └─→ GPIO 8 (ESP32-C3)

For 4S (16.8V max): Ratio = 5.06
For 3S (12.6V max): Ratio = 3.82
```

## 🔧 Setup Instructions

### 1. Install Arduino IDE
Download and install Arduino IDE 2.0 or later.

### 2. Add ESP32 Board Support
- Open Arduino IDE
- Go to File → Preferences
- Add to "Additional Board Manager URLs":
  ```
  https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
  ```
- Go to Tools → Board → Boards Manager
- Search for "esp32" and install "esp32 by Espressif Systems"

### 3. Install Libraries
Go to Tools → Manage Libraries and install:
- **ESP32Servo** by Kevin Harrington
- **WiFi** (built-in with ESP32 core)
- **Wire** (built-in)

### 4. Configure Board
- Select Board: **Tools → Board → ESP32 → ESP32C3 Dev Module**
- Select Port: **Tools → Port** → (your ESP32-C3 port)
- Upload Speed: **921600**

### 5. Configure Firmware
Edit `config.h`:
```cpp
// Set your WiFi credentials
#define WIFI_SSID       "YourWiFiNetwork"
#define WIFI_PASSWORD   "YourPassword"

// Set unique drone ID (different for each drone!)
#define DRONE_ID        1  // Change to 2, 3, 4... for each drone

// Tune PID values for your drone
#define PID_ROLL_P      1.5  // Start here, tune later
#define PID_ROLL_I      0.0
#define PID_ROLL_D      0.3
```

### 6. ESC Calibration (IMPORTANT!)
**Only do this ONCE per ESC set:**

1. Disconnect battery
2. Connect ESP32-C3 via USB
3. In `setup()`, uncomment:
   ```cpp
   motors.calibrate();
   ```
4. Upload code
5. Follow serial monitor instructions
6. After calibration, comment out `motors.calibrate()` and re-upload

### 7. IMU Calibration
1. Place drone on level surface
2. Keep it completely still
3. Power on drone
4. Firmware will auto-calibrate (takes 3 seconds)
5. LED will indicate ready

### 8. Upload Firmware
- Connect ESP32-C3 via USB
- Click Upload button (→)
- Wait for "Done uploading" message

## 🎮 Flying Your Drone

### First Flight Checklist
1. ✅ ESCs calibrated
2. ✅ IMU calibrated
3. ✅ Motors spin correct direction (see below)
4. ✅ Propellers mounted correctly (check rotation)
5. ✅ Battery fully charged
6. ✅ Open area, no obstacles
7. ✅ Serial monitor connected (for safety)

### Motor Direction Test
```
Without propellers, send ARM command:
- M1 should spin (front-left)
- M2 should spin (front-right)
- M3 should spin (back-right)
- M4 should spin (back-left)

If wrong, swap any 2 motor wires on the ESC
```

### Propeller Installation
```
        FRONT
    M1(CCW)  M2(CW)
       \  X  /
        \|X|/
       / X  \
    M4(CW)  M3(CCW)
        BACK

CCW = Counter-clockwise propeller
CW  = Clockwise propeller
```

### Flight Modes

**DISARMED** (Default)
- Motors off
- Safe to handle
- LED blinking slowly

**STABILIZE**
- Self-leveling
- Manual throttle control
- Good for learning

**ALT_HOLD** (Needs barometer)
- Maintains altitude
- Easier to fly

**AUTONOMOUS**
- Swarm control
- Hide-and-seek game
- Formation flying

## 📡 Communication Protocol

### Send Commands (from Python/Ground Station)
```python
import socket
import struct

# Connect to drone
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
drone_ip = "192.168.1.100"  # Drone's IP address

# ARM command
cmd_type = 1  # CMD_ARM
sock.sendto(struct.pack('B', cmd_type), (drone_ip, 14551))

# Control input
cmd_type = 4  # CMD_CONTROL_INPUT
roll, pitch, yaw, throttle = 0.0, 0.0, 0.0, 0.5
data = struct.pack('Bffff', cmd_type, roll, pitch, yaw, throttle)
sock.sendto(data, (drone_ip, 14551))
```

### Receive Telemetry
```python
import socket
import struct

# Listen for telemetry
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 14550))

while True:
    data, addr = sock.recvfrom(1024)
    # Unpack telemetry packet
    timestamp, roll, pitch, yaw, alt, battery, armed, mode = \
        struct.unpack('Iffffffbi', data)

    print(f"Drone: Roll={roll:.2f} Pitch={pitch:.2f} Alt={alt:.2f}m Battery={battery:.1f}V")
```

## ⚙️ PID Tuning Guide

### When to Tune
- Drone wobbles or oscillates
- Sluggish response
- Overshoots when tilting

### Tuning Process
1. **Start with all gains at 0**
2. **Increase P gain** until oscillation starts
3. **Reduce P by 20%**
4. **Increase D gain** to dampen oscillations
5. **Add small I gain** only if drift occurs

### Typical Values (starting point)
```cpp
// Roll/Pitch
P: 1.0 - 2.0
I: 0.0 - 0.1
D: 0.2 - 0.5

// Yaw
P: 2.0 - 4.0
I: 0.0
D: 0.0
```

## 🔍 Troubleshooting

### Motors don't spin
- Check ESC calibration
- Verify battery voltage
- Check ARM command sent
- Ensure throttle > 0

### Drone flips on takeoff
- Check motor directions
- Verify propeller installation
- Check IMU orientation
- Recalibrate IMU

### Oscillates/wobbles
- Reduce P gain
- Increase D gain
- Check propeller balance
- Verify frame rigidity

### Drifts to one side
- Recalibrate IMU on level surface
- Check motor/propeller condition
- Add small I gain
- Verify CG (center of gravity)

### WiFi won't connect
- Check SSID/password in config.h
- Verify router is 2.4GHz (not 5GHz)
- Check serial monitor for IP address
- Reduce distance to router

## 🔐 Safety Features

### Automatic Disarm
- Low battery (< 10.5V for 3S)
- Loop failure (> 10ms)
- Lost communication (> 2 seconds)
- Geofence violation

### Manual Disarm
- Send DISARM command
- Remove battery

## 📊 Performance Specs

- **Control loop**: 500 Hz (2ms)
- **Telemetry rate**: 20 Hz (50ms)
- **WiFi latency**: ~10-20ms
- **IMU rate**: 1000 Hz
- **Motor update**: 50 Hz (ESC standard)

## 🚀 Next Steps

### Integration with Swarm Logic
See `../../hardware/esp32_interface.py` for Python interface.

### Add GPS Module
Uncomment GPS code in main sketch, connect to UART.

### Add FPV Camera
Use analog camera with 5.8GHz transmitter.

### Build Swarm
Flash firmware to multiple ESP32-C3 with unique IDs.

---

## ⚠️ SAFETY WARNING

**NEVER:**
- Fly near people or animals
- Fly indoors without prop guards
- Touch spinning propellers
- Fly with damaged parts
- Fly in rain or wet conditions
- Fly beyond visual line of sight

**ALWAYS:**
- Remove propellers when testing
- Use prop guards for indoor flight
- Keep spare propellers
- Monitor battery voltage
- Have fire extinguisher nearby (LiPo safety)
- Follow local regulations

---

## 📝 License

This code is provided as-is for educational and research purposes.
Use at your own risk. Always follow safety guidelines.

Happy flying! 🚁✨
