from django.db import models

class Passenger(models.Model):
    nic_number = models.IntegerField().primary_key
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    dob = models.DateField()
    address = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)


class Station(models.Model):
    station_ID = models.IntegerField().primary_key
    station_name  = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)


class Card(models.Model):
    card_num = models.IntegerField().primary_key
    nic_number = models.ForeignKey(Passenger, on_delete=models.CASCADE)
    card_type = models.CharField(max_length=100, null=False, default="normal")
    issued_date = models.DateField()
    issued_station = models.ForeignKey(Station, on_delete=models.CASCADE)


class Transaction(models.Model):
    Transaction_ID = models.IntegerField().primary_key
    card_num = models.ForeignKey(Card, on_delete=models.CASCADE)
    S_station = models.CharField(max_length=100)
    E_station = models.CharField(max_length=100)
    date = models.DateTimeField()
    amount = models.FloatField()


class Recharge(models.Model):
    Recharge_ID = models.IntegerField().primary_key
    card_num = models.ForeignKey(Card, on_delete=models.CASCADE)
    amount = models.FloatField()
    date = models.DateTimeField()
    station = models.ForeignKey(Station, on_delete=models.CASCADE)


class TransportFees(models.Model):
    Price_ID = models.IntegerField().primary_key
    station_1 = models.CharField(max_length=100)
    station_2 = models.CharField(max_length=100)
    amount = models.FloatField()



