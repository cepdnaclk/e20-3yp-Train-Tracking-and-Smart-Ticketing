import os
from django.apps import AppConfig
import threading
from .mqtt_client import start_mqtt_client

class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    mqtt_client_started = False

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':  # Prevents double execution
            if not ApiConfig.mqtt_client_started:
                thread = threading.Thread(target=start_mqtt_client)
                thread.daemon = True
                thread.start()
                ApiConfig.mqtt_client_started = True
                print("MQTT client started")
