import paho.mqtt.client as mqtt
import ssl
import time
import threading

# Define your AWS IoT Core endpoint, topic, and paths to certificates
AWS_IOT_ENDPOINT = 'a2v3g8yh48u9ya-ats.iot.ap-south-1.amazonaws.com'  # Replace with your IoT endpoint
MQTT_TOPIC = 'esp32/abcd'  # Replace with your topic
CA_PATH = './certs/AWS_CERT_CA.pem'  # Path to the root CA certificate
CERT_PATH = './certs/device-cert.pem'  # Path to your device certificate
KEY_PATH = './certs/device-private-key.pem'  # Path to your device private key

# Function to handle connection to the MQTT broker
def on_connect(client, userdata, flags, rc):
    print(f'Connected with result code {rc}')
    if rc == 0:
        print(f'Subscribing to topic: {MQTT_TOPIC}')
        client.subscribe(MQTT_TOPIC)
    else:
        print(f'Failed to connect, return code {rc}')

# Function to handle receiving messages
def on_message(client, userdata, msg):
    print(f'Received message on {msg.topic}: {msg.payload.decode()}')

# Function to publish messages with 3-second intervals
def publish_messages(client):
    while True:
        message = "Hello from Django! This is a periodic message."
        client.publish(MQTT_TOPIC, payload=message, qos=1)
        print(f"Published message: {message}")
        time.sleep(5)  # Wait for 3 seconds before publishing again

# Function that sets up the MQTT client
def start_mqtt_client():
    print('Starting MQTT client...')
    # Create MQTT client instance
    client = mqtt.Client()

    # Set up the certificates for secure connection
    client.tls_set(CA_PATH, certfile=CERT_PATH, keyfile=KEY_PATH)
    client.tls_insecure_set(True)  # Set to False if you want to verify server certificates

    # Assign the callback functions for connect and message
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to the AWS IoT Core MQTT broker (replace with your broker URL)
    client.connect(AWS_IOT_ENDPOINT, port=8883, keepalive=60)

    # Start the loop to listen for incoming messages in a background thread
    client.loop_start()

    # Start the publishing thread to send messages every 3 seconds
    publishing_thread = threading.Thread(target=publish_messages, args=(client,))
    publishing_thread.daemon = True  # This will allow the thread to exit when the main program exits
    publishing_thread.start()

    # Keep the main thread running so the publishing thread continues to publish messages
    try:
        while True:
            time.sleep(1)  # Main thread does nothing, just waits
    except KeyboardInterrupt:
        print("Server stopped.")

