#include "secrets.h"
#include <WiFiClientSecure.h>
#include <MQTTClient.h>
#include <ArduinoJson.h>
#include "WiFi.h"
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// LCD Configuration
LiquidCrystal_I2C lcd(0x27, 20, 4);  // Adjust address if needed

// RFID Module Pins
#define SS_PIN 5
#define RST_PIN 4
#define READ_BLOCK 0
#define NO_OF_BLOCKS 3

#define AWS_IOT_PUBLISH_TOPIC   "esp32/rfid_pub"
#define AWS_IOT_SUBSCRIBE_TOPIC "esp32/rfid_sub"

MFRC522 rfid(SS_PIN, RST_PIN);
WiFiClientSecure net;
MQTTClient client(256);

struct RFIDData {
  String uid;
  String blockData[NO_OF_BLOCKS];
};
RFIDData rfidData;

void lcdLog(const String &message, int line = 0) {
  lcd.setCursor(0, line);
  lcd.print("                    ");  // Clear line
  lcd.setCursor(0, line);
  lcd.print(message);
}

// read block of data
bool readBlock(byte block, byte *buffer) {
  MFRC522::MIFARE_Key key;
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

  lcdLog("Reading RFID block", 0);

  if (rfid.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(rfid.uid)) != MFRC522::STATUS_OK) {
    lcdLog("Auth Failed!", 1);
    return false;
  }

  byte size = 18;
  if (rfid.MIFARE_Read(block, buffer, &size) != MFRC522::STATUS_OK) {
    lcdLog("Read Failed!", 1);
    rfid.PCD_StopCrypto1();
    return false;
  }

  lcdLog("Read Block OK", 1);
  rfid.PCD_StopCrypto1();
  return true;
}

void parseBlockData(byte block, uint32_t &price, uint16_t &stationId, bool &startStop) {
  byte buffer[18];
  if (readBlock(block, buffer)) {
    price = ((uint32_t)buffer[0] << 24) | ((uint32_t)buffer[1] << 16) | ((uint32_t)buffer[2] << 8) | buffer[3];
    stationId = ((uint16_t)buffer[4] << 8) | buffer[5];
    startStop = (buffer[6] & 0x01);
  }
}

void writeBlockData(byte block, String data) {
  MFRC522::MIFARE_Key key;
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

  byte buffer[16] = {0};
  data.getBytes(buffer, 16);

  if (rfid.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(rfid.uid)) == MFRC522::STATUS_OK) {
    if (rfid.MIFARE_Write(block, buffer, 16) == MFRC522::STATUS_OK) {
      lcdLog("Write Success", 1);
    } else {
      lcdLog("Write Failed", 1);
    }
  } else {
    lcdLog("Auth Failed!", 1);
  }
}

void handleAWSWriteCommand(String &payload) {
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, payload);
  if (error) {
    lcdLog("JSON Parse Err", 1);
    return;
  }

  int block = doc["block"].as<int>();
  String data = doc["data"].as<String>();
  lcdLog("Writing Block: " + String(block), 1);
  writeBlockData(block, data);
}

bool checkRFID() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return false;
  }

  String cardUID = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    cardUID += String(rfid.uid.uidByte[i], HEX);
  }

  uint32_t price = 0;
  uint16_t stationId = 0;
  bool startStop = false;
  parseBlockData(READ_BLOCK, price, stationId, startStop);

  lcd.clear();
  lcdLog("UID: " + cardUID, 0);
  lcdLog("Price: " + String(price), 1);
  lcdLog("Station ID: " + String(stationId), 2);
  lcdLog(startStop ? "Status: Start" : "Status: Stop", 3);

  StaticJsonDocument<200> jsonDoc;
  jsonDoc["uid"] = cardUID;
  jsonDoc["price"] = price;
  jsonDoc["station_id"] = stationId;
  jsonDoc["start_stop"] = startStop;

  char jsonBuffer[256];
  serializeJson(jsonDoc, jsonBuffer);

  if (client.connected()) {
    client.publish(AWS_IOT_PUBLISH_TOPIC, jsonBuffer);
    lcdLog("Published to AWS", 1);
  } else {
    lcdLog("MQTT Not Conn", 1);
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  return true;
}

void waitForCardRead() {
  lcd.clear();
  lcdLog("Place RFID Card...", 0);
  while (!checkRFID()) {
    delay(500);
    client.loop();
  }
  delay(2000);
}

void messageHandler(String &topic, String &payload) {
  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, payload);
  if (error) {
    lcdLog("AWS JSON Err", 0);
    return;
  }

  String uid = doc["uid"].as<String>();
  uint32_t price = doc["price"];
  uint16_t stationId = doc["station_id"];
  bool startStop = doc["start_stop"];

  byte buffer[16] = {0};
  buffer[0] = (price >> 24) & 0xFF;
  buffer[1] = (price >> 16) & 0xFF;
  buffer[2] = (price >> 8) & 0xFF;
  buffer[3] = price & 0xFF;
  buffer[4] = (stationId >> 8) & 0xFF;
  buffer[5] = stationId & 0xFF;
  buffer[6] = startStop ? 0x01 : 0x00;

  MFRC522::MIFARE_Key key;
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    if (rfid.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, 1, &key, &(rfid.uid)) == MFRC522::STATUS_OK) {
      if (rfid.MIFARE_Write(1, buffer, 16) == MFRC522::STATUS_OK) {
        lcdLog("Write Block 1 OK", 1);
      } else {
        lcdLog("Write Block 1 Err", 1);
      }
    } else {
      lcdLog("Auth Failed", 1);
    }
  } else {
    lcdLog("No Card Present", 1);
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

void setup() {
  Serial.begin(115200);
  lcd.init();
  lcd.backlight();
  lcdLog("Init RFID + LCD", 0);

  SPI.begin();
  rfid.PCD_Init();

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lcdLog("Connecting WiFi", 1);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    lcdLog("WiFi...", 1);
  }

  lcdLog("WiFi Connected", 1);
  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);

  client.begin(AWS_IOT_ENDPOINT, 8883, net);
  client.onMessage(messageHandler);

  lcdLog("Connecting AWS", 2);
  while (!client.connect(THINGNAME)) {
    delay(1000);
    lcdLog("Retry AWS...", 2);
  }

  if (client.subscribe(AWS_IOT_SUBSCRIBE_TOPIC)) {
    lcdLog("Subscribed AWS", 3);
  } else {
    lcdLog("Sub Failed", 3);
  }

  delay(1000);
  lcd.clear();
}

void loop() {
  waitForCardRead();
  client.loop();
}
