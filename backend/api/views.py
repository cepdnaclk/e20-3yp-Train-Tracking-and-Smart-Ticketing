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
from django.db.models import Sum, Count
import json
from django.utils.timezone import now
from .models import Passenger, Station, Card, TransportFees, Transaction, Recharge
from .serializer import RechargeSerializer, TransactionSerializer, TransportFeesSerializer, PassengerSignupSerializer, StationSignupSerializer, AdminSignupSerializer, UserLoginSerializer, PassengerSerializer, StationSerializer, CardSerializer
import paho.mqtt.client as mqtt
import ssl

User = get_user_model()

# ---- SIGNUP VIEWS ----
class PassengerSignupView(APIView):
    permission_classes = [AllowAny]


    def post(self, request):
        print(request.data)
        serializer = PassengerSignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
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
    

class PublishMessageView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        topic = settings.MQTT_TOPIC_PUB  # Use the topic from settings
        #message = request.data.get("message")
        res = {"message": "pakaya"}
        try:
            mqtt_client.publish(topic, json.dumps(res))  # Convert to JSON string
            return JsonResponse({"status": "Message published", "message": res}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        

class GetcarddetailsView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        print(request.data)
        task_ID  = request.data.get('task_id')


        if task_ID == 1:
            card_num = request.data.get('uid')
            try:
                card = Card.objects.get(card_num=card_num)
                response_data = {
                    "nic": card.nic_number.nic_number,
                    "amount": card.balance
                }
                return Response(response_data, status=status.HTTP_200_OK)
            except Card.DoesNotExist:
                return Response({"error": "Card not found"}, status=status.HTTP_404_NOT_FOUND)
            

        elif task_ID == 2:
            nic = request.data.get('nic')
            if not nic:
                return Response({"error": "Card is invalid_0"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                passenger = Passenger.objects.get(nic_number=nic)
                card = Card.objects.get(nic_number=passenger)
                return Response({"message": "Card is valid",}, status=status.HTTP_200_OK)
            except Passenger.DoesNotExist:
                return Response({"error": "Card is invalid_1"}, status=status.HTTP_404_NOT_FOUND)
            except Card.DoesNotExist:
                return Response({"error": "Card is invalid_2"}, status=status.HTTP_404_NOT_FOUND)
        

        elif task_ID == 3:
            nic = request.data.get('nic')
            start = request.data.get('station_id')
            end = request.data.get('this_station')
            amount = request.data.get('amount')
            try:
                min_station = min(int(start), int(end))
                max_station = max(int(start), int(end))
                route = str(min_station) + "-" + str(max_station)
                try:
                    price = TransportFees.objects.get(route=route).amount
                    new_amount = int(amount - price)
                    passenger = Passenger.objects.get(nic_number=nic)
                    card = Card.objects.get(nic_number=passenger)
                    card.balance = new_amount
                    card.save()
                except TransportFees.DoesNotExist:
                    return Response({"error": "Route not found"}, status=status.HTTP_404_NOT_FOUND)
                passenger = Passenger.objects.get(nic_number=nic)
                card = Card.objects.get(nic_number=passenger)
                transaction = Transaction.objects.create(
                    card_num=card,
                    S_station=start,
                    E_station=end,
                    amount=price
                )
                transaction.save()
                return Response({"new_amount": new_amount}, status=status.HTTP_200_OK)
            except Passenger.DoesNotExist:
                return Response({"error": "Passenger with this NIC does not exist"}, status=status.HTTP_404_NOT_FOUND)
            except Card.DoesNotExist:
                return Response({"error": "No card found for this NIC"}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


    
    def get(self, request):
        return Response({"error" : "pa####d get ewanne post ewapan"}, status=status.HTTP_201_CREATED)
        
        
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

    def publish_to_mqtt(self, topic, payload):
        client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)
        client.tls_set(
            ca_certs=settings.MQTT_CA_PATH,
            certfile=settings.MQTT_CERT_PATH,
            keyfile=settings.MQTT_KEY_PATH,
            tls_version=ssl.PROTOCOL_TLSv1_2,
        )
        client.connect(settings.MQTT_BROKER_URL, settings.MQTT_BROKER_PORT)
        client.loop_start()
        result = client.publish(topic, json.dumps(payload))
        client.loop_stop()
        client.disconnect()
        return result

    def create(self, request, *args, **kwargs):
        station_id = request.data.get("issued_station")
        #station_num = get_object_or_404(Station, id=station_id).station_ID
        #topic = settings.STATION_MQTT_TOPICS.get(str(station_id))
        topic = "esp32/rfid_sub"
        print(topic)

        if not topic:
            return Response({"error": "Invalid or missing station_id"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            card = serializer.save()

            payload = {
                "card_number": card.card_num,
                "amount": card.balance,
                "nic_number": getattr(card.nic_number, "nic_number", None)
            }
            print(payload)

            try:
                self.publish_to_mqtt(topic, payload)
            except Exception as e:
                return Response({
                    "message": "Card created, but MQTT publish failed",
                    "error": str(e),
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)

            return Response({
                "message": "Card created successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
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
            departing_data = [
                {
                    "card_num": transaction.card_num.card_num,
                    "start_station": get_object_or_404(Station, station_ID=transaction.S_station).station_name + " (" + str(transaction.S_station) + ")",
                    "end_station": get_object_or_404(Station, station_ID=transaction.E_station).station_name + " (" + str(transaction.E_station) + ")",
                    "date": transaction.date,
                    "amount": transaction.amount
                }
                for transaction in departing_transactions
            ]

            arriving_data = [
                {
                    "card_num": transaction.card_num.card_num,
                    "start_station": get_object_or_404(Station, station_ID=transaction.S_station).station_name + " (" + str(transaction.S_station) + ")",
                    "end_station": get_object_or_404(Station, station_ID=transaction.E_station).station_name + " (" + str(transaction.E_station) + ")",
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
        


class AdminDailyReportView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        today = datetime.today().date()
        total_cards_issued_today = Card.objects.filter(issued_date=today).count()
        total_passengers = Passenger.objects.count()
        daily_revenue = Transaction.objects.filter(date__date=today).aggregate(total=Sum('amount'))['total'] or 0
        start_of_month = today.replace(day=1)
        monthly_revenue = Transaction.objects.filter(date__date__gte=start_of_month).aggregate(total=Sum('amount'))['total'] or 0
        station_counts = Transaction.objects.values('S_station').annotate(count=Count('S_station'))
        total_trips = sum([x['count'] for x in station_counts])
        station_percentages = [
            {
                "station": entry['S_station'],
                "percentage": (entry['count'] / total_trips) * 100 if total_trips > 0 else 0
            } for entry in station_counts
        ]

        response_data = {
            "total_cards_issued_today": total_cards_issued_today,
            "total_passengers": total_passengers,
            "daily_revenue": daily_revenue,
            "monthly_revenue": monthly_revenue,
            "station_usage_percentages": station_percentages
        }

        return Response(response_data, status=status.HTTP_200_OK)
    

