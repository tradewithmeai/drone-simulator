/**
 * ESP32-C3 Quadcopter Flight Controller
 *
 * Hardware Requirements:
 * - ESP32-C3 Mini board
 * - MPU6050 or MPU9250 IMU (I2C)
 * - 4x ESCs (Electronic Speed Controllers)
 * - 4x Brushless motors
 * - LiPo battery (3S or 4S)
 * - Optional: Barometer (BMP280/BMP388)
 * - Optional: Magnetometer (if not using MPU9250)
 *
 * Pin Configuration:
 * - GPIO 2,3,4,5: Motor PWM outputs (M1-M4)
 * - GPIO 6,7: I2C (SDA, SCL) for IMU
 * - GPIO 8: Battery voltage monitor
 * - GPIO 9,10: UART for telemetry (optional)
 *
 * Frame: X-configuration quadcopter
 *
 *        FRONT
 *     M1 ---- M2
 *      \  X  /
 *       \ | /
 *        \|/
 *     M4 ---- M3
 *        BACK
 */

#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include "config.h"
#include "imu.h"
#include "motors.h"
#include "pid.h"
#include "communication.h"
#include "filters.h"

// ============================================================================
// GLOBAL STATE
// ============================================================================

// Flight state
enum FlightMode {
  MODE_DISARMED,
  MODE_ARMED,
  MODE_STABILIZE,
  MODE_ALT_HOLD,
  MODE_POS_HOLD,
  MODE_AUTONOMOUS
};

FlightMode currentMode = MODE_DISARMED;
bool motorsArmed = false;

// Sensor data
IMU imu;
Vector3 gyro;           // rad/s
Vector3 accel;          // m/s²
Vector3 mag;            // μT
Quaternion attitude;    // Orientation
Vector3 eulerAngles;    // roll, pitch, yaw (rad)

// Control inputs (from radio or autonomous controller)
struct ControlInputs {
  float roll;           // -1.0 to 1.0
  float pitch;          // -1.0 to 1.0
  float yaw;            // -1.0 to 1.0
  float throttle;       // 0.0 to 1.0
} controlInputs;

// Position/velocity (from external source or GPS)
Vector3 position;       // meters (x, y, z)
Vector3 velocity;       // m/s
float altitude;         // meters
bool hasPositionFix = false;

// PID Controllers
PIDController pidRoll(PID_ROLL_P, PID_ROLL_I, PID_ROLL_D);
PIDController pidPitch(PID_PITCH_P, PID_PITCH_I, PID_PITCH_D);
PIDController pidYaw(PID_YAW_P, PID_YAW_I, PID_YAW_D);
PIDController pidAltitude(PID_ALT_P, PID_ALT_I, PID_ALT_D);

// Motor outputs
Motors motors;
float motorPWM[4] = {0, 0, 0, 0};

// Timing
unsigned long lastLoopTime = 0;
unsigned long loopTime = 0;
float dt = 0.0;

// Communication
Communication comm;

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n\n");
  Serial.println("========================================");
  Serial.println("ESP32-C3 Flight Controller");
  Serial.println("========================================");

  // Initialize I2C for sensors
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  Wire.setClock(400000); // 400kHz I2C

  // Initialize IMU
  Serial.print("Initializing IMU... ");
  if (!imu.begin()) {
    Serial.println("FAILED!");
    Serial.println("Check IMU connections!");
    while (1) {
      digitalWrite(LED_PIN, !digitalRead(LED_PIN));
      delay(100);
    }
  }
  Serial.println("OK");

  // Calibrate IMU (drone must be level!)
  Serial.println("Calibrating IMU - Keep drone LEVEL and STILL!");
  delay(2000);
  imu.calibrate();
  Serial.println("Calibration complete!");

  // Initialize motors (ESCs need calibration on first use)
  Serial.print("Initializing motors... ");
  motors.begin();
  Serial.println("OK");

  // Initialize communication (WiFi/ESP-NOW)
  Serial.print("Initializing communication... ");
  comm.begin();
  Serial.println("OK");

  // Set up status LED
  pinMode(LED_PIN, OUTPUT);

  // Initialize filters
  attitude = Quaternion(1, 0, 0, 0); // Identity quaternion

  Serial.println("========================================");
  Serial.println("Flight controller ready!");
  Serial.println("Send ARM command to enable motors");
  Serial.println("========================================\n");

  lastLoopTime = micros();
}

