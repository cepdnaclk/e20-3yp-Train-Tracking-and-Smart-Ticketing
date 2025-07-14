import paho.mqtt.client as mqtt
from django.conf import settings
import threading
import uuid
import ssl
import json
from .helper import process_task_id_3
from .location_cache import set_latest_location


mqtt_client = None
client_lock = threading.Lock()

import requests

def send_to_backend(data):
    try:
        #url = 'https://raillynk.site/api/mqtt-data/'
        url = 'http://127.0.0.1:8000/api/mqtt-data/' # for local testing, use 'http://localhost:8000/api/mqtt-data/'
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, json=data, timeout=5)
        if response.status_code == 200:
            print("✅ Successfully sent data to backend")
        else:
            print(f"❌ Failed to send data: {response.status_code} {response.text}")
    except Exception as e:
        print(f"[HTTP POST Error] {e}")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to AWS IoT Core!")
        for topic in settings.MQTT_SUBSCRIBE_TOPICS:
            client.subscribe(topic, qos=1)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode()
        print(f"📥 Message: {payload_str} on topic {msg.topic}")
        payload = json.loads(payload_str)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"[MQTT Error] Invalid payload: {e}")
        return

    # Immediately send the full payload to backend via HTTP POST
    send_to_backend(payload)

def on_disconnect(client, userdata, rc):
    print(f"Disconnected from AWS IoT Core with result code: {rc}")
    start_mqtt_client()  # Attempt to reconnect

def start_mqtt_client():
    global mqtt_client
    with client_lock:
        if mqtt_client is None:
            client_id = f"DjangoBackend-{uuid.uuid4()}"
            mqtt_client = mqtt.Client(client_id=client_id, clean_session=True)
            mqtt_client.on_connect = on_connect
            mqtt_client.on_message = on_message
            mqtt_client.on_disconnect = on_disconnect

            mqtt_client.tls_set(
                ca_certs=settings.MQTT_CA_PATH,
                certfile=settings.MQTT_CERT_PATH,
                keyfile=settings.MQTT_KEY_PATH,
            )

            mqtt_client.connect(settings.MQTT_BROKER_URL, settings.MQTT_BROKER_PORT)
    mqtt_client.loop_forever()

def publish_message(data,topic):
    payload = json.dumps(data)
    mqtt_client.publish(topic, payload)
    print(f"📤 Published to {topic}: {payload}")