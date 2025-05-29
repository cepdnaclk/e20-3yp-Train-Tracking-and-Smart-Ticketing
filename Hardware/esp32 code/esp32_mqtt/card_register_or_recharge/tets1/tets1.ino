#include "secrets.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <LiquidCrystal_I2C.h>
#include <MQTTClient.h>
#include <vector>
#include "LittleFS.h"

// variable to store the csv file
File ticketFile;

// data structure to store the ticket prices and the distance
struct TicketInfo {
  float distance_km;
  float class1_price;
  float class2_price;
  float class3_price;
};

// variables for offline mode
unsigned long lastWiFiCheck = 0;
const unsigned long WIFI_CHECK_INTERVAL = 5 * 60 * 1000; // 5 minutes
bool isWiFiConnected = false;
bool isMQTTConnected = false;
bool shouldConnectAWS = false;

// vector to store the requests arrive in offline mode
std::vector<String> nicQueue;

// LCD Setup (Check I2C address, try 0x3F if 0x27 doesn’t work)
LiquidCrystal_I2C lcd(0x27, 16, 2);

// RFID Module Pins
#define SS_PIN 5
#define RST_PIN 4

// define variables
#define STATION_ID 500

// amount variable
#define min_amount 100

// Initialize RFID and WiFiClient
MFRC522 mfrc522(SS_PIN, RST_PIN);
WiFiClientSecure net;

// Initiating MQTT client
MQTTClient client(256);

// Default MIFARE Classic key
MFRC522::MIFARE_Key key;

// NTP Configuration
WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", 19800, 60000); // UTC

void initTime() {
    timeClient.begin();
    timeClient.update();
}

// supportive function to display a message on lcd
void lcdLog(const String &message, int row = 0) {
    lcd.setCursor(0, row);
    lcd.print("                ");  // Clear the row
    lcd.setCursor(0, row);
    lcd.print(message);
}

// taking the current time
String getCurrentDateTime() {
    timeClient.update();
    time_t rawTime = timeClient.getEpochTime();
    struct tm *timeInfo = localtime(&rawTime);
    char buffer[30];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", timeInfo);
    return String(buffer);
}

/*
// connecting to wifi
void connectWiFi() {
    Serial.print("Connecting to WiFi...");
    lcd.clear();
    lcdLog("Connecting WiFi...");

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 10) {
        delay(1000);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        isWiFiConnected = true;
        processPayloadQueue();
        Serial.println("\n✅ Connected to WiFi!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());
        lcd.clear();
        lcdLog("WiFi Connected", 0);
        lcd.setCursor(0, 1);
        lcd.print(WiFi.localIP());
    } else {
        isWiFiConnected = false;
        Serial.println("\n❌ WiFi failed.");
        lcd.clear();
        lcdLog("WiFi Failed!", 0);
        delay(3000);
        //ESP.restart();
        lcdLog("Offline mode...", 0);
        delay(2000);
    }
}*/

// take actions looking at the type of message received
void messageHandler(String &topic, String &payload) {
    Serial.println("Message received:");
    Serial.println("Topic: " + topic);
    Serial.println("Payload: " + payload);
    StaticJsonDocument<512> jsonDoc;
    DeserializationError error = deserializeJson(jsonDoc, payload);
    if (error) {
        Serial.println("JSON Parsing failed!");
        lcd.clear();
        lcdLog("JSON Parse Error!");
        return;
    }
    int task_id = jsonDoc["task_id"];
    String nic = jsonDoc["nic"].as<String>();
    int price = jsonDoc["amount"];
    if (task_id == 1){
        byte block5[16] = {0};
        byte block4[16] = {0};

        strncpy((char*)block5, nic.c_str(), sizeof(block5) - 1);
        block5[sizeof(block5) - 1] = '\0';

        block4[0] = (price >> 24) & 0xFF;
        block4[1] = (price >> 16) & 0xFF;
        block4[2] = (price >> 8) & 0xFF;
        block4[3] = price & 0xFF;

        lcd.clear();
        lcdLog("Place Card NOW", 0);
        while (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
            delay(100);
        }
        Serial.println("Card Detected");
        lcd.setCursor(0, 1);
        lcd.print(getUID());

        writeBlockData(5, block5);
        writeBlockData(4, block4);

        //verifyCardData();

        lcdLog("Done.....", 0);
        delay(2000);
        lcdLog("Place the card",0);
        lcdLog("to travel",1);
    }
}

