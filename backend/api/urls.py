from django.urls import path
from .views import PassengerRechargesView, PassengerTransactionsView, TransactionListView, CreateRouteView, RechargeCardView, CreateCardView, PassengerAndCardDetailsView, CreatePassengerView, CreateStationView, PassengerSignupView, StationSignupView, AdminSignupView, UserLoginView, GetcarddetailsView

urlpatterns = [
    path('passengers/new/', CreatePassengerView.as_view()),
    path('stations/new/', CreateStationView.as_view()),
    path('signup/passenger/', PassengerSignupView.as_view(), name='passenger_signup'),
    path('signup/station/', StationSignupView.as_view(), name='station_signup'),
    path('signup/admin/', AdminSignupView.as_view(), name='admin_signup'),
    path('login/', UserLoginView.as_view(), name='login'),
    path("card/read/", GetcarddetailsView.as_view(), name='card_read'),
    path("passengers/<str:nic_number>/", PassengerAndCardDetailsView.as_view(), name="get_passenger_and_card_details"),
    path("card/create/", CreateCardView.as_view(), name='create-card'),
    path("card/recharge/", RechargeCardView.as_view(), name='update-card'),
    path("route/create/", CreateRouteView.as_view(), name='create-route'),
    path("transactions/", TransactionListView.as_view(), name='transaction-list'),
    path('passenger/transactions/', PassengerTransactionsView.as_view(), name='passenger-transactions'),
    path("recharges/", PassengerRechargesView.as_view(), name="passenger-recharges"),
]