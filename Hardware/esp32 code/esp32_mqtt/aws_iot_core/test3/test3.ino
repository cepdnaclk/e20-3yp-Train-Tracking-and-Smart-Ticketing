#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>

// WiFi Credentials
#define WIFI_SSID "Redmi 9T"
#define WIFI_PASSWORD "qwertyuiop"

// API Endpoint
#define SERVER_URL "http://192.168.42.64:8000/api/card/read/"

// RFID Module Pins
#define SS_PIN 5
#define RST_PIN 22

// Station details
#define STATION_ID 501

// for buzzer
#define BUZZER_PIN 4  // Change this to your preferred GPIO pin

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
        Serial.println("\n Connected to WiFi!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());
        success();
    } else {
        Serial.println("\n WiFi connection failed. Restarting...");
        alert();
        ESP.restart();
    }
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

void receiveJsonFromAPI() {
    HTTPClient http;
    http.begin(client, SERVER_URL);
    int httpResponseCode = http.GET();
    
    if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println(" Received JSON: " + response);
        success();
        parseAndWriteJson(response);
    } else {
        Serial.println(" Failed to receive JSON. Error Code: " + String(httpResponseCode));
        alert();
    }
    
    http.end();
}

// if the card is authorized

void sendPostRequest(const String &uid, const String &nic, int price, int stationId, const String &date) {
    HTTPClient http;
    http.begin(client, SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(10000);

    StaticJsonDocument<200> jsonDoc;
    jsonDoc["task_id"] = 3;
    jsonDoc["uid"] = uid;
    jsonDoc["nic"] = nic;
    jsonDoc["amount"] = price;
    jsonDoc["station_id"] = stationId;
    jsonDoc["date"] = date;
    jsonDoc["this_station"] = STATION_ID;
    
    String requestBody;
    serializeJson(jsonDoc, requestBody);
    
    Serial.println("📡 Sending JSON: " + requestBody);

    int httpResponseCode = http.POST(requestBody);
    String response = http.getString();
    if (httpResponseCode > 0) {
        Serial.println(" Response: " + response);
        success();
        StaticJsonDocument<200> jsonDoc2;
        DeserializationError error = deserializeJson(jsonDoc2, response);
        int new_price = jsonDoc2["new_amount"];
        Serial.println("new_price: Rs " + new_price);
        byte block4[16] = {0};
        byte* updatedBlock4 = updateBlock4(block4, new_price);
        writeBlockData(4, block4);
    } else {
        Serial.println(" HTTP Request Failed! Error Code: " + String(httpResponseCode));
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

void readBlockData(byte block, byte *buffer) {
    MFRC522::MIFARE_Key key;
    byte len = 18;  // Buffer size

    // Initialize key to default FFFFFFFFFFFFh
    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    // Authenticate using Key A
    MFRC522::StatusCode status = mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid));
    if (status != MFRC522::STATUS_OK) {
        Serial.print(" Authentication failed: ");
        alert();
        Serial.println(mfrc522.GetStatusCodeName(status));
        return;
    }

    // Read block data
    memset(buffer, 0, len);  // Clear buffer before reading
    status = mfrc522.MIFARE_Read(block, buffer, &len);
    if (status != MFRC522::STATUS_OK) {
        Serial.print(" Reading failed: ");
        alert();
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


bool writeBlockData(byte block, byte *buffer) {
    if (mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)) != MFRC522::STATUS_OK) {
        Serial.println(" Authentication failed!");
        alert();
        return false;
    }

    if (mfrc522.MIFARE_Write(block, buffer, 16) != MFRC522::STATUS_OK) {
        Serial.println(" Writing failed!");
        alert();
        return false;
    }

    Serial.println(" Writing successful!");
    success();
    return true;
}

byte* updateBlock4(byte block4[16], int newPrice) {
    // Set station ID to 0 (stored in block4[4] and block4[5])
    block4[4] = 0x00;
    block4[5] = 0x00;

    // Convert price to 4 bytes (Big Endian) and update block4
    block4[0] = (newPrice >> 24) & 0xFF;
    block4[1] = (newPrice >> 16) & 0xFF;
    block4[2] = (newPrice >> 8) & 0xFF;
    block4[3] = newPrice & 0xFF;

    return block4;  // Return the updated block4
}



void parseAndWriteJson(const String &jsonData) {
    StaticJsonDocument<200> jsonDoc;
    DeserializationError error = deserializeJson(jsonDoc, jsonData);
    if (error) {
        Serial.println(" JSON Parsing failed!");
        alert();
        return;
    }

    String nic = jsonDoc["nic"].as<String>();
    int price = jsonDoc["price"];
    int stationId = jsonDoc["station_id"];
    String date = jsonDoc["date"].as<String>();

    byte block1[16] = {0};
    byte block4[16] = {0};

    strncpy((char*)block1, nic.c_str(), 16);
    block4[0] = (price >> 24) & 0xFF;
    block4[1] = (price >> 16) & 0xFF;
    block4[2] = (price >> 8) & 0xFF;
    block4[3] = price & 0xFF;
    block4[4] = (stationId >> 8) & 0xFF;
    block4[5] = stationId & 0xFF;
    strncpy((char*)&block4[6], date.c_str(), 10);

    writeBlockData(1, block1);
    writeBlockData(4, block4);
}

void setup() {
    Serial.begin(115200);
    pinMode(BUZZER_PIN, OUTPUT);
    SPI.begin();
    mfrc522.PCD_Init();
    connectWiFi();

    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    Serial.println(" Setup Complete! Ready to scan cards.");
}


void loop() {
    if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
        return;
    }

    Serial.println("\n🔹 Card Detected!");
    String cardUID = getUID();
    Serial.println("UID: " + cardUID);

    byte block1[18];
    byte block4[18];

    readBlockData(1, block1);
    readBlockData(4, block4);

    sendPostRequest(cardUID, (char*)block1, (block4[0] << 24) | (block4[1] << 16) | (block4[2] << 8) | block4[3], (block4[4] << 8) | block4[5], (char*)&block4[6]);


    delay(500);
}
