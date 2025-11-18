/**
 * Communication Module - WiFi and ESP-NOW
 */

#ifndef COMMUNICATION_H
#define COMMUNICATION_H

#include <Arduino.h>
#include <WiFi.h>

// Command types
enum CommandType {
  CMD_ARM = 1,
  CMD_DISARM = 2,
  CMD_SET_MODE = 3,
  CMD_CONTROL_INPUT = 4,
  CMD_POSITION_TARGET = 5,
  CMD_VELOCITY_COMMAND = 6
};

// Command packet structure
struct CommandPacket {
  uint8_t type;
  union {
    struct {
      float roll, pitch, yaw, throttle;
    };
    struct {
      float targetX, targetY, targetZ;
    };
    struct {
      float vx, vy, vz, vyaw;
    };
    struct {
      uint8_t mode;
    };
  } data;
};

// Telemetry packet structure
struct TelemetryPacket {
  uint32_t timestamp;
  float roll, pitch, yaw;
  float altitude;
  float battery;
  bool armed;
  uint8_t mode;
};

class Communication {
public:
  Communication();

  void begin();
  bool available();
  CommandPacket readCommand();
  void sendTelemetry(const TelemetryPacket& telemetry);

private:
  WiFiUDP udp;
  uint8_t buffer[256];
};

#endif // COMMUNICATION_H
