/**
 * PID Controller
 */

#ifndef PID_H
#define PID_H

class PIDController {
public:
  PIDController(float kp, float ki, float kd);

  float compute(float error, float dt);
  void reset();
  void setGains(float kp, float ki, float kd);

private:
  float kp, ki, kd;
  float integral;
  float lastError;
  float integralLimit;
};

#endif // PID_H
