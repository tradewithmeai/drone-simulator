/**
 * IMU Implementation - MPU6050
 */

#include "imu.h"
#include "config.h"

// MPU6050 Registers
#define MPU6050_REG_PWR_MGMT_1    0x6B
#define MPU6050_REG_GYRO_CONFIG   0x1B
#define MPU6050_REG_ACCEL_CONFIG  0x1C
#define MPU6050_REG_ACCEL_XOUT_H  0x3B
#define MPU6050_REG_TEMP_OUT_H    0x41
#define MPU6050_REG_GYRO_XOUT_H   0x43

IMU::IMU() : address(IMU_ADDRESS) {
  gyro = Vector3(0, 0, 0);
  accel = Vector3(0, 0, 0);
  mag = Vector3(0, 0, 0);
  gyroBias = Vector3(0, 0, 0);
  accelBias = Vector3(0, 0, 0);
  temperature = 0;
}

bool IMU::begin() {
  // Wake up MPU6050
  writeRegister(MPU6050_REG_PWR_MGMT_1, 0x00);
  delay(100);

  // Set gyro range to ±250 deg/s
  writeRegister(MPU6050_REG_GYRO_CONFIG, 0x00);

  // Set accel range to ±2g
  writeRegister(MPU6050_REG_ACCEL_CONFIG, 0x00);

  delay(100);

  // Verify connection
  uint8_t whoAmI = readRegister(0x75);
  if (whoAmI != 0x68 && whoAmI != 0x98) {
    return false;
  }

  return true;
}

void IMU::calibrate() {
  Serial.println("Calibrating gyro and accelerometer...");

  const int samples = 1000;
  Vector3 gyroSum(0, 0, 0);
  Vector3 accelSum(0, 0, 0);

  for (int i = 0; i < samples; i++) {
    update();
    gyroSum = gyroSum + gyro;
    accelSum = accelSum + accel;
    delay(3);

    if (i % 100 == 0) {
      Serial.print(".");
    }
  }

  gyroBias.x = gyroSum.x / samples;
  gyroBias.y = gyroSum.y / samples;
  gyroBias.z = gyroSum.z / samples;

  accelBias.x = accelSum.x / samples;
  accelBias.y = accelSum.y / samples;
  accelBias.z = (accelSum.z / samples) - 9.81; // Gravity

  Serial.println(" Done!");
  Serial.printf("Gyro bias: %.4f, %.4f, %.4f rad/s\n",
                gyroBias.x, gyroBias.y, gyroBias.z);
  Serial.printf("Accel bias: %.4f, %.4f, %.4f m/s²\n",
                accelBias.x, accelBias.y, accelBias.z);
}

void IMU::update() {
  uint8_t buffer[14];

  // Read all sensor data in one burst
  readRegisters(MPU6050_REG_ACCEL_XOUT_H, buffer, 14);

  // Accelerometer (raw to m/s²)
  int16_t ax = (buffer[0] << 8) | buffer[1];
  int16_t ay = (buffer[2] << 8) | buffer[3];
  int16_t az = (buffer[4] << 8) | buffer[5];

  accel.x = (ax / 16384.0) * 9.81 - accelBias.x;
  accel.y = (ay / 16384.0) * 9.81 - accelBias.y;
  accel.z = (az / 16384.0) * 9.81 - accelBias.z;

  // Temperature
  int16_t temp = (buffer[6] << 8) | buffer[7];
  temperature = (temp / 340.0) + 36.53;

  // Gyroscope (raw to rad/s)
  int16_t gx = (buffer[8] << 8) | buffer[9];
  int16_t gy = (buffer[10] << 8) | buffer[11];
  int16_t gz = (buffer[12] << 8) | buffer[13];

  gyro.x = (gx / 131.0) * (PI / 180.0) - gyroBias.x;
  gyro.y = (gy / 131.0) * (PI / 180.0) - gyroBias.y;
  gyro.z = (gz / 131.0) * (PI / 180.0) - gyroBias.z;
}

void IMU::writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

uint8_t IMU::readRegister(uint8_t reg) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(address, (uint8_t)1);
  return Wire.read();
}

void IMU::readRegisters(uint8_t reg, uint8_t* buffer, size_t length) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(address, (uint8_t)length);

  for (size_t i = 0; i < length; i++) {
    buffer[i] = Wire.read();
  }
}
