from django.urls import path
from .views import RouteStateView, ReceiveLocationView, ReceiveGPSView, TrainLocationListView, TrainRouteDetailsView, CreateTrainView, StationListView, CreateRouteView, FindRoute, AdminDailyReportView, PassengerRechargesView, PassengerTransactionsView, TransactionListView, CreateRouteView, RechargeCardView, CreateCardView, PassengerAndCardDetailsView, CreatePassengerView, CreateStationView, PassengerSignupView, StationSignupView, AdminSignupView, UserLoginView,MqttDataView,PassengerListView,DeletePassengerView,UpdatePassengerProfileView,CustomPasswordResetView,CardCountTodayView,PassengerFlowStatsView
from django.contrib.auth import views as auth_view

urlpatterns = [
    path('passengers/new/', CreatePassengerView.as_view()),
    path('stations/new/', CreateStationView.as_view()),
    path('signup/passenger/', PassengerSignupView.as_view(), name='passenger_signup'),
    path('signup/station/', StationSignupView.as_view(), name='station_signup'),
    path('signup/admin/', AdminSignupView.as_view(), name='admin_signup'),
    path('login/', UserLoginView.as_view(), name='login'),
    #path("card/read/", GetcarddetailsView.as_view(), name='card_read'),
    path("passengers/<str:nic_number>/", PassengerAndCardDetailsView.as_view(), name="get_passenger_and_card_details"),
    path("card/create/", CreateCardView.as_view(), name='create-card'),
    path("card/recharge/", RechargeCardView.as_view(), name='update-card'),
    path("route/create/", CreateRouteView.as_view(), name='create-route'),
    path("transactions/", TransactionListView.as_view(), name='transaction-list'),
    path('passenger/transactions/', PassengerTransactionsView.as_view(), name='passenger-transactions'),
    path("recharges/", PassengerRechargesView.as_view(), name="passenger-recharges"),
    #path('publish-message/', PublishMessageView.as_view(), name='publish_message'),
    path("admin/dashboard-stats", AdminDailyReportView.as_view(), name="admin-daily-report"),
    path("paths/route/", FindRoute.as_view(), name="find_route_between_stations"),
    path("create/routes/", CreateRouteView.as_view(), name="create_new_routes"),
    path("station/list/", StationListView.as_view(), name="give_all_stations"),
    path("create/train/", CreateTrainView.as_view(), name="create_train"),
    path("find/train/details/", TrainRouteDetailsView.as_view(), name="find_train_locations"),
    path("trains/locations/", TrainLocationListView.as_view(), name="find_all_trains"),
    path("get/gps/location/", ReceiveGPSView.as_view(), name="get_gps_locations"),
    path("loc/", ReceiveLocationView.as_view(), name="location"),
    path("mqtt-data/", MqttDataView.as_view(), name="mqtt_data"),
    path("route/update/", RouteStateView.as_view(), name="update_routeVStrains"),
    path('passengers/', PassengerListView.as_view(), name='passenger-list'),
    path('passengers/delete/<int:pk>/', DeletePassengerView, name='delete-passenger'),
    path('passenger/update/',UpdatePassengerProfileView.as_view(),name = 'update-profile'),
    path('reset_password/', CustomPasswordResetView.as_view(), name='reset_password'),
    path('reset_password_sent/', auth_view.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/',auth_view.PasswordResetConfirmView.as_view(template_name = "registration/password_reset_confirm.html"),name='password_reset_confirm'),
    path('reset_password_complete/', auth_view.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('station/<str:station_id>/cards-today/', CardCountTodayView.as_view(), name='cards-today-count'),
    path('station/<str:station_id>/flow-stats/', PassengerFlowStatsView.as_view(), name='station-flow-stats'),


]