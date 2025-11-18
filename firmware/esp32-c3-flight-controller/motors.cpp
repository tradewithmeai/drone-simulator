/**
 * Motor/ESC Control Implementation
 */

#include "motors.h"
#include "config.h"
#include <ESP32Servo.h>

static Servo escs[4];

Motors::Motors() {
  pins[0] = MOTOR_1_PIN;
  pins[1] = MOTOR_2_PIN;
  pins[2] = MOTOR_3_PIN;
  pins[3] = MOTOR_4_PIN;
}

void Motors::begin() {
  // Initialize ESC control using Servo library
  for (int i = 0; i < 4; i++) {
    escs[i].attach(pins[i], ESC_MIN_PULSE, ESC_MAX_PULSE);
    escs[i].writeMicroseconds(ESC_MIN_PULSE); // Start at minimum
  }

  delay(1000); // Let ESCs initialize
}

void Motors::calibrate() {
  Serial.println("ESC Calibration Mode");
  Serial.println("1. Disconnect battery");
  Serial.println("2. Press Enter when ready");

  while (!Serial.available());
  Serial.read();

  // Send maximum throttle
  Serial.println("Sending MAX throttle...");
  for (int i = 0; i < 4; i++) {
    escs[i].writeMicroseconds(ESC_MAX_PULSE);
  }

  Serial.println("3. Connect battery now");
  Serial.println("4. Wait for beeps, then press Enter");

  while (!Serial.available());
  Serial.read();

  // Send minimum throttle
  Serial.println("Sending MIN throttle...");
  for (int i = 0; i < 4; i++) {
    escs[i].writeMicroseconds(ESC_MIN_PULSE);
  }

  Serial.println("ESC calibration complete!");
  delay(2000);
}

void Motors::set(int motorIndex, float throttle) {
  if (motorIndex < 0 || motorIndex >= 4) return;

  throttle = constrain(throttle, 0.0, 1.0);
  int pulseWidth = throttleToMicroseconds(throttle);
  escs[motorIndex].writeMicroseconds(pulseWidth);
}

void Motors::setAll(float throttle[4]) {
  for (int i = 0; i < 4; i++) {
    set(i, throttle[i]);
  }
}

void Motors::stop() {
  for (int i = 0; i < 4; i++) {
    escs[i].writeMicroseconds(ESC_MIN_PULSE);
  }
}

int Motors::throttleToMicroseconds(float throttle) {
  // Convert 0.0-1.0 to ESC_MIN_PULSE - ESC_MAX_PULSE
  return map(throttle * 1000, 0, 1000, ESC_MIN_PULSE, ESC_MAX_PULSE);
}
