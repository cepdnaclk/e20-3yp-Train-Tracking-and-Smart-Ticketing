#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <Arduino.h>
#include "esp32-hal-ledc.h"


// WiFi Credentials
#define WIFI_SSID "UPUL slt fiber"
#define WIFI_PASSWORD "panawennage2020"

// API Endpoint
#define SERVER_URL "http://192.168.42.64:8000/api/card/read/"

// RFID Module Pins
#define SS_PIN 5
#define RST_PIN 22

// for buzzer
#define BUZZER_PIN 4  // Change this to your buzzer's GPIO pin
#define LEDC_CHANNEL  0
#define LEDC_FREQUENCY 1000
#define LEDC_RESOLUTION 8

/*
void buzz(int frequency, int duration) {
    ledcSetup(LEDC_CHANNEL, frequency, LEDC_RESOLUTION);  // Configure the PWM channel
    ledcAttachPin(BUZZER_PIN, LEDC_CHANNEL);  // Attach buzzer pin to PWM channel
    ledcWrite(LEDC_CHANNEL, 128);   // 50% duty cycle (128 out of 255 for 8-bit resolution)

    delay(duration);  // Wait for the duration

    ledcWrite(LEDC_CHANNEL, 0);  // Stop sound
}*/

// Initialize RFID and WiFiClient
MFRC522 mfrc522(SS_PIN, RST_PIN);
WiFiClient client;

// Default MIFARE Classic key for authentication
MFRC522::MIFARE_Key key;

// NTP Configuration
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", 0, 60000); // UTC time, updates every 60 seconds

void initTime() {
    timeClient.begin();
    timeClient.update();
}

// Function to get the current date and time
String getCurrentDateTime() {
    timeClient.update();
    int year = 1970 + timeClient.getEpochTime() / 31556926; // Approximate year calculation
    int month = (timeClient.getEpochTime() % 31556926) / 2629743 + 1;
    int day = (timeClient.getEpochTime() % 2629743) / 86400 + 1;
    String date = String(year) + "-" + String(month) + "-" + String(day);

    String time = timeClient.getFormattedTime();
    return date + " " + time;
}

void connectWiFi() {
    Serial.print("Connecting to WiFi...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 10) {
        delay(1000);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ Connected to WiFi!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ WiFi connection failed. Restarting...");
        alert();
        ESP.restart();
    }
}

// sending post request including task_id and card_id
void sendPostRequest(const String &uid) {
    HTTPClient http;
    http.begin(client, SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(10000);

    StaticJsonDocument<200> jsonDoc;
    jsonDoc["task_id"] = 1;
    jsonDoc["uid"] = uid;

    String requestBody;
    serializeJson(jsonDoc, requestBody);
    
    Serial.println("📡 Sending JSON: " + requestBody);

    int httpResponseCode = http.POST(requestBody);

    if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println("✅ Response: " + response);
        parseAndWriteJson(response);
    } else {
        Serial.println("❌ HTTP Request Failed! Error Code: " + String(httpResponseCode));
        alert();
    }
    

    http.end();
}


String getUID() {
    String cardUID = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
        if (mfrc522.uid.uidByte[i] < 0x10) {
            cardUID += "0";
        }
        cardUID += String(mfrc522.uid.uidByte[i], HEX);
    }
    cardUID.toUpperCase();
    return cardUID;
}


bool writeBlockData(byte block, byte *buffer) {
    if (mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)) != MFRC522::STATUS_OK) {
        Serial.println("❌ Authentication failed!");
        alert();
        return false;
    }

    if (mfrc522.MIFARE_Write(block, buffer, 16) != MFRC522::STATUS_OK) {
        Serial.println("❌ Writing failed!");
        alert();
        return false;
    }

    Serial.println("✅ Writing successful!");
    success();
    //buzz(5000,1000);
    return true;
}

// function to convert to integer
String intToBinary(int num) {
    String binaryString = "";
    for (int i = 31; i >= 0; i--) {  // 32-bit integer
        binaryString += (num & (1 << i)) ? "1" : "0"; 
        if (i % 4 == 0) binaryString += " ";  // Space for readability
    }
    return binaryString;
}

void success(){
    digitalWrite(BUZZER_PIN, HIGH);
    delay(1000);
    digitalWrite(BUZZER_PIN, LOW);
}

void alert(){
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
    digitalWrite(BUZZER_PIN, HIGH);
    delay(100);
    digitalWrite(BUZZER_PIN, LOW);
}


void parseAndWriteJson(const String &jsonData) {
    StaticJsonDocument<512> jsonDoc; // Increase size if needed
    DeserializationError error = deserializeJson(jsonDoc, jsonData);
    if (error) {
        Serial.println("❌ JSON Parsing failed!");
        alert();
        return;
    }

    String nic = jsonDoc["nic"].as<String>();
    int price = jsonDoc["amount"];
    int stationId = 0;  // Set station ID to 0
    uint32_t timestamp = timeClient.getEpochTime(); // Get compact date-time

    // Ensure timestamp is valid before using
    if (timestamp == 0) {
        Serial.println("❌ Invalid timestamp!");
        alert();
        return;
    }

    Serial.print("✅ Parsed price: ");
    Serial.println(price, DEC);  // Print price in decimal for debugging

    byte block1[16] = {0};
    byte block4[16] = {0};

    // Copy NIC to block1, ensuring null termination
    strncpy((char*)block1, nic.c_str(), sizeof(block1) - 1);
    block1[sizeof(block1) - 1] = '\0';  // Ensure null termination

    // Convert price to 4 bytes (Big Endian)
    block4[0] = (price >> 24) & 0xFF;
    block4[1] = (price >> 16) & 0xFF;
    block4[2] = (price >> 8) & 0xFF;
    block4[3] = price & 0xFF;

    // Convert station ID to 2 bytes
    block4[4] = (stationId >> 8) & 0xFF;
    block4[5] = stationId & 0xFF;

    // Convert timestamp to 4 bytes
    block4[6] = (timestamp >> 24) & 0xFF;
    block4[7] = (timestamp >> 16) & 0xFF;
    block4[8] = (timestamp >> 8) & 0xFF;
    block4[9] = timestamp & 0xFF;

    // Debugging Output - Print Block Data in Hex
    Serial.print("Block 1: ");
    for (int i = 0; i < 16; i++) {
        Serial.printf("%02X ", block1[i]);  // Print as HEX with leading zeros
    }
    Serial.println();

    Serial.print("Block 4: ");
    for (int i = 0; i < 16; i++) {
        Serial.printf("%02X ", block4[i]);  // Print as HEX with leading zeros
    }
    Serial.println();

    // Write to RFID
    writeBlockData(1, block1);
    writeBlockData(4, block4);
}



void setup() {
    pinMode(BUZZER_PIN, OUTPUT);
    Serial.begin(115200);
    SPI.begin();
    mfrc522.PCD_Init();
    connectWiFi();

    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    Serial.println("🔹 Setup Complete! Ready to scan cards.");
}

void loop() {
    if (!mfrc522.PICC_IsNewCardPresent()) {
        delay(500); // Prevent CPU overload
        return;
    }

    if (!mfrc522.PICC_ReadCardSerial()) {
        Serial.println("⚠️ Failed to read card. Retrying...");
        return;
    }

    Serial.println("\n🔹 Card Detected!");
    String cardUID = getUID();
    Serial.println("UID: " + cardUID);

    sendPostRequest(cardUID);

    // Halt the card and stop communication
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();

    delay(2000); // Add a delay to prevent multiple readings of the same card
}
