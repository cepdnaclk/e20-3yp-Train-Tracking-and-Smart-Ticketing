import paho.mqtt.client as mqtt
from django.conf import settings

# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to AWS IoT Core!")
        client.subscribe(settings.MQTT_TOPIC_SUB)  # Subscribe to the topic
    else:
        print(f"Failed to connect, return code {rc}")

# Callback when a message is received
def on_message(client, userdata, msg):
    print(f"Received message: {msg.payload.decode()} on topic {msg.topic}")
    # backend ekata ena message eka methana process karanna puluwan
    # e.g., save to database, send to another service, etc.

# Initialize MQTT client
def start_mqtt_client():
    client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    # Configure TLS/SSL
    client.tls_set(
        ca_certs=settings.MQTT_CA_PATH,
        certfile=settings.MQTT_CERT_PATH,
        keyfile=settings.MQTT_KEY_PATH,
    )

    # Connect to the broker
    client.connect(settings.MQTT_BROKER_URL, settings.MQTT_BROKER_PORT)
    client.subscribe(settings.MQTT_TOPIC_SUB) # Subscribe to the pub of esp32

    # Start the loop to process network traffic and dispatch callbacks
    client.loop_start()
    return client