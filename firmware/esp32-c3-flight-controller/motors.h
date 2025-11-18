/**
 * Motor/ESC Control
 */

#ifndef MOTORS_H
#define MOTORS_H

#include <Arduino.h>

class Motors {
public:
  Motors();

  void begin();
  void calibrate(); // ESC calibration (run once)

  void set(int motorIndex, float throttle); // Set single motor (0.0 to 1.0)
  void setAll(float throttle[4]);            // Set all motors
  void stop();                               // Stop all motors

private:
  int pins[4];
  int channels[4];

  int throttleToMicroseconds(float throttle);
};

#endif // MOTORS_H
