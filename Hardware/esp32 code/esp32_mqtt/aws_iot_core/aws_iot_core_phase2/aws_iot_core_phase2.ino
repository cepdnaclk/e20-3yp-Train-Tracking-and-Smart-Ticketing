#include "secrets.h"
#include <WiFiClientSecure.h>
#include <MQTTClient.h>
#include <ArduinoJson.h>
#include "WiFi.h"
#include <SPI.h>
#include <MFRC522.h>

// RFID Module Pins
#define SS_PIN 5    // ESP32 GPIO5 (D5)
#define RST_PIN 22  // ESP32 GPIO22 (D22)
#define READ_BLOCK 0 // Block that we are reading from

// AWS IoT Topics
#define AWS_IOT_PUBLISH_TOPIC   "esp32/rfid_pub"
#define AWS_IOT_SUBSCRIBE_TOPIC "esp32/rfid_sub"
#define NO_OF_BLOCKS 3

// Initialize objects
MFRC522 rfid(SS_PIN, RST_PIN);
WiFiClientSecure net;
MQTTClient client(256);

// Store RFID data before uploading
struct RFIDData {
  String uid;
  String blockData[NO_OF_BLOCKS];
};
RFIDData rfidData; // Global structure to hold RFID data

// read block of data from the card
bool readBlock(byte block, byte *buffer) {
    MFRC522::MIFARE_Key key;
    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    Serial.println("🔄 Attempting to read RFID block...");

    if (rfid.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(rfid.uid)) != MFRC522::STATUS_OK) {
        Serial.println("❌ Authentication Failed!");
        return false;
    }

    byte size = 18;  // 16 bytes of data + 2 CRC bytes
    if (rfid.MIFARE_Read(block, buffer, &size) != MFRC522::STATUS_OK) {
        Serial.println("❌ Read Block Failed!");
        rfid.PCD_StopCrypto1();
        return false;
    }

    Serial.print("✅ Read Block ");
    Serial.print(block);
    Serial.print(": ");
    for (byte i = 0; i < 16; i++) Serial.printf("%02X ", buffer[i]);
    Serial.println();

    rfid.PCD_StopCrypto1();
    return true;
}

// Function to parse block data
void parseBlockData(byte block, uint32_t &price, uint16_t &stationId, bool &startStop) {
    byte buffer[18];
    if (readBlock(block, buffer)) {
        price = ((uint32_t)buffer[0] << 24) | ((uint32_t)buffer[1] << 16) | ((uint32_t)buffer[2] << 8) | buffer[3];
        stationId = ((uint16_t)buffer[4] << 8) | buffer[5];
        startStop = (buffer[6] & 0x01);
    }
}

// Function to write data to a specific block
void writeBlockData(byte block, String data) {
    MFRC522::MIFARE_Key key;
    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    byte buffer[16] = {0};
    data.getBytes(buffer, 16);

    if (rfid.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(rfid.uid)) == MFRC522::STATUS_OK) {
        if (rfid.MIFARE_Write(block, buffer, 16) == MFRC522::STATUS_OK) {
            Serial.println("✅ Write Successful!");
        } else {
            Serial.println("❌ Write Failed!");
        }
    } else {
        Serial.println("❌ Authentication Failed!");
    }
}

// Function to handle AWS IoT messages
void handleAWSWriteCommand(String &payload) {
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, payload);
    
    if (error) {
        Serial.println("❌ JSON Parsing Failed!");
        return;
    }

    int block = doc["block"].as<int>();
    String data = doc["data"].as<String>();

    Serial.print("Writing to Block ");
    Serial.println(block);

    writeBlockData(block, data);
}

