from django.contrib import admin
from .models import User, Passenger, Station, Card, Transaction, Recharge, TransportFees

# Register your models here.
admin.site.register(User)
admin.site.register(Passenger)
admin.site.register(Station)
admin.site.register(Card)
admin.site.register(Transaction)
admin.site.register(Recharge)
admin.site.register(TransportFees)