// ============================================================================
// MAIN LOOP (Target: 500 Hz / 2ms)
// ============================================================================

void loop() {
  // Timing
  unsigned long currentTime = micros();
  loopTime = currentTime - lastLoopTime;
  lastLoopTime = currentTime;
  dt = loopTime / 1000000.0; // Convert to seconds

  // Ensure minimum loop time (safety)
  if (dt > 0.02) dt = 0.02; // Cap at 50Hz if loop is slow

  // ========== 1. READ SENSORS ==========
  readSensors();

  // ========== 2. STATE ESTIMATION ==========
  updateAttitudeEstimate();

  // ========== 3. RECEIVE COMMANDS ==========
  receiveCommands();

  // ========== 4. FLIGHT CONTROL ==========
  runFlightController();

  // ========== 5. MOTOR MIXING ==========
  mixMotors();

  // ========== 6. OUTPUT TO MOTORS ==========
  motors.setAll(motorPWM);

  // ========== 7. SEND TELEMETRY ==========
  sendTelemetry();

  // ========== 8. STATUS LED ==========
  updateStatusLED();

  // Loop timing debug (every 1s)
  static unsigned long lastPrintTime = 0;
  if (currentTime - lastPrintTime > 1000000) {
    float loopFreq = 1.0 / dt;
    Serial.printf("Loop: %.1f Hz | Mode: %d | Armed: %d\n",
                  loopFreq, currentMode, motorsArmed);
    lastPrintTime = currentTime;
  }
}

// ============================================================================
// SENSOR READING
// ============================================================================

void readSensors() {
  // Read IMU
  imu.update();
  gyro = imu.getGyro();
  accel = imu.getAccel();
  mag = imu.getMag();

  // Read battery voltage
  float batteryVoltage = analogRead(BATTERY_PIN) * (3.3 / 4095.0) * VOLTAGE_DIVIDER_RATIO;

  // Low battery warning
  if (batteryVoltage < LOW_BATTERY_VOLTAGE && motorsArmed) {
    Serial.println("WARNING: LOW BATTERY!");
    // Could auto-land here
  }
}

// ============================================================================
// ATTITUDE ESTIMATION (Complementary Filter)
// ============================================================================

void updateAttitudeEstimate() {
  // Simple complementary filter: 98% gyro, 2% accel
  // For production, use Madgwick or Mahony filter

  // Integrate gyro for attitude change
  Vector3 gyroRate = gyro * dt;

  // Gyro integration (quaternion)
  Quaternion gyroQuat = Quaternion::fromEuler(gyroRate.x, gyroRate.y, gyroRate.z);
  Quaternion attitudeGyro = attitude * gyroQuat;

  // Accel-based tilt estimate (when not accelerating)
  float accelMag = accel.magnitude();
  float rollAccel = atan2(accel.y, accel.z);
  float pitchAccel = atan2(-accel.x, sqrt(accel.y * accel.y + accel.z * accel.z));

  // Complementary filter
  if (abs(accelMag - 9.81) < 2.0) { // Only trust accel when near 1g
    eulerAngles.x = 0.98 * attitudeGyro.toEuler().x + 0.02 * rollAccel;
    eulerAngles.y = 0.98 * attitudeGyro.toEuler().y + 0.02 * pitchAccel;
  } else {
    eulerAngles.x = attitudeGyro.toEuler().x;
    eulerAngles.y = attitudeGyro.toEuler().y;
  }

  // Yaw from gyro only (or magnetometer if available)
  eulerAngles.z = attitudeGyro.toEuler().z;

  // Update quaternion from filtered Euler angles
  attitude = Quaternion::fromEuler(eulerAngles.x, eulerAngles.y, eulerAngles.z);
}

