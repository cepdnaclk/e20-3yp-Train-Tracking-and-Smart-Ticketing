#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// WiFi Credentials
#define WIFI_SSID "SIGNAL_NA"
#define WIFI_PASSWORD "new_password"

// API Endpoint
#define SERVER_URL "http://192.168.8.119:8000/api/card/read/"

// RFID Module Pins
#define SS_PIN 5
#define RST_PIN 4

// Buzzer
#define BUZZER_PIN 4

// Station ID
#define STATION_ID 501

// RFID and LCD
MFRC522 mfrc522(SS_PIN, RST_PIN);
WiFiClient client;
LiquidCrystal_I2C lcd(0x27, 16, 2);  // I2C address 0x27, 16 columns, 2 rows
MFRC522::MIFARE_Key key;

void setup() {
    Serial.begin(115200);
    pinMode(BUZZER_PIN, OUTPUT);

    SPI.begin();
    mfrc522.PCD_Init();
    lcd.init();
    lcd.backlight();

    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    connectWiFi();

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Scan Your Card");
}

void loop() {
    if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
        return;
    }

    Serial.println("\n🔹 Card Detected!");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Card Detected");

    String cardUID = getUID();
    Serial.println("UID: " + cardUID);
    lcd.setCursor(0, 1);
    lcd.print("UID:");
    lcd.print(cardUID.substring(0, 6));

    byte block1[18], block4[18];
    readBlockData(1, block1);
    readBlockData(4, block4);

    int price = (block4[0] << 24) | (block4[1] << 16) | (block4[2] << 8) | block4[3];
    int stationId = (block4[4] << 8) | block4[5];
    String date = String((char*)&block4[6]);

    sendPostRequest(cardUID, (char*)block1, price, stationId, date);

    delay(500);
}

void connectWiFi() {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Connecting...");
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 10) {
        delay(1000);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nConnected to WiFi!");
        lcd.setCursor(0, 1);
        lcd.print("WiFi Connected");
        success();
    } else {
        Serial.println("\nWiFi Failed!");
        lcd.setCursor(0, 1);
        lcd.print("WiFi Failed!");
        alert();
        ESP.restart();
    }
}

void success() {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(1000);
    digitalWrite(BUZZER_PIN, LOW);
}

void alert() {
    for (int i = 0; i < 3; i++) {
        digitalWrite(BUZZER_PIN, HIGH);
        delay(100);
        digitalWrite(BUZZER_PIN, LOW);
        delay(100);
    }
}

String getUID() {
    String cardUID = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
        if (mfrc522.uid.uidByte[i] < 0x10) cardUID += "0";
        cardUID += String(mfrc522.uid.uidByte[i], HEX);
    }
    cardUID.toUpperCase();
    return cardUID;
}

void readBlockData(byte block, byte *buffer) {
    MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
        MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid));

    if (status != MFRC522::STATUS_OK) {
        Serial.print("Auth failed: ");
        Serial.println(mfrc522.GetStatusCodeName(status));
        lcd.clear();
        lcd.print("Auth Failed");
        alert();
        return;
    }

    byte len = 18;
    memset(buffer, 0, len);
    status = mfrc522.MIFARE_Read(block, buffer, &len);

    if (status != MFRC522::STATUS_OK) {
        Serial.print("Read failed: ");
        Serial.println(mfrc522.GetStatusCodeName(status));
        lcd.clear();
        lcd.print("Read Failed");
        alert();
    }
}

bool writeBlockData(byte block, byte *buffer) {
    if (mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)) != MFRC522::STATUS_OK) {
        Serial.println("Authentication failed!");
        lcd.clear();
        lcd.print("Write Auth Fail");
        alert();
        return false;
    }

    if (mfrc522.MIFARE_Write(block, buffer, 16) != MFRC522::STATUS_OK) {
        Serial.println("Write failed!");
        lcd.clear();
        lcd.print("Write Failed");
        alert();
        return false;
    }

    Serial.println("Write success!");
    success();
    return true;
}

byte* updateBlock4(byte block4[16], int newPrice) {
    block4[0] = (newPrice >> 24) & 0xFF;
    block4[1] = (newPrice >> 16) & 0xFF;
    block4[2] = (newPrice >> 8) & 0xFF;
    block4[3] = newPrice & 0xFF;
    block4[4] = 0x00; // Station ID set to 0
    block4[5] = 0x00;
    return block4;
}

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
        Serial.println("✅ Response: " + response);
        StaticJsonDocument<200> jsonDoc2;
        DeserializationError error = deserializeJson(jsonDoc2, response);

        if (!error) {
            int new_price = jsonDoc2["new_amount"];
            Serial.println("💰 new_price: Rs " + String(new_price));
            byte block4[16] = {0};
            updateBlock4(block4, new_price);
            writeBlockData(4, block4);

            lcd.clear();
            lcd.setCursor(0, 0);
            lcd.print("Updated Balance:");
            lcd.setCursor(0, 1);
            lcd.print("Rs ");
            lcd.print(new_price);
        } else {
            lcd.clear();
            lcd.print("JSON Parse Err");
            alert();
        }

        success();
    } else {
        Serial.println("❌ HTTP Error: " + String(httpResponseCode));
        lcd.clear();
        lcd.print("API Error");
        alert();
    }

    http.end();
}
