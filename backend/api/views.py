from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import generics

from .models import Passenger, Station
from .serializer import PassengerSignupSerializer, StationSignupSerializer, AdminSignupSerializer, UserLoginSerializer, PassengerSerializer, StationSerializer

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
