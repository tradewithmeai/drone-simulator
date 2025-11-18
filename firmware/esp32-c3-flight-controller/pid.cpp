/**
 * PID Controller Implementation
 */

#include "pid.h"
#include <Arduino.h>

PIDController::PIDController(float kp, float ki, float kd)
  : kp(kp), ki(ki), kd(kd), integral(0), lastError(0), integralLimit(10.0) {}

float PIDController::compute(float error, float dt) {
  // Proportional
  float P = kp * error;

  // Integral (with anti-windup)
  integral += error * dt;
  integral = constrain(integral, -integralLimit, integralLimit);
  float I = ki * integral;

  // Derivative
  float derivative = (error - lastError) / dt;
  float D = kd * derivative;

  lastError = error;

  return P + I + D;
}

void PIDController::reset() {
  integral = 0;
  lastError = 0;
}

void PIDController::setGains(float kp, float ki, float kd) {
  this->kp = kp;
  this->ki = ki;
  this->kd = kd;
}
