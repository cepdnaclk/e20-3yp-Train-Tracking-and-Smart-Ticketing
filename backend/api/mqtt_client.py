# mqtt_client.py
import paho.mqtt.client as mqtt
from django.conf import settings
import threading
import uuid
import ssl
import json
from .helper import process_task_id_3

published = False
mqtt_client = None
client_lock = threading.Lock()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to AWS IoT Core!")
        for topic in settings.MQTT_SUBSCRIBE_TOPICS:
            client.subscribe(topic, qos=1)
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    print(f"Received message: {msg.payload.decode()} on topic {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        task_ID = payload.get("task_id")

        if task_ID == 4:
            print("gps info received", payload)

        #card recharge task
        elif task_ID == 3:
            result = process_task_id_3(payload)
            print("[MQTT Response]", result)
    except Exception as e:
        print("[MQTT Error]", str(e))

def on_disconnect(client, userdata, rc):
    print(f"Disconnected from AWS IoT Core with result code: {rc}")

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
            mqtt_client.loop_start()
    return mqtt_client

