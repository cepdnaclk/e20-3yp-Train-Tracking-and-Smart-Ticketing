#include "secrets.h"
#include <WiFiClientSecure.h>
#include <MQTTClient.h>
#include <ArduinoJson.h>
#include "WiFi.h"
#include <SPI.h>
#include <MFRC522.h>

// RFID Module Pins
#define SS_PIN 5   // ESP32's GPIO5 (D5)
#define RST_PIN 22 // ESP32's GPIO22 (D22)

// AWS IoT Topics
#define AWS_IOT_PUBLISH_TOPIC   "esp32/rfid_pub"
#define AWS_IOT_SUBSCRIBE_TOPIC "esp32/rfid_sub"

// Initialize objects
MFRC522 rfid(SS_PIN, RST_PIN);
WiFiClientSecure net;
MQTTClient client(256);

// Function to connect to WiFi & AWS IoT
void connectAWS() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi Connected!");

  // Configure TLS certificates
  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);

  // Connect to AWS IoT
  client.begin(AWS_IOT_ENDPOINT, 8883, net);
  client.onMessage(messageHandler);

  Serial.print("Connecting to AWS IoT\n");
  while (!client.connect(THINGNAME)) {
    Serial.print(".");
    delay(100);
  }

  if (!client.connected()) {
    Serial.println("AWS IoT Connection Failed!");
    return;
  }

  client.subscribe(AWS_IOT_SUBSCRIBE_TOPIC);
  Serial.println("AWS IoT Connected!");
}

// Function to publish RFID data to AWS
void publishRFID(String uid) {
  StaticJsonDocument<200> doc;
  doc["RFID_UID"] = uid;
  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer);

  client.publish(AWS_IOT_PUBLISH_TOPIC, jsonBuffer);
  Serial.print("Published UID to AWS: ");
  Serial.println(uid);
}

// Function to handle incoming messages from AWS
void messageHandler(String &topic, String &payload) {
  Serial.println("Incoming message from AWS: " + topic + " - " + payload);
}

// Function to read RFID card
void checkRFID() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  Serial.print("Card Detected! UID: ");
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  Serial.println(uid);

  publishRFID(uid);

  // Halt the card
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

void setup() {
  Serial.begin(115200);
  SPI.begin();        // Init SPI bus
  rfid.PCD_Init();    // Init RFID scanner
  connectAWS();       // Connect to AWS IoT
}

void loop() {
  checkRFID();  // Continuously check for RFID cards
  client.loop();
}
