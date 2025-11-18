/**
 * Filters and Quaternion Math Implementation
 */

#include "filters.h"

// ============================================================================
// QUATERNION
// ============================================================================

Quaternion Quaternion::fromEuler(float roll, float pitch, float yaw) {
  float cy = cos(yaw * 0.5);
  float sy = sin(yaw * 0.5);
  float cp = cos(pitch * 0.5);
  float sp = sin(pitch * 0.5);
  float cr = cos(roll * 0.5);
  float sr = sin(roll * 0.5);

  Quaternion q;
  q.w = cr * cp * cy + sr * sp * sy;
  q.x = sr * cp * cy - cr * sp * sy;
  q.y = cr * sp * cy + sr * cp * sy;
  q.z = cr * cp * sy - sr * sp * cy;

  return q;
}

Vector3 Quaternion::toEuler() const {
  Vector3 euler;

  // Roll (x-axis rotation)
  float sinr_cosp = 2 * (w * x + y * z);
  float cosr_cosp = 1 - 2 * (x * x + y * y);
  euler.x = atan2(sinr_cosp, cosr_cosp);

  // Pitch (y-axis rotation)
  float sinp = 2 * (w * y - z * x);
  if (fabs(sinp) >= 1)
    euler.y = copysign(PI / 2, sinp); // Use 90 degrees if out of range
  else
    euler.y = asin(sinp);

  // Yaw (z-axis rotation)
  float siny_cosp = 2 * (w * z + x * y);
  float cosy_cosp = 1 - 2 * (y * y + z * z);
  euler.z = atan2(siny_cosp, cosy_cosp);

  return euler;
}

Quaternion Quaternion::operator*(const Quaternion& q) const {
  Quaternion result;
  result.w = w * q.w - x * q.x - y * q.y - z * q.z;
  result.x = w * q.x + x * q.w + y * q.z - z * q.y;
  result.y = w * q.y - x * q.z + y * q.w + z * q.x;
  result.z = w * q.z + x * q.y - y * q.x + z * q.w;
  return result;
}

void Quaternion::normalize() {
  float norm = sqrt(w * w + x * x + y * y + z * z);
  if (norm > 0.0001) {
    w /= norm;
    x /= norm;
    y /= norm;
    z /= norm;
  }
}

Quaternion Quaternion::conjugate() const {
  return Quaternion(w, -x, -y, -z);
}

// ============================================================================
// COMPLEMENTARY FILTER
// ============================================================================

ComplementaryFilter::ComplementaryFilter(float alpha) : alpha(alpha) {
  attitude = Quaternion(1, 0, 0, 0);
}

void ComplementaryFilter::update(const Vector3& gyro, const Vector3& accel, float dt) {
  // Integrate gyroscope for attitude change
  Quaternion gyroQuat = Quaternion::fromEuler(gyro.x * dt, gyro.y * dt, gyro.z * dt);
  Quaternion attitudeGyro = attitude * gyroQuat;
  attitudeGyro.normalize();

  // Get accelerometer-based tilt estimate
  float roll = atan2(accel.y, accel.z);
  float pitch = atan2(-accel.x, sqrt(accel.y * accel.y + accel.z * accel.z));

  Quaternion attitudeAccel = Quaternion::fromEuler(roll, pitch, 0);

  // Complementary filter: blend gyro and accel
  // SLERP would be better, but this is simpler
  attitude.w = alpha * attitudeGyro.w + (1 - alpha) * attitudeAccel.w;
  attitude.x = alpha * attitudeGyro.x + (1 - alpha) * attitudeAccel.x;
  attitude.y = alpha * attitudeGyro.y + (1 - alpha) * attitudeAccel.y;
  attitude.z = alpha * attitudeGyro.z + (1 - alpha) * 0; // Yaw from gyro only

  attitude.normalize();
}
