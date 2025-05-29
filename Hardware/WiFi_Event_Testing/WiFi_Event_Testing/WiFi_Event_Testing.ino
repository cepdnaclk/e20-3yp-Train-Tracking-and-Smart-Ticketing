#include <WiFi.h>

// Replace with your network credentials
const char* ssid = "SIGNAL_NA";
const char* password = "new_password";

// WiFi disconnected event handler
void onWiFiDisconnected(WiFiEvent_t event, WiFiEventInfo_t info) {
  Serial.println("WiFi Disconnected");
  isWiFiConnected = false;
}

// Got IP address event handler
void onWiFiGotIP(WiFiEvent_t event, WiFiEventInfo_t info) {
  Serial.print("WiFi Connected. IP Address: ");
  Serial.println(WiFi.localIP());
  isWiFiConnected = true;
}

void setup() {
  Serial.begin(115200);

  // Register WiFi and IP event handlers
  WiFi.onEvent(onWiFiDisconnected, ARDUINO_EVENT_WIFI_STA_DISCONNECTED);
  WiFi.onEvent(onWiFiGotIP, ARDUINO_EVENT_WIFI_STA_GOT_IP);

  // Set Wi-Fi to station mode and initiate connection
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.println("Attempting to connect to WiFi...");
}

void loop() {
  delay(1000);
}