// ============================================================================
// RECEIVE COMMANDS
// ============================================================================

void receiveCommands() {
  // Check for commands from WiFi/ESP-NOW
  if (comm.available()) {
    CommandPacket cmd = comm.readCommand();

    switch (cmd.type) {
      case CMD_ARM:
        if (!motorsArmed && currentMode == MODE_DISARMED) {
          motorsArmed = true;
          currentMode = MODE_STABILIZE;
          Serial.println("MOTORS ARMED");
        }
        break;

      case CMD_DISARM:
        motorsArmed = false;
        currentMode = MODE_DISARMED;
        Serial.println("MOTORS DISARMED");
        break;

      case CMD_SET_MODE:
        currentMode = (FlightMode)cmd.data.mode;
        Serial.printf("Mode changed to: %d\n", currentMode);
        break;

      case CMD_CONTROL_INPUT:
        controlInputs.roll = cmd.data.roll;
        controlInputs.pitch = cmd.data.pitch;
        controlInputs.yaw = cmd.data.yaw;
        controlInputs.throttle = cmd.data.throttle;
        break;

      case CMD_POSITION_TARGET:
        // For autonomous mode
        position.x = cmd.data.targetX;
        position.y = cmd.data.targetY;
        position.z = cmd.data.targetZ;
        break;
    }
  }
}

// ============================================================================
// FLIGHT CONTROLLER
// ============================================================================

void runFlightController() {
  if (!motorsArmed) {
    // Reset PIDs when disarmed
    pidRoll.reset();
    pidPitch.reset();
    pidYaw.reset();
    pidAltitude.reset();
    return;
  }

  float rollOutput = 0, pitchOutput = 0, yawOutput = 0, throttleOutput = 0;

  switch (currentMode) {
    case MODE_STABILIZE:
      // Stabilize mode: User controls desired angle rates
      rollOutput = stabilizeControl(controlInputs.roll, eulerAngles.x, gyro.x);
      pitchOutput = stabilizeControl(controlInputs.pitch, eulerAngles.y, gyro.y);
      yawOutput = yawControl(controlInputs.yaw, gyro.z);
      throttleOutput = controlInputs.throttle;
      break;

    case MODE_ALT_HOLD:
      // Altitude hold: Maintain height
      rollOutput = stabilizeControl(controlInputs.roll, eulerAngles.x, gyro.x);
      pitchOutput = stabilizeControl(controlInputs.pitch, eulerAngles.y, gyro.y);
      yawOutput = yawControl(controlInputs.yaw, gyro.z);
      throttleOutput = altitudeControl(altitude);
      break;

    case MODE_AUTONOMOUS:
      // Autonomous: Position control from swarm logic
      // This will be used for hide-and-seek!
      autonomousControl(&rollOutput, &pitchOutput, &yawOutput, &throttleOutput);
      break;

    default:
      // Safety: disarm if unknown mode
      motorsArmed = false;
      currentMode = MODE_DISARMED;
      break;
  }

  // Store outputs for motor mixing
  controlInputs.roll = rollOutput;
  controlInputs.pitch = pitchOutput;
  controlInputs.yaw = yawOutput;
  controlInputs.throttle = throttleOutput;
}

// ============================================================================
// CONTROL ALGORITHMS
// ============================================================================

float stabilizeControl(float desiredAngle, float currentAngle, float currentRate) {
  // Convert desired input (-1 to 1) to angle (-MAX_ANGLE to +MAX_ANGLE)
  float targetAngle = desiredAngle * MAX_TILT_ANGLE;

  // Angle error
  float angleError = targetAngle - currentAngle;

  // PID on angle error gives desired rate
  float desiredRate = angleError * ANGLE_TO_RATE_GAIN;

  // Limit desired rate
  desiredRate = constrain(desiredRate, -MAX_RATE, MAX_RATE);

  // Rate error
  float rateError = desiredRate - currentRate;

  // PID on rate (this is the actual control output)
  return rateError * RATE_P_GAIN;
}

