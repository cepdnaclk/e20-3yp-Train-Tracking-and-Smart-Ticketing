from django.urls import path
from .views import CreatePassengerView, CreateStationView, PassengerSignupView, StationSignupView, AdminSignupView, UserLoginView

urlpatterns = [
    path('passengers/new/', CreatePassengerView.as_view()),
    path('stations/new/', CreateStationView.as_view()),
    path('signup/passenger/', PassengerSignupView.as_view(), name='passenger_signup'),
    path('signup/station/', StationSignupView.as_view(), name='station_signup'),
    path('signup/admin/', AdminSignupView.as_view(), name='admin_signup'),
    path('login/', UserLoginView.as_view(), name='login'),
]