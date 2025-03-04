from django.apps import AppConfig
import threading
from .mqtt_client import start_mqtt_client

class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    def ready(self):
        # Run the MQTT client in a background thread when the app is ready
        thread = threading.Thread(target=start_mqtt_client)
        thread.daemon = True  # This allows the thread to exit when the main program exits
        thread.start()
        print("MQTT client started")
