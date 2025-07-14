import os
from django.apps import AppConfig
import threading


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    "test manuja"
    #def ready(self):
    #    from .mqtt_client import start_mqtt_client
    #    start_mqtt_client()