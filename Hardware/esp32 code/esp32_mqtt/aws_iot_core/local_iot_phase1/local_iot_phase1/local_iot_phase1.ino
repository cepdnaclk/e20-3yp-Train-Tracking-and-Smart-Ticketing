#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>

// WiFi Credentials
#define WIFI_SSID "UPUL slt fiber"
#define WIFI_PASSWORD "panawennage2020"

// API Endpoint
#define SERVER_URL "http://192.168.137.241/rfid_api"
const String VERIFY_CARD_URL = String(SERVER_URL) + "/verify_card.php";

// RFID Module Pins
#define SS_PIN 5
#define RST_PIN 22

// Initialize RFID and WiFiClient
MFRC522 rfid(SS_PIN, RST_PIN);
WiFiClient client;

// Function to connect to WiFi
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

// Function to send HTTP POST request
String sendPostRequest(const String &url, const String &uid) {
    HTTPClient http;  // Declare locally to avoid memory issues
    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");  

    StaticJsonDocument<100> jsonDoc;
    jsonDoc["uid"] = uid;
    
    String requestBody;
    serializeJson(jsonDoc, requestBody);
    
    Serial.println("📡 Sending JSON: " + requestBody);

    int httpResponseCode = http.POST(requestBody);
    String response = "";

    if (httpResponseCode > 0) {
        response = http.getString();
        Serial.println("✅ Response: " + response);
    } else {
        Serial.println("❌ HTTP Request Failed! Error Code: " + String(httpResponseCode));
    }

    http.end();  // Close connection
    return response;
}

// Function to verify card in the database
bool verifyCard(const String &uid) {
    Serial.println("\n🔹 Verifying Card...");
    
    String response = sendPostRequest(VERIFY_CARD_URL, uid);

    // Check if the response is empty
    if (response.isEmpty()) {
        Serial.println("⚠️ Empty response from server!");
        return false;
    }

    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, response);

    if (error) {
        Serial.println("❌ JSON Parsing Failed! Response: " + response);
        return false;
    }

    bool cardExists = doc["exists"];
    Serial.println(cardExists ? "✅ Authorized" : "⚠️ Not Authorized");
    return cardExists;
}

// Function to get card UID as uppercase string with zero-padding
String getUID() {
    String cardUID = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
        if (rfid.uid.uidByte[i] < 0x10) {
            cardUID += "0"; // Ensure two-digit hex values
        }
        cardUID += String(rfid.uid.uidByte[i], HEX);
    }
    cardUID.toUpperCase();  // Convert to uppercase
    return cardUID;
}

// Function to check and process RFID card
void checkRFID() {
    if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
        return;
    }

    Serial.println("\n🔹 Card Detected!");
    String cardUID = getUID();
    Serial.println("UID: " + cardUID);

    bool authorized = verifyCard(cardUID);
    if (authorized) {
        Serial.println("🚪 Access Granted!");
        // Perform some action like unlocking a door
    } else {
        Serial.println("⛔ Access Denied!");
    }

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
}

// Setup function
void setup() {
    Serial.begin(115200);
    SPI.begin();
    rfid.PCD_Init();
    connectWiFi();
}

// Main loop
void loop() {
    checkRFID();
    delay(500);  // Reduce CPU usage and prevent rapid re-scanning
}
