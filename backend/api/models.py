from django.db import models

class Passenger(models.Model):
    nic_number = models.IntegerField().primary_key
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    dob = models.DateField()
