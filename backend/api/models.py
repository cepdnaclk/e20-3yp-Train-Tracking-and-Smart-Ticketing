from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('passenger', 'Passenger'),
        ('station', 'Station'),
        ('admin', 'Admin'),
        ('driver', 'Driver'),
    )

    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES)

    groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)

    def __str__(self):
        return self.username

class Passenger(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="passenger_profile")
    nic_number = models.CharField(unique=True, max_length=20)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    dob = models.DateField()
    address = models.CharField(max_length=200)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15)


class Station(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="station_profile")
    station_ID = models.CharField(unique=True, max_length=20)
    station_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15)


class Card(models.Model):
    card_num = models.CharField(unique=True, default="0101", max_length=10)
    nic_number = models.OneToOneField(Passenger, on_delete=models.CASCADE, related_name="card", unique=True)
    balance = models.IntegerField(null=False, default=0)
    card_type = models.CharField(max_length=100, null=False, default="normal")
    issued_date = models.DateField()
    issued_station = models.ForeignKey(Station, on_delete=models.CASCADE)


class Transaction(models.Model):
    card_num = models.ForeignKey(Card, on_delete=models.CASCADE)
    S_station = models.CharField(max_length=100, null=True)
    E_station = models.CharField(max_length=100, null=True)
    date = models.DateTimeField(auto_now_add=True)
    amount = models.FloatField()


class Recharge(models.Model):
    card_num = models.ForeignKey(Card, on_delete=models.CASCADE)
    amount = models.FloatField()
    date = models.DateTimeField(auto_now_add=True)
    station = models.ForeignKey(Station, on_delete=models.CASCADE)


class TransportFees(models.Model):
    route = models.CharField(max_length=100, unique=True, null=True)
    amount = models.FloatField()


class Routes(models.Model):
    route_id = models.CharField(max_length=10)
    state = models.BooleanField()
    station_list = models.JSONField()


class Trains(models.Model):
    location = models.CharField(max_length=100)
    train_name = models.CharField(max_length=200)
    last_station = models.CharField(max_length=10)
    route = models.ForeignKey(Routes, on_delete=models.CASCADE, null=True)






