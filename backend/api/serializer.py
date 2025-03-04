from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Passenger, Station, Card, Transaction, Recharge, TransportFees

User = get_user_model()  # Get the custom User model

class PassengerSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Passenger
        fields = ["email", "password", "nic_number", "first_name", "last_name", "dob", "address", "phone"]

    def create(self, validated_data):
        email = validated_data.pop("email")
        password = validated_data.pop("password")

        # ✅ Ensure a user with this email doesn't already exist
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})

        # ✅ Create the User instance correctly
        user = User.objects.create_user(username=email, email=email, user_type="passenger")
        user.set_password(password)
        user.save()

        # ✅ Explicitly pass the User instance when creating Passenger
        passenger = Passenger.objects.create(user=user, email=email, **validated_data)
        return passenger


class StationSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Station
        fields = ['station_ID', 'station_name', 'email', 'phone', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create(username=validated_data['email'], email=validated_data['email'], user_type='station')
        user.set_password(password)
        user.save()
        station = Station.objects.create(user=user, **validated_data)
        return user

class AdminSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create(username=validated_data['username'], email=validated_data['email'], user_type='admin', is_staff=True, is_superuser=True,)
        user.set_password(validated_data['password'])
        user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = '__all__'


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = '__all__'


class CardSerializer(serializers.ModelSerializer):
    # We will validate the nic_number and issued_station fields here
    nic_number = serializers.CharField(max_length=20)
    issued_station = serializers.CharField(max_length=20)

    class Meta:
        model = Card
        fields = ['card_num', 'nic_number', 'balance', 'card_type', 'issued_date', 'issued_station']

    def validate_nic_number(self, value):
        # Check if the nic_number exists in the Passenger model
        try:
            passenger = Passenger.objects.get(nic_number=value)
        except Passenger.DoesNotExist:
            raise serializers.ValidationError("The NIC number does not exist.")
        return passenger

    def validate_issued_station(self, value):
        try:
            station = Station.objects.get(station_ID=value)
        except Station.DoesNotExist:
            raise serializers.ValidationError("The Station ID does not exist.")
        return station


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'


class RechargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recharge
        fields = '__all__'


class TransportFeesSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransportFees
        fields = '__all__'
