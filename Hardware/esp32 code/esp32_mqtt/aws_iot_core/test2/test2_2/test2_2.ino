#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>
#include <LiquidCrystal_I2C.h>  // ✅ NEW

// WiFi Credentials
#define WIFI_SSID "SIGNAL_NA"
#define WIFI_PASSWORD "new_password"

// API Endpoint
#define SERVER_URL "http://192.168.8.119:8000/api/card/read/"

// RFID Module Pins
#define SS_PIN 5
#define RST_PIN 4

// Station details
#define STATION_ID 500

// Buzzer
#define BUZZER_PIN 4

// Initialize RFID, WiFiClient, and LCD
MFRC522 mfrc522(SS_PIN, RST_PIN);
WiFiClient client;
MFRC522::MIFARE_Key key;

LiquidCrystal_I2C lcd(0x27, 16, 2);  // ✅ Adjust address if needed

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

void connectWiFi() {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Connecting WiFi");

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
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("WiFi Connected");
        lcd.setCursor(0, 1);
        lcd.print(WiFi.localIP());
    } else {
        Serial.println("\n WiFi Failed. Restarting...");
        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print("WiFi Failed...");
        delay(2000);
        ESP.restart();
    }
}

void sendPostRequest(const String &uid, const String &nic, int price, int stationId, const String &date) {
    HTTPClient http;
    http.begin(client, SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(10000);

    StaticJsonDocument<200> jsonDoc;
    jsonDoc["task_id"] = 2;
    jsonDoc["uid"] = uid;
    jsonDoc["nic"] = nic;
    jsonDoc["price"] = price;
    jsonDoc["station_id"] = stationId;
    jsonDoc["date"] = date;

    String requestBody;
    serializeJson(jsonDoc, requestBody);

    Serial.println("📡 Sending JSON: " + requestBody);
    int httpResponseCode = http.POST(requestBody);
    String response = http.getString();

    lcd.clear();
    lcd.setCursor(0, 0);

    if (httpResponseCode > 0) {
        Serial.println(" Response: " + response);
        StaticJsonDocument<200> jsonDoc2;
        DeserializationError error = deserializeJson(jsonDoc2, response);

        String message = jsonDoc2["message"].as<String>();
        lcd.print("Card: " + message.substring(0, 11));
        lcd.setCursor(0, 1);

        if (message == "Card is valid") {
            Serial.println("Card is Valid............");

            if (price < 1000) {
                Serial.println("Not enough money");
                lcd.print("Low Balance");
                return;
            }

            if (stationId == 0) {
                Serial.println("Fraud Detected");
                lcd.print("Invalid Station");
                return;
            }

            lcd.print("Access Granted");
            success();
        } else {
            lcd.print("Access Denied");
            alert();
        }
    } else {
        Serial.println(" HTTP Request Failed! Error Code: " + String(httpResponseCode));
        lcd.print("HTTP Error");
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
    byte len = 18;
    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    if (mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)) != MFRC522::STATUS_OK) {
        Serial.println("Authentication failed");
        alert();
        return;
    }

    memset(buffer, 0, len);
    if (mfrc522.MIFARE_Read(block, buffer, &len) != MFRC522::STATUS_OK) {
        Serial.println("Read failed");
        alert();
        return;
    }
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

byte* updateStationId(byte block4[16], int stationId) {
    block4[4] = (stationId >> 8) & 0xFF;
    block4[5] = stationId & 0xFF;
    return block4;
}

void setup() {
    Serial.begin(115200);
    pinMode(BUZZER_PIN, OUTPUT);
    SPI.begin();
    mfrc522.PCD_Init();
    lcd.init();        // ✅ LCD setup
    lcd.backlight();   // ✅ Enable backlight

    connectWiFi();

    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Ready to Scan...");
    Serial.println("🔹 Setup Complete! Ready to scan cards.");
}

void loop() {
    if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
        return;
    }

    Serial.println("\n🔹 Card Detected!");
    String cardUID = getUID();
    Serial.println("UID: " + cardUID);

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("UID:");
    lcd.setCursor(0, 1);
    lcd.print(cardUID.substring(0, 16));

    byte block1[18];
    byte block4[18];

    readBlockData(1, block1);
    readBlockData(4, block4);

    sendPostRequest(cardUID, (char*)block1,
        (block4[0] << 24) | (block4[1] << 16) | (block4[2] << 8) | block4[3],
        (block4[4] << 8) | block4[5],
        (char*)&block4[6]
    );

    updateStationId(block4, STATION_ID);
    writeBlockData(4, block4);

    delay(1000);
}
