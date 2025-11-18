/**
 * Filters and Quaternion Math
 */

#ifndef FILTERS_H
#define FILTERS_H

#include <Arduino.h>
#include "imu.h"

// Quaternion for attitude representation
class Quaternion {
public:
  float w, x, y, z;

  Quaternion() : w(1), x(0), y(0), z(0) {}
  Quaternion(float w, float x, float y, float z) : w(w), x(x), y(y), z(z) {}

  // Create quaternion from Euler angles (roll, pitch, yaw)
  static Quaternion fromEuler(float roll, float pitch, float yaw);

  // Convert to Euler angles
  Vector3 toEuler() const;

  // Quaternion multiplication
  Quaternion operator*(const Quaternion& q) const;

  // Normalize
  void normalize();

  // Conjugate
  Quaternion conjugate() const;
};

// Complementary filter for attitude estimation
class ComplementaryFilter {
public:
  ComplementaryFilter(float alpha = 0.98);

  void update(const Vector3& gyro, const Vector3& accel, float dt);
  Quaternion getAttitude() const { return attitude; }
  Vector3 getEuler() const { return attitude.toEuler(); }

private:
  float alpha; // Filter coefficient (0-1, higher = more gyro)
  Quaternion attitude;
};

#endif // FILTERS_H
