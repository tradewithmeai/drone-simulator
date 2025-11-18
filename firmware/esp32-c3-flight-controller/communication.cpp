/**
 * Communication Implementation
 */

#include "communication.h"
#include "config.h"

Communication::Communication() {}

void Communication::begin() {
  // Connect to WiFi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Connecting to WiFi");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(" Connected!");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());

    // Start UDP for commands and telemetry
    udp.begin(COMMAND_PORT);
  } else {
    Serial.println(" Failed! Running without WiFi");
  }
}

bool Communication::available() {
  int packetSize = udp.parsePacket();
  return (packetSize > 0);
}

CommandPacket Communication::readCommand() {
  CommandPacket cmd;
  int len = udp.read(buffer, sizeof(buffer));

  if (len > 0) {
    memcpy(&cmd, buffer, sizeof(CommandPacket));
  }

  return cmd;
}

void Communication::sendTelemetry(const TelemetryPacket& telemetry) {
  if (WiFi.status() != WL_CONNECTED) return;

  // Send to ground station (broadcast or specific IP)
  udp.beginPacket(WiFi.gatewayIP(), TELEMETRY_PORT);
  udp.write((uint8_t*)&telemetry, sizeof(TelemetryPacket));
  udp.endPacket();
}