// connecting to aws and subscribing to a topic
void awsConnect() {
    net.setCACert(AWS_CERT_CA);
    net.setCertificate(AWS_CERT_CRT);
    net.setPrivateKey(AWS_CERT_PRIVATE);

    client.begin(AWS_IOT_ENDPOINT, 8883, net);
    client.onMessage(messageHandler);

    lcdLog("Connecting AWS", 0);
    delay(500);
    int attempts = 0;
    while (!client.connect(THINGNAME) && attempts < 10) {
        delay(1000);
        lcdLog("Retry AWS...", 1);
        attempts++;
    }
    if (client.connect(THINGNAME)){
        isMQTTConnected = true;
    }

    if (client.subscribe(AWS_IOT_SUBSCRIBE_TOPIC)) {
        lcdLog("Subscribed AWS", 0);
        delay(500);
    } else {
        lcdLog("Sub Failed", 1);
    }
}

/*
void sendPostRequest(const String &uid) {
    HTTPClient http;
    http.begin(net, SERVER_URL);
    http.addHeader("Content-Type", "application/json");

    StaticJsonDocument<200> jsonDoc;
    jsonDoc["task_id"] = 1;
    jsonDoc["uid"] = uid;

    String requestBody;
    serializeJson(jsonDoc, requestBody);

    Serial.println("📡 Sending JSON: " + requestBody);
    lcd.clear();
    lcdLog("Sending to API...");

    int httpResponseCode = http.POST(requestBody);

    if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println("✅ Response: " + response);
        lcd.clear();
        lcdLog("API Success!");
        parseAndWriteJson(response);
    } else {
        Serial.println("❌ HTTP Request Failed! Code: " + String(httpResponseCode));
        lcd.clear();
        lcdLog("API Failed!", 0);
        lcd.setCursor(0, 1);
        lcd.print("Code: ");
        lcd.print(httpResponseCode);
    }

    http.end();
}
*/

// read cardID
String getUID() {
    String cardUID = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
        if (mfrc522.uid.uidByte[i] < 0x10) cardUID += "0";
        cardUID += String(mfrc522.uid.uidByte[i], HEX);
    }
    cardUID.toUpperCase();
    return cardUID;
}

// write to a certain block
bool writeBlockData(byte block, byte *buffer) {
    if (mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)) != MFRC522::STATUS_OK) {
        Serial.println("❌ Authentication failed!");
        lcd.clear();
        lcdLog("Auth Failed!", 0);
        lcd.setCursor(0, 1);
        lcd.print("Block ");
        lcd.print(block);
        delay(2000);
        return false;
    }

    if (mfrc522.MIFARE_Write(block, buffer, 16) != MFRC522::STATUS_OK) {
        Serial.println("❌ Writing failed!");
        lcd.clear();
        lcdLog("Write Failed!", 0);
        lcd.setCursor(0, 1);
        lcd.print("Block ");
        lcd.print(block);
        delay(2000);
        return false;
    }

    Serial.println("✅ Writing successful!");
    lcd.clear();
    lcdLog("Write Success", 0);
    lcd.setCursor(0, 1);
    lcd.print("Block ");
    lcd.print(block);
    delay(2000);
    return true;
}

// read data from a certain block
bool readBlockData(byte block, byte *buffer) {
    byte size = 18;
    if (mfrc522.PCD_Authenticate(MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)) != MFRC522::STATUS_OK) {
        Serial.println("❌ Authentication failed!");
        lcd.clear();
        lcdLog("Auth Failed!", 0);
        lcd.setCursor(0, 1);
        lcd.print("Block ");
        lcd.print(block);
        return false;
    }

    if (mfrc522.MIFARE_Read(block, buffer, &size) != MFRC522::STATUS_OK) {
        Serial.println("❌ Reading failed!");
        lcd.clear();
        lcdLog("Read Failed!", 0);
        lcd.setCursor(0, 1);
        lcd.print("Block ");
        lcd.print(block);
        return false;
    }

    Serial.println("✅ Read successful!");
    Serial.print("Block ");
    Serial.print(block);
    Serial.print(": ");
    for (int i = 0; i < 16; i++) {
        Serial.print(buffer[i], HEX);
        Serial.print(" ");
    }
    Serial.println();

    lcd.clear();
    lcdLog("Read Success", 0);
    lcd.setCursor(0, 1);
    lcd.print("Block ");
    lcd.print(block);
    return true;
}

