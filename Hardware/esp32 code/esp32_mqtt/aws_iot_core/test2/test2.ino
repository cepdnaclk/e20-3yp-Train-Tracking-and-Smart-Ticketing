#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>

// WiFi Credentials
#define WIFI_SSID "SIGNAL_NA"
#define WIFI_PASSWORD "new_password"

// API Endpoint
#define SERVER_URL "http://192.168.8.119:8000/api/card/read/"

// RFID Module Pins
#define SS_PIN 5
#define RST_PIN 22

// Define variables
#define Station_ID 111

// Initialize RFID and WiFiClient
MFRC522 mfrc522(SS_PIN, RST_PIN);
WiFiClient client;

// Default MIFARE Classic key for authentication
MFRC522::MIFARE_Key key;

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
        ESP.restart();
    }
}

// Function to read data from an RFID block and print as 1s and 0s
void readBlockData(byte block) {
    byte buffer[18];  // Buffer to store block data
    byte len = sizeof(buffer);

    // Authenticate using Key A
    MFRC522::StatusCode status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid));
    if (status != MFRC522::STATUS_OK) {
        Serial.print("❌ Authentication failed on Block ");
        Serial.print(block);
        Serial.print(": ");
        Serial.println(mfrc522.GetStatusCodeName(status));
        return;
    }

    // Read block data
    memset(buffer, 0, len);  // Clear buffer before reading
    status = mfrc522.MIFARE_Read(block, buffer, &len);
    if (status != MFRC522::STATUS_OK) {
        Serial.print("❌ Reading failed on Block ");
        Serial.print(block);
        Serial.print(": ");
        Serial.println(mfrc522.GetStatusCodeName(status));
        return;
    }

    // Print block data as 1s and 0s
    Serial.print("Block ");
    Serial.print(block);
    Serial.print(": ");
    for (int i = 0; i < 16; i++) {
        for (int bit = 7; bit >= 0; bit--) {
            Serial.print((buffer[i] >> bit) & 1); // Print each bit
        }
        Serial.print(" ");  // Space between bytes
    }
    Serial.println();
}

// Function to get the UID of the detected card
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

void setup() {
    Serial.begin(115200);
    SPI.begin();
    mfrc522.PCD_Init();
    connectWiFi();

    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF; // Set default key

    Serial.println("🔹 Setup Complete! Ready to scan cards.");
}

void loop() {
    // Wait for a new card to be present
    if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
        return;
    }

    Serial.println("\n🔹 Card Detected!");
    String cardUID = getUID();
    Serial.println("UID: " + cardUID);

    // Read Block 1 and Block 4
    readBlockData(1);  
    readBlockData(4);
    
    Serial.println("**Reading Complete**\n");

    // Halt communication with the card
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();

    delay(2000); // Prevent duplicate reads
}
