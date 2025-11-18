/**
 * IMU Interface - MPU6050/MPU9250
 */

#ifndef IMU_H
#define IMU_H

#include <Arduino.h>
#include <Wire.h>

// Simple 3D vector
struct Vector3 {
  float x, y, z;

  Vector3() : x(0), y(0), z(0) {}
  Vector3(float x, float y, float z) : x(x), y(y), z(z) {}

  float magnitude() const {
    return sqrt(x * x + y * y + z * z);
  }

  Vector3 operator*(float scalar) const {
    return Vector3(x * scalar, y * scalar, z * scalar);
  }

  Vector3 operator+(const Vector3& other) const {
    return Vector3(x + other.x, y + other.y, z + other.z);
  }

  Vector3 operator-(const Vector3& other) const {
    return Vector3(x - other.x, y - other.y, z - other.z);
  }
};

class IMU {
public:
  IMU();

  bool begin();
  void calibrate();
  void update();

  Vector3 getGyro() const { return gyro; }
  Vector3 getAccel() const { return accel; }
  Vector3 getMag() const { return mag; }

  float getTemperature() const { return temperature; }

private:
  void writeRegister(uint8_t reg, uint8_t value);
  uint8_t readRegister(uint8_t reg);
  void readRegisters(uint8_t reg, uint8_t* buffer, size_t length);

  Vector3 gyro;      // rad/s
  Vector3 accel;     // m/s²
  Vector3 mag;       // μT
  float temperature; // °C

  Vector3 gyroBias;
  Vector3 accelBias;

  uint8_t address;
};

#endif // IMU_H