// function which runs when card is first kept
void verifyCardData() {
    byte buffer1[18];
    byte buffer4[18];
    String nic;
    if (readBlockData(5, buffer1)) {
        nic = String((char*)buffer1);
        Serial.println("✅ NIC Read from card: " + nic);
        lcd.clear();
        lcdLog("NIC: " + nic);
    } else {
        Serial.println("❌ Failed to read NIC from block 1");
    }

    if (readBlockData(4, buffer4)) {
        int price = (buffer4[0] << 24) | (buffer4[1] << 16) | (buffer4[2] << 8) | buffer4[3];
        int stationId = (buffer4[4] << 8) | buffer4[5];
        //uint32_t timestamp = (buffer4[6] << 24) | (buffer4[7] << 16) | (buffer4[8] << 8) | buffer4[9];

        Serial.println("✅ Price: " + String(price));
        Serial.println("Station ID: " + String(stationId));
        //Serial.println("Timestamp: " + String(timestamp));
        lcd.setCursor(0, 1);
        lcd.print("Rs: ");
        lcd.print(price);

        // if the passenger entering the station (STATION_ID = 0)
        if (stationId == 0){
            // function to implement when passenger enters
            Serial.print("stationId: " + stationId);
            passengerEnters(price, nic);
        } else {
            // when passenger exits from a station
            passengerExits(price, nic, stationId);
        }
    } else {
        Serial.println("❌ Failed to read data from block 4");
    }
}

// enqueue the json payload
void enqueueFailedPayload(const String& jsonPayload) {
  nicQueue.push_back(jsonPayload);
  Serial.println("Enqueued failed payload: " + jsonPayload);
}

// dequeue the json payload from the queue
void processPayloadQueue() {

  std::vector<String> remainingQueue;

  for (String& payload : nicQueue) {
    /*if (client.connect(THINGNAME)){
        Serial.println("Connected to AWS");
    }*/
    if (client.publish(AWS_IOT_PUBLISH_TOPIC, payload)) {
      Serial.println("Queued payload published: " + payload);
    } else {
      Serial.println("Failed to publish queued payload: " + payload);
      remainingQueue.push_back(payload);
    }
  }

  nicQueue = remainingQueue;
}

// send data to iot core and write to the card
void sendData(int amount, String &nic, int taskId){

    StaticJsonDocument<200> jsonDoc;
    jsonDoc["task_id"] = taskId;
    jsonDoc["nic"] = nic;
    jsonDoc["amount"] = amount;
    jsonDoc["station"] = STATION_ID;
    Serial.println("jsonDoc prepared");

    char jsonBuffer[256];
    serializeJson(jsonDoc, jsonBuffer);
    Serial.print("Payload: ");
    Serial.println(jsonBuffer);
    
    if (!isWiFiConnected){
        enqueueFailedPayload(jsonBuffer);
    }
    else{
        if (client.connected()) {
        client.publish(AWS_IOT_PUBLISH_TOPIC, jsonBuffer);
        lcdLog("Published to AWS", 1);
        } else {
        lcdLog("MQTT Not Conn", 1);
        }
    }
    
    uint32_t timestamp = timeClient.getEpochTime();
    if (timestamp == 0) {
        Serial.println("❌ Invalid timestamp!");
        lcd.clear();
        lcdLog("Bad Timestamp!");
        return;
    }

    byte block4[16] = {0};
    block4[0] = (amount >> 24) & 0xFF;
    block4[1] = (amount >> 16) & 0xFF;
    block4[2] = (amount >> 8) & 0xFF;
    block4[3] = amount & 0xFF;
    if (taskId == 2){
        block4[4] = (STATION_ID >> 8) & 0xFF;
        block4[5] = STATION_ID & 0xFF;
    } else if (taskId == 3){
        block4[4] = 0x00;
        block4[5] = 0x00;        
    }
    block4[6] = (timestamp >> 24) & 0xFF;
    block4[7] = (timestamp >> 16) & 0xFF;
    block4[8] = (timestamp >> 8) & 0xFF;
    block4[9] = timestamp & 0xFF;

    lcd.clear();
    Serial.println("Rewriting card already present...");
    lcd.setCursor(0, 1);
    //lcd.print(getUID());

    Serial.println("Card Detected");
    lcd.setCursor(0, 1);
    lcd.print(getUID());

    writeBlockData(4, block4);

    lcdLog("Done.....", 0);
    delay(2000);
    lcdLog("Place the card",0);
    lcdLog("to travel",1);

}

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
  shouldConnectAWS = true;
}

