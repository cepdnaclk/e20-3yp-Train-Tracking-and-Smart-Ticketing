from django.core.management.base import BaseCommand
from api.mqtt_client import start_mqtt_client

class Command(BaseCommand):
    help = "Run the MQTT subscriber with dynamic client ID and wildcard topics"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("📡 Running MQTT subscriber..."))
        start_mqtt_client()
