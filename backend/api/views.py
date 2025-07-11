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
from .helper import process_task_id_3
from .mqtt_client import start_mqtt_client
from django.utils.timezone import now
from .models import Passenger, Station, Card, TransportFees, Transaction, Recharge, Routes, Trains
from .serializer import RouteSerializer, TrainSerializer, RechargeSerializer, TransactionSerializer, TransportFeesSerializer, PassengerSignupSerializer, StationSignupSerializer, AdminSignupSerializer, UserLoginSerializer, PassengerSerializer, StationSerializer, CardSerializer
import paho.mqtt.client as mqtt
import ssl
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
mqtt_client = start_mqtt_client()

# Setup Neo4j driver
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

User = get_user_model()


def sort_by_departure_time(routes):
    return sorted(
        routes,
        key=lambda x: datetime.strptime(x["departure_time_from_start"], "%H:%M").time()
    )

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
            return Response({"message": "Admin registered successfully CICD IS WORKING"}, status=status.HTTP_201_CREATED)
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
                        "card_id" : card.card_num,
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
    

class FindRoute(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        start_station = request.data.get('from')
        end_station = request.data.get('to')

        if not start_station or not end_station:
            return Response(
                {"error": "Both 'from' and 'to' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        query = """
        MATCH 
          (start:Station {name: $start_station})-[startRel:SERVES_ROUTE]->(),
          (end:Station {name: $end_station})<-[endRel:SERVES_ROUTE]-()
        WHERE startRel.route_id = endRel.route_id 
          AND toInteger(startRel.sequence) < toInteger(endRel.sequence)
        RETURN 
          startRel.route_id AS route_id,
          startRel.departure_time AS departure_time_from_start,
          endRel.arrival_time AS arrival_time_at_end
        ORDER BY startRel.departure_time
        """

        try:
            with driver.session() as session:
                result = session.run(query, start_station=start_station, end_station=end_station)
                neo4j_data = [record.data() for record in result]

            # Replace route_id with train_name using Django ORM
            response_data = []
            for entry in neo4j_data:
                route_id = entry["route_id"]
                try:
                    train = Trains.objects.get(route=route_id)
                    entry["train_name"] = train.train_name
                    del entry["route_id"]
                except Trains.DoesNotExist:
                    entry["train_name"] = "Unknown Train"

                response_data.append(entry)
                
            

            return Response(sort_by_departure_time(response_data), status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class CreateRouteView(generics.CreateAPIView):
    queryset = Routes.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [AllowAny]


class CreateTrainView(generics.CreateAPIView):
    queryset = Trains.objects.all()
    serializer_class = TrainSerializer
    permission_classes = [AllowAny]

class StationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stations = Station.objects.all().values('station_ID', 'station_name')
        return Response(stations)
    

class TrainRouteDetailsView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        train_name = request.data.get("train_name")
        if not train_name:
            return Response({"error": "train_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            train = Trains.objects.get(train_name=train_name)
        except Trains.DoesNotExist:
            return Response({"error": "Train not found"}, status=status.HTTP_404_NOT_FOUND)

        route_id = train.route

        # Query Neo4j for route stations with coordinates and IDs
        neo_query = """
            MATCH (s:Station)-[r:SERVES_ROUTE {route_id: $route_id}]->(next:Station)
            RETURN 
            s.station_id AS station_id,
            s.name AS station_name,
            s.latitude AS lat,
            s.longitude AS lon,
            toInteger(r.sequence) AS sequence
            UNION
            MATCH (s:Station)<-[r:SERVES_ROUTE {route_id: $route_id}]-(prev)
            WHERE NOT (s)-[:SERVES_ROUTE {route_id: $route_id}]->()
            RETURN 
            s.station_id AS station_id,
            s.name AS station_name,
            s.latitude AS lat,
            s.longitude AS lon,
            toInteger(r.sequence) AS sequence
            ORDER BY sequence
        """

        with driver.session() as session:
            result = session.run(neo_query, route_id=route_id)
            station_data = [record.data() for record in result]

        if not station_data:
            return Response({"error": "No stations found for this route"}, status=status.HTTP_404_NOT_FOUND)

        first_station = station_data[0]
        matched_station = None
        for station in station_data:
            if int(station["station_id"]) == int(train.last_station):
                matched_station = station
                break
        response_data = {
            "route_id": route_id,
            "train_location": train.location,
            "stations": station_data,
            "starting_station": first_station,
            "last_station": matched_station,
        }

        return Response(response_data, status=status.HTTP_200_OK)
    

class TrainLocationListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        trains = Trains.objects.all()
        data = [
            {
                "train_name": train.train_name,
                "location": train.location
            }
            for train in trains
        ]
        return Response(data, status=status.HTTP_200_OK)
    

class ReceiveGPSView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        latitude = request.data.get("latitude")
        longitude = request.data.get("longitude")
        
        if latitude and longitude:
            print(f"Received GPS: lat={latitude}, lon={longitude}")
            return Response({"message": "GPS received"}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)
    
class ReceiveLocationView(APIView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            name = data.get('name')
            lat = data.get('lat')
            lon = data.get('lon')

            print(f"[Location Received] Name: {name}, Latitude: {lat}, Longitude: {lon}")

            return JsonResponse({"status": "success", "message": "Location received."}, status=200)
        except Exception as e:
            print(f"[Error] {e}")
            return JsonResponse({"status": "error", "message": str(e)}, status=400)