float yawControl(float desiredYawRate, float currentYawRate) {
  // Yaw is rate-only (no angle hold)
  float targetRate = desiredYawRate * MAX_YAW_RATE;
  float rateError = targetRate - currentYawRate;
  return rateError * YAW_P_GAIN;
}

float altitudeControl(float currentAlt) {
  // Maintain altitude using PID
  static float targetAlt = 0;

  if (controlInputs.throttle > 0.55) {
    targetAlt += (controlInputs.throttle - 0.5) * ALT_CLIMB_RATE * dt;
  } else if (controlInputs.throttle < 0.45) {
    targetAlt += (controlInputs.throttle - 0.5) * ALT_CLIMB_RATE * dt;
  }

  targetAlt = constrain(targetAlt, 0, MAX_ALTITUDE);

  float altError = targetAlt - currentAlt;
  float throttle = pidAltitude.compute(altError, dt);

  return constrain(throttle, 0.0, 1.0);
}

void autonomousControl(float* roll, float* pitch, float* yaw, float* throttle) {
  // This integrates with our Python swarm logic!
  // For now, simple position hold

  // Get target from swarm controller (received via WiFi)
  // For now, just hover in place

  *roll = 0;
  *pitch = 0;
  *yaw = 0;
  *throttle = 0.5; // Hover throttle (will be tuned)
}

// ============================================================================
// MOTOR MIXING (X-Configuration Quadcopter)
// ============================================================================

void mixMotors() {
  if (!motorsArmed) {
    motorPWM[0] = motorPWM[1] = motorPWM[2] = motorPWM[3] = 0;
    return;
  }

  float throttle = controlInputs.throttle;
  float roll = controlInputs.roll;
  float pitch = controlInputs.pitch;
  float yaw = controlInputs.yaw;

  // X-configuration motor mixing:
  // M1 (front-left):  +throttle -roll +pitch -yaw
  // M2 (front-right): +throttle +roll +pitch +yaw
  // M3 (back-right):  +throttle +roll -pitch -yaw
  // M4 (back-left):   +throttle -roll -pitch +yaw

  motorPWM[0] = throttle - roll + pitch - yaw;
  motorPWM[1] = throttle + roll + pitch + yaw;
  motorPWM[2] = throttle + roll - pitch - yaw;
  motorPWM[3] = throttle - roll - pitch + yaw;

  // Constrain to 0-1 range
  for (int i = 0; i < 4; i++) {
    motorPWM[i] = constrain(motorPWM[i], MOTOR_MIN_THROTTLE, MOTOR_MAX_THROTTLE);
  }
}

// ============================================================================
// TELEMETRY
// ============================================================================

void sendTelemetry() {
  static unsigned long lastTelemetryTime = 0;
  unsigned long currentTime = millis();

  if (currentTime - lastTelemetryTime > TELEMETRY_INTERVAL_MS) {
    TelemetryPacket telemetry;
    telemetry.timestamp = currentTime;
    telemetry.roll = eulerAngles.x;
    telemetry.pitch = eulerAngles.y;
    telemetry.yaw = eulerAngles.z;
    telemetry.altitude = altitude;
    telemetry.battery = analogRead(BATTERY_PIN) * (3.3 / 4095.0) * VOLTAGE_DIVIDER_RATIO;
    telemetry.armed = motorsArmed;
    telemetry.mode = currentMode;

    comm.sendTelemetry(telemetry);

    lastTelemetryTime = currentTime;
  }
}

// ============================================================================
// STATUS LED
// ============================================================================

void updateStatusLED() {
  static unsigned long lastBlink = 0;
  unsigned long currentTime = millis();

  if (currentMode == MODE_DISARMED) {
    // Slow blink when disarmed
    if (currentTime - lastBlink > 1000) {
      digitalWrite(LED_PIN, !digitalRead(LED_PIN));
      lastBlink = currentTime;
    }
  } else if (motorsArmed) {
    // Solid on when armed
    digitalWrite(LED_PIN, HIGH);
  }
}
