from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from datetime import datetime
from rest_framework import generics
from django.conf import settings
import json
from .helper import process_task_id_3
from .models import Passenger, Station, Card, TransportFees, Transaction, Recharge
from .serializer import RechargeSerializer, TransactionSerializer, TransportFeesSerializer, PassengerSignupSerializer, StationSignupSerializer, AdminSignupSerializer, UserLoginSerializer, PassengerSerializer, StationSerializer, CardSerializer
from .mqtt_client import start_mqtt_client

User = get_user_model()

# ---- SIGNUP VIEWS ----
class PassengerSignupView(APIView):
    permission_classes = [AllowAny]


    def post(self, request):
        print("Passenger signup")
        print(request.data)
        serializer = PassengerSignupSerializer(data=request.data)
        if serializer.is_valid():
            station_id = str(request.data.get("station_ID"))
            station_topics = getattr(settings, "STATION_MQTT_TOPICS", {})
            topic = station_topics.get(station_id)
            print("topic: ",topic)
            passenger = serializer.save()
            #topic = "esp32/rfid_sub"
            if topic:
                payload = {
                        "task_id": 1,
                        "nic_number": passenger.nic_number,
                        "station_id": passenger.station_id,
                    }
                '''print(f"Publishing to topic: {topic}")
                print(f"Payload: {json.dumps(payload)}")
                result = mqtt_client.publish(topic, json.dumps(payload),qos=1)
                print(f"Publish result: {result.rc}")  # 0 means success'''
            else:
                print(f"No topic found for station ID: {station_id}")
            return Response({"message": "Passenger registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StationSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StationSignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Station registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AdminSignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Admin registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ---- LOGIN VIEWS ----
class UserLoginView(APIView):
    permission_classes = [AllowAny]
    print("User login")

    def post(self, request):
        print(request.data)
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(username=username, password=password)

            if user:
                refresh = RefreshToken.for_user(user)
                response_data = {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                    "user_type": user.user_type
                }
                if user.user_type == 'passenger':
                    response_data["profile"] = {
                        "nic_number": user.passenger_profile.nic_number,
                        "first_name": user.passenger_profile.first_name,
                        "last_name": user.passenger_profile.last_name,
                        "dob": user.passenger_profile.dob,
                        "address": user.passenger_profile.address,
                        "email": user.passenger_profile.email,
                        "phone": user.passenger_profile.phone,
                    }
                elif user.user_type == 'station':
                    response_data["profile"] = {
                        "station_ID": user.station_profile.station_ID,
                        "station_name": user.station_profile.station_name,
                        "email": user.station_profile.email,
                        "phone": user.station_profile.phone,
                    }

                return Response(response_data)

            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Create Passenger (User)
class CreatePassengerView(generics.CreateAPIView):
    queryset = Passenger.objects.all()
    serializer_class = PassengerSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Passenger created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Create Station
class CreateStationView(generics.CreateAPIView):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Station created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class GetcarddetailsView(APIView):
    def post(self, request):
        task_ID = request.data.get('task_id')

        if task_ID == 3:
            result = process_task_id_3(request.data)
            if "error" in result:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
            return Response(result, status=status.HTTP_200_OK)

        return Response({"error": "Invalid task_id"}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        return Response({"error": "send post"}, status=status.HTTP_201_CREATED)
        
class PassengerAndCardDetailsView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, nic_number, *args, **kwargs):
        passenger = get_object_or_404(Passenger, nic_number=nic_number)

        # Get card details
        cards = Card.objects.filter(nic_number=passenger)

        # Convert passenger details to JSON
        passenger_data = {
            "nic_number": passenger.nic_number,
            "first_name": passenger.first_name,
            "last_name": passenger.last_name,
            "dob": passenger.dob.strftime("%Y-%m-%d"),
            "address": passenger.address,
            "email": passenger.email,
            "phone": passenger.phone,
        }

        # Convert card details to JSON
        card_data = [
            {
                "card_num": card.card_num,
                "balance": card.balance,
                "card_type": card.card_type,
                "issued_date": card.issued_date.strftime("%Y-%m-%d"),
                "issued_station": card.issued_station.station_name,  # Assuming Station model has a 'name' field
            }
            for card in cards
        ]

        # Combine both responses
        response_data = {
            "passenger": passenger_data,
            "cards": card_data,
        }

        return Response(response_data, status=200)


class CreateCardView(generics.CreateAPIView):
    queryset = Card.objects.all()
    serializer_class = CardSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            card = serializer.save()
            station_id = card.issued_station.station_ID
            station_topics = getattr(settings, "STATION_MQTT_TOPICS", {})
            topic = station_topics.get(station_id)
            print("topic: ",topic)
            
            if topic:
                payload = {
                        "task_id": 1,
                        "nic": card.nic_number.nic_number,
                        "amount": card.balance,
                    }
                print(f"Publishing to topic: {topic}")
                print(f"Payload: {json.dumps(payload)}")
                result = mqtt_client.publish(topic, json.dumps(payload),qos=1)
                print(f"Publish result: {result.rc}")  # 0 means success
            else:
                print(f"No topic found for station ID: {station_id}")
            return Response({"message": "Card created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)

        # If validation fails, return the error details
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class RechargeCardView(APIView):
    permission_classes = [AllowAny]
    def patch(self, request, *args, **kwargs):
        nic_number = request.data.get("nic_number")
        new_balance = request.data.get("balance")
        station_id = request.data.get("station_ID")
        if not nic_number or new_balance is None:
            return Response({"error": "Card number and balance are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            passenger = Passenger.objects.get(nic_number=nic_number)
            card = Card.objects.get(nic_number_id=passenger.pk)
            old_balance = card.balance
            old_balance = old_balance + new_balance
            card.balance = old_balance
            card.save()
            station = Station.objects.get(station_ID=str(station_id))
            Recharge.objects.create(
                card_num=card,
                amount=new_balance,
                station=station
            )
            topic = f"esp32/stationsub/{station_id}"
            print("topic: ",topic)
            
            if topic:
                payload = {
                        "task_id": 1,
                        "nic": card.nic_number.nic_number,
                        "amount": card.balance,
                    }
                print(f"Publishing to topic: {topic}")
                print(f"Payload: {json.dumps(payload)}")
                result = mqtt_client.publish(topic, json.dumps(payload),qos=1)
                print(f"Publish result: {result.rc}")  # 0 means success
            else:
                print(f"No topic found for station ID: {station_id}")
            return Response({"message": "Balance updated successfully", "balance": card.balance}, status=status.HTTP_200_OK)
        except Card.DoesNotExist:
            return Response({"error": "Card not found"}, status=status.HTTP_404_NOT_FOUND)
        

class CreateRouteView(generics.CreateAPIView):
    queryset = TransportFees.objects.all()
    serializer_class = TransportFeesSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Route added successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class TransactionListView(APIView):
    def get(self, request):
        date = request.GET.get('date')
        station_id = request.GET.get('station_id')
        if not date or not station_id:
            return Response({"error": "Date and station_id are required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            formatted_date = datetime.strptime(date, "%Y-%m-%d").date()
            # Filter transactions for the specific date and station_id
            departing_transactions = Transaction.objects.filter(date__date=formatted_date, S_station=station_id)
            arriving_transactions = Transaction.objects.filter(date__date=formatted_date, E_station=station_id)
            # Serialize the transactions
            departing_data = [
                {
                    "card_num": transaction.card_num.card_num,
                    "start_station": transaction.S_station,
                    "end_station": transaction.E_station,
                    "date": transaction.date,
                    "amount": transaction.amount
                }
                for transaction in departing_transactions
            ]

            arriving_data = [
                {
                    "card_num": transaction.card_num.card_num,
                    "start_station": transaction.S_station,
                    "end_station": transaction.E_station,
                    "date": transaction.date,
                    "amount": transaction.amount
                }
                for transaction in arriving_transactions
            ]

            return Response({
                "departing": departing_data,
                "arriving": arriving_data
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response({"error": "Invalid date format, use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)


class PassengerTransactionsView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        passenger_id = request.GET.get('passenger_id')
        if not passenger_id:
            return Response({"error": "Passenger ID is required"}, status=400)
        try:
            passenger = get_object_or_404(Passenger, nic_number=passenger_id)
            card = get_object_or_404(Card, nic_number=passenger)
            transactions = Transaction.objects.filter(card_num=card)
            serializer = TransactionSerializer(transactions, many=True)
            return Response(serializer.data, status=200)
        except Passenger.DoesNotExist:
            return Response({"error": "Passenger not found"}, status=404)
        except Card.DoesNotExist:
            return Response({"error": "No card associated with this passenger"}, status=404)
        

class PassengerRechargesView(APIView):
    def get(self, request, *args, **kwargs):
        nic_number = request.query_params.get("passenger_id")  # Getting NIC number from query params
        if not nic_number:
            return Response({"error": "NIC number is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            passenger = Passenger.objects.get(nic_number=nic_number)
            card = Card.objects.get(nic_number=passenger)
            recharges = Recharge.objects.filter(card_num=card)
            serializer = RechargeSerializer(recharges, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Passenger.DoesNotExist:
            return Response({"error": "Passenger not found"}, status=status.HTTP_404_NOT_FOUND)
        except Card.DoesNotExist:
            return Response({"error": "No card found for this passenger"}, status=status.HTTP_404_NOT_FOUND)
        
## mqtt-iot-core-intergration

# Start the MQTT client
mqtt_client = start_mqtt_client()

'''import logging
logging.basicConfig(level=logging.DEBUG)
mqtt_client.enable_logger()'''

class PublishMessageView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            message = request.data
            station_id = str(message.get("station_id"))
            station_topics = getattr(settings, "STATION_MQTT_TOPICS", {})
            topic = station_topics.get(station_id)
            if not topic:
                return JsonResponse({"error": "Invalid or missing station_id"}, status=400)
            payload_json = json.dumps(message)
            mqtt_client.publish(topic, payload_json)
            return JsonResponse({"status": "Message published", "topic": topic, "payload": message}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
