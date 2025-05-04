#include <WiFi.h>
#include <PubSubClient.h>
#include <WiFiClientSecure.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// AWS IoT Core credentials
const char* awsEndpoint = "YOUR_AWS_IOT_ENDPOINT";  // Example: "a3teh89xyz-ats.iot.us-west-2.amazonaws.com"
const char* mqttTopic = "esp32/data";  // Change the topic as needed

// AWS IoT Certificates
const char* awsRootCA = R"EOF(
-----BEGIN CERTIFICATE-----
YOUR_AWS_ROOT_CA_CERTIFICATE_HERE
-----END CERTIFICATE-----
)EOF";

const char* clientCert = R"EOF(
-----BEGIN CERTIFICATE-----
YOUR_DEVICE_CERTIFICATE_HERE
-----END CERTIFICATE-----
)EOF";

const char* privateKey = R"EOF(
-----BEGIN RSA PRIVATE KEY-----
YOUR_PRIVATE_KEY_HERE
-----END RSA PRIVATE KEY-----
)EOF";

// WiFi and MQTT clients
WiFiClientSecure espClient;
PubSubClient mqttClient(espClient);

// Function to connect to WiFi
void connectWiFi() {
    Serial.print("Connecting to WiFi...");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.print(".");
    }
    Serial.println("\nConnected to WiFi");
}

// Function to connect to AWS IoT
void connectAWSIoT() {
    espClient.setCACert(awsRootCA);
    espClient.setCertificate(clientCert);
    espClient.setPrivateKey(privateKey);

    mqttClient.setServer(awsEndpoint, 8883);
    
    while (!mqttClient.connected()) {
        Serial.print("Connecting to AWS IoT...");
        if (mqttClient.connect("ESP32Client")) {
            Serial.println("Connected!");
        } else {
            Serial.print("Failed, retrying...");
            delay(2000);
        }
    }
}

// Function to publish message
void publishMessage(String message) {
    if (mqttClient.connected()) {
        mqttClient.publish(mqttTopic, message.c_str());
        Serial.println("Message sent: " + message);
    } else {
        Serial.println("MQTT not connected. Trying to reconnect...");
        connectAWSIoT();
    }
}

void setup() {
    Serial.begin(115200);
    connectWiFi();
    connectAWSIoT();
}

void loop() {
    if (Serial.available()) {
        String inputMessage = Serial.readStringUntil('\n');  // Read input from Serial Monitor
        inputMessage.trim();
        if (inputMessage.length() > 0) {
            publishMessage(inputMessage);
        }
    }
    mqttClient.loop();
}