// Function to check for an RFID card and read its data
bool checkRFID() {
    if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
        return false;
    }

    Serial.println("\n🔹 Card Detected!");
    Serial.print("UID: ");
    String cardUID = "";

    for (byte i = 0; i < rfid.uid.size; i++) {
        cardUID += String(rfid.uid.uidByte[i], HEX);
    }
    Serial.println(cardUID);

    // Read Block and parse data
    uint32_t price = 0;
    uint16_t stationId = 0;
    bool startStop = false;
    parseBlockData(READ_BLOCK, price, stationId, startStop);

    Serial.print("Price: ");
    Serial.println(price);
    Serial.print("Station ID: ");
    Serial.println(stationId);
    Serial.print("Start/Stop: ");
    Serial.println(startStop ? "Start" : "Stop");

    // Create JSON payload
    StaticJsonDocument<200> jsonDoc;
    jsonDoc["uid"] = cardUID;
    jsonDoc["price"] = price;
    jsonDoc["station_id"] = stationId;
    jsonDoc["start_stop"] = startStop;
    
    char jsonBuffer[256];
    serializeJson(jsonDoc, jsonBuffer);

    Serial.print("JSON Payload: ");
    Serial.println(jsonBuffer);

    // Publish to AWS IoT Core
    if (client.connected()) {
        client.publish(AWS_IOT_PUBLISH_TOPIC, jsonBuffer);
        Serial.println("✅ Data sent to AWS IoT Core!");
    } else {
        Serial.println("⚠️ MQTT not connected!");
    }

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    return true;  // Indicate successful read
}

// Function to wait until an RFID card is successfully read
void waitForCardRead() {
    Serial.println("\n📡 Waiting for an RFID card...or a message from the backendaaa");

    while (!checkRFID()) {  // Keep looping until a successful read
        delay(500);
        client.loop();
    }

    Serial.println("\n✅ Card read successfully! Waiting 2 seconds before next scan...");
    delay(2000);  // Wait 2 seconds before allowing another scan
}

// AWS IoT Message Handler
void messageHandler(String &topic, String &payload) {
    Serial.println("-------Message Handler -------");
    Serial.println("Incoming AWS message: " + payload);

    // Parse JSON payload
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, payload);
    
    if (error) {
        Serial.println("❌ JSON Parsing Failed!");
        return;
    }

    String uid = doc["uid"].as<String>();
    uint32_t price = doc["price"];
    uint16_t stationId = doc["station_id"];
    bool startStop = doc["start_stop"];

    Serial.println("✅ Parsed Data:");
    Serial.print("UID: "); Serial.println(uid);
    Serial.print("Price: "); Serial.println(price);
    Serial.print("Station ID: "); Serial.println(stationId);
    Serial.print("Start/Stop: "); Serial.println(startStop ? "Start" : "Stop");

    // Convert data into a 16-byte block
    byte buffer[16] = {0};
    buffer[0] = (price >> 24) & 0xFF;
    buffer[1] = (price >> 16) & 0xFF;
    buffer[2] = (price >> 8) & 0xFF;
    buffer[3] = price & 0xFF;
    
    buffer[4] = (stationId >> 8) & 0xFF;
    buffer[5] = stationId & 0xFF;

    buffer[6] = startStop ? 0x01 : 0x00;

    // Authenticate and Write to Block 1
    MFRC522::MIFARE_Key key;
    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
        if (rfid.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, 1, &key, &(rfid.uid)) == MFRC522::STATUS_OK) {
            if (rfid.MIFARE_Write(1, buffer, 16) == MFRC522::STATUS_OK) {
                Serial.println("✅ Successfully written to Block 1!");
            } else {
                Serial.println("❌ Write to Block 1 Failed!");
            }
        } else {
            Serial.println("❌ Authentication Failed!");
        }
    } else {
        Serial.println("⚠️ No RFID card detected!");
    }

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
}


// Setup WiFi and AWS MQTT connection
void setup() {
    Serial.begin(115200);
    SPI.begin();
    rfid.PCD_Init();

    // Connect to WiFi
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\n✅ Wi-Fi Connected!");

    // Configure AWS IoT certificates
    net.setCACert(AWS_CERT_CA);
    net.setCertificate(AWS_CERT_CRT);
    net.setPrivateKey(AWS_CERT_PRIVATE);

    // Connect to AWS MQTT
    client.begin(AWS_IOT_ENDPOINT, 8883, net);
    client.onMessage(messageHandler);

    Serial.println("Connecting to AWS IoT");
    while (!client.connect(THINGNAME)) {
        Serial.print(".");
        delay(1000);
    }

    if (client.subscribe(AWS_IOT_SUBSCRIBE_TOPIC)) {
        Serial.println("✅ Successfully subscribed to: " AWS_IOT_SUBSCRIBE_TOPIC);
    } else {
        Serial.println("❌ Subscription Failed!");
    }
}

// Main loop - Keeps waiting for card reads
void loop() {
    waitForCardRead();  // Ensure a card is read before proceeding
    client.loop();
}