// function to implement passenger exit
void passengerExits(int amount, String &nic, int stationId){
    Serial.println("Passenger exiting...");
    TicketInfo ticketDetails = getTicketInfo(STATION_ID, stationId);
    int price = ticketDetails.class3_price;
    lcd.setCursor(0, 1);
    lcd.print("Price Rs: ");
    lcd.print(price, 2);
    delay(2000);
    amount = amount - price;
    lcd.setCursor(0, 1);
    lcd.print("Balance left Rs: ");
    lcd.print(amount, 2);
    delay(2000);
    // send data to aws and wite to the card
    sendData(amount, nic, 3);    
}

// function to implement when passenger enters
void passengerEnters(int amount, String &nic){
    lcdLog("Place the card!",0);
    if (amount >= min_amount){
        // send data to aws and wite to the card
        sendData(amount, nic, 2);
    }else{
        lcdLog("Balance is ", 0);
        lcdLog("Not enough....", 1);
        delay(2000);
        lcd.clear();
        lcdLog("Place the card!", 0);        
    }
}

// Fetch data from the incoming json file
void parseAndWriteJson(const String &jsonData) {
    StaticJsonDocument<512> jsonDoc;
    DeserializationError error = deserializeJson(jsonDoc, jsonData);
    if (error) {
        Serial.println("❌ JSON Parsing failed!");
        lcd.clear();
        lcdLog("JSON Parse Error!");
        return;
    }

    String nic = jsonDoc["nic"].as<String>();
    int price = jsonDoc["amount"];
    if (!jsonDoc.containsKey("nic") || !jsonDoc.containsKey("amount")) {
        lcd.clear();
        lcdLog("Invalid JSON!");
        return;
    }
    uint32_t timestamp = timeClient.getEpochTime();
    if (timestamp == 0) {
        Serial.println("❌ Invalid timestamp!");
        lcd.clear();
        lcdLog("Bad Timestamp!");
        return;
    }

    byte block1[16] = {0};
    byte block4[16] = {0};

    strncpy((char*)block1, nic.c_str(), sizeof(block1) - 1);
    block1[sizeof(block1) - 1] = '\0';

    block4[0] = (price >> 24) & 0xFF;
    block4[1] = (price >> 16) & 0xFF;
    block4[2] = (price >> 8) & 0xFF;
    block4[3] = price & 0xFF;
    block4[4] = (STATION_ID >> 8) & 0xFF;
    block4[5] = STATION_ID & 0xFF;
    block4[6] = (timestamp >> 24) & 0xFF;
    block4[7] = (timestamp >> 16) & 0xFF;
    block4[8] = (timestamp >> 8) & 0xFF;
    block4[9] = timestamp & 0xFF;

    writeBlockData(1, block1);
    writeBlockData(4, block4);
}

// handle the card reading and looping
void readCardAndHandle() {
    if (!mfrc522.PICC_IsNewCardPresent()) {
        delay(500);
        return;
    }

    if (!mfrc522.PICC_ReadCardSerial()) {
        Serial.println("⚠️ Failed to read card.");
        lcd.clear();
        lcdLog("Read Failed!");
        return;
    }

    Serial.println("\n🔹 Card Detected!");
    String cardUID = getUID();
    Serial.println("UID: " + cardUID);

    lcd.clear();
    lcdLog("Card UID:", 0);
    lcd.setCursor(0, 1);
    lcd.print(cardUID);

    verifyCardData();

    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();

    delay(2000);
}

