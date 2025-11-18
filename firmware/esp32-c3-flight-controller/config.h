/**
 * Configuration file for ESP32-C3 Flight Controller
 *
 * IMPORTANT: Tune these values for your specific drone build!
 */

#ifndef CONFIG_H
#define CONFIG_H

// ============================================================================
// HARDWARE PIN CONFIGURATION
// ============================================================================

// Motor PWM outputs (GPIO pins)
#define MOTOR_1_PIN     2  // Front-left
#define MOTOR_2_PIN     3  // Front-right
#define MOTOR_3_PIN     4  // Back-right
#define MOTOR_4_PIN     5  // Back-left

// I2C for sensors
#define I2C_SDA_PIN     6
#define I2C_SCL_PIN     7

// Analog inputs
#define BATTERY_PIN     8  // Battery voltage monitor

// UART for telemetry (optional)
#define UART_TX_PIN     9
#define UART_RX_PIN     10

// Status LED
#define LED_PIN         LED_BUILTIN

// ============================================================================
// IMU CONFIGURATION
// ============================================================================

#define IMU_ADDRESS     0x68  // MPU6050 I2C address
#define GYRO_SCALE      250   // deg/s (250, 500, 1000, 2000)
#define ACCEL_SCALE     2     // g (2, 4, 8, 16)

// ============================================================================
// MOTOR/ESC CONFIGURATION
// ============================================================================

#define MOTOR_PWM_FREQUENCY   50    // Hz (standard for ESCs)
#define MOTOR_PWM_RESOLUTION  16    // bits (ESP32-C3 supports up to 20-bit)

// ESC pulse widths (microseconds)
#define ESC_MIN_PULSE    1000  // Minimum throttle
#define ESC_MAX_PULSE    2000  // Maximum throttle

// Motor throttle limits (0.0 to 1.0)
#define MOTOR_MIN_THROTTLE  0.0   // Motor off
#define MOTOR_IDLE_THROTTLE 0.05  // Minimum spin
#define MOTOR_MAX_THROTTLE  1.0   // Full power

// ============================================================================
// FLIGHT CONTROL PARAMETERS
// ============================================================================

// Maximum angles (radians)
#define MAX_TILT_ANGLE   0.524  // 30 degrees
#define MAX_RATE         3.14   // 180 deg/s

#define MAX_YAW_RATE     1.57   // 90 deg/s

// Angle to rate conversion
#define ANGLE_TO_RATE_GAIN  2.0

// Rate PID gains (TUNE THESE!)
#define RATE_P_GAIN      0.5
#define RATE_I_GAIN      0.1
#define RATE_D_GAIN      0.05

// Yaw PID gains
#define YAW_P_GAIN       1.0
#define YAW_I_GAIN       0.05
#define YAW_D_GAIN       0.0

// ============================================================================
// PID TUNING (Start with these, then tune!)
// ============================================================================

// Roll PID
#define PID_ROLL_P      1.5
#define PID_ROLL_I      0.0
#define PID_ROLL_D      0.3

// Pitch PID
#define PID_PITCH_P     1.5
#define PID_PITCH_I     0.0
#define PID_PITCH_D     0.3

// Yaw PID
#define PID_YAW_P       2.0
#define PID_YAW_I       0.0
#define PID_YAW_D       0.0

// Altitude PID (if using barometer)
#define PID_ALT_P       2.0
#define PID_ALT_I       0.5
#define PID_ALT_D       1.0

// ============================================================================
// ALTITUDE CONTROL
// ============================================================================

#define ALT_CLIMB_RATE  1.0   // m/s
#define MAX_ALTITUDE    50.0  // meters

// ============================================================================
// BATTERY MONITORING
// ============================================================================

#define VOLTAGE_DIVIDER_RATIO  3.3  // Adjust based on your voltage divider
#define LOW_BATTERY_VOLTAGE    10.5 // Volts (for 3S LiPo)
#define CRITICAL_BATTERY       9.9  // Volts

// ============================================================================
// COMMUNICATION
// ============================================================================

// WiFi credentials (for ground station)
#define WIFI_SSID       "DroneSwarm"
#define WIFI_PASSWORD   "SwarmControl123"

// ESP-NOW channel
#define ESPNOW_CHANNEL  1

// Telemetry rate
#define TELEMETRY_INTERVAL_MS  50  // 20 Hz

// UDP ports
#define TELEMETRY_PORT  14550
#define COMMAND_PORT    14551

// ============================================================================
// SWARM CONFIGURATION
// ============================================================================

#define DRONE_ID        1  // Unique ID for this drone (set differently for each)
#define MAX_SWARM_SIZE  20 // Maximum drones in swarm

// ============================================================================
// SAFETY LIMITS
// ============================================================================

#define MAX_LOOP_TIME_MS    10    // Emergency if loop takes longer
#define GEOFENCE_RADIUS     100.0 // meters
#define GEOFENCE_HEIGHT     50.0  // meters

// ============================================================================
// DEBUGGING
// ============================================================================

#define DEBUG_SERIAL    1  // Enable serial debug output
#define DEBUG_IMU       0  // Print IMU data
#define DEBUG_MOTORS    0  // Print motor outputs
#define DEBUG_PID       0  // Print PID values

#endif // CONFIG_H