// Initiation of LittleFS
void littleFSInnitiation(){

    if(!LittleFS.begin()){
    Serial.println("An Error has occurred while mounting LittleFS");
    return;
    }
    ticketFile = LittleFS.open("/ticket_prices.csv", "r");
    if (!ticketFile) {
        Serial.println("Failed to open /ticket_prices.csv");
    } else {
        Serial.println("File opened successfully");
    }
}

// function returns the price of the ticket and the distances
TicketInfo getTicketInfo(int fromID, int toID) {
  TicketInfo info = { -1.0, -1.0, -1.0, -1.0 }; // Default values indicating not found

  if (!ticketFile) {
    Serial.println("File not open");
    return info;
  }

  // Move to the beginning of the file
  ticketFile.seek(0, SeekSet);

  // Skip the header line
  String header = ticketFile.readStringUntil('\n');

  while (ticketFile.available()) {
    String line = ticketFile.readStringUntil('\n');
    line.trim(); // Remove any leading/trailing whitespace

    if (line.length() == 0) continue; // Skip empty lines

    // Split the line by commas
    int commaIndex1 = line.indexOf(',');
    int commaIndex2 = line.indexOf(',', commaIndex1 + 1);
    int commaIndex3 = line.indexOf(',', commaIndex2 + 1);
    int commaIndex4 = line.indexOf(',', commaIndex3 + 1);
    int commaIndex5 = line.indexOf(',', commaIndex4 + 1);

    if (commaIndex5 == -1) continue; // Malformed line

    int fileFromID = line.substring(0, commaIndex1).toInt();
    int fileToID = line.substring(commaIndex1 + 1, commaIndex2).toInt();

    if (fileFromID == fromID && fileToID == toID) {
      info.distance_km = line.substring(commaIndex2 + 1, commaIndex3).toFloat();
      info.class1_price = line.substring(commaIndex3 + 1, commaIndex4).toFloat();
      info.class2_price = line.substring(commaIndex4 + 1, commaIndex5).toFloat();
      info.class3_price = line.substring(commaIndex5 + 1).toFloat();
      break;
    }
  }

  return info;
}


// set aws connect to run on a differen core
/*
void onWiFiGotIP(WiFiEvent_t event, WiFiEventInfo_t info) {
  Serial.print("WiFi Connected. IP Address: ");
  Serial.println(WiFi.localIP());
  isWiFiConnected = true;

  // Run AWS connect and queue processing in its own task
    xTaskCreatePinnedToCore(
    awsConnectTask,     // task function
    "AWSConnectTask",   // task name
    8192,               // stack size
    NULL,               // task parameters
    1,                  // priority
    NULL,               // task handle (optional)
    0                   // run on core 0
  );
}*/

void setup() {
    Serial.begin(115200);
    littleFSInnitiation();
    WiFi.mode(WIFI_STA);
    SPI.begin();
    mfrc522.PCD_Init();
    for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;

    lcd.init();
    lcd.backlight();
    lcdLog("Starting...", 0);

    // Register WiFi and IP event handlers
    WiFi.onEvent(onWiFiDisconnected, ARDUINO_EVENT_WIFI_STA_DISCONNECTED);
    WiFi.onEvent(onWiFiGotIP, ARDUINO_EVENT_WIFI_STA_GOT_IP);

    // Set Wi-Fi to station mode and initiate connection
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    Serial.println("Attempting to connect to WiFi...");


    awsConnect();
    initTime();

    lcd.clear();
    lcdLog("System Ready", 0);
    lcd.setCursor(0, 1);
    lcd.print("Place a Card");
    Serial.println("Setup Complete! Ready to scan cards.");
}

void loop() {
    if (shouldConnectAWS) {
        awsConnect();
    if (!nicQueue.empty()) {
        processPayloadQueue();
    }
        shouldConnectAWS = false;
    }
    readCardAndHandle();
    client.loop();

}
