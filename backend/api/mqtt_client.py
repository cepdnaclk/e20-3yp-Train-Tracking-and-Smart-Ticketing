import paho.mqtt.client as mqtt
from django.conf import settings
import json


# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to AWS IoT Core!")
        client.subscribe(settings.MQTT_TOPIC_SUB)  # Subscribe to the topic
    else:
        print(f"Failed to connect, return code {rc}")

# Callback when a message is received
def on_message(client, userdata, msg):
    from .models import Passenger, Station, Card, TransportFees, Transaction, Recharge
    from .serializer import RechargeSerializer, TransactionSerializer, TransportFeesSerializer, PassengerSignupSerializer, StationSignupSerializer, AdminSignupSerializer, UserLoginSerializer, PassengerSerializer, StationSerializer, CardSerializer

    topic = settings.MQTT_TOPIC_PUB
    message = msg.payload.decode()
    message = json.loads(message)  
    task_ID = message["task_id"]

    # 🔹 Handle the message for task ID 1 
    if task_ID == 1:
        card_num = message["uid"]
        print(f"Received message for task ID 1: {card_num}")
        try:
            card = Card.objects.get(card_num=card_num)
            response_data = {"response": {
                "nic": card.nic_number.nic_number,
                "amount": card.balance
            }}
            print(json.dumps(response_data))
            client.publish(topic, json.dumps(response_data))  
        except Card.DoesNotExist:
            response_data = {
                "response": "invalid"
            }
            print(json.dumps(response_data))
            client.publish(topic, json.dumps(response_data)) 

    # 🔹 Handle the message for task ID 2 
    elif task_ID == 2:
        nic = message.get('nic')
        print(f"Received message for task ID 2: {nic}")
        if not nic:
            response_data = {
                "response": "Card is invalid_0"
            }
            client.publish(topic, json.dumps(response_data))
        else:
            try:
                passenger = Passenger.objects.get(nic_number=nic)
                card = Card.objects.get(nic_number=passenger)
                response_data = {
                    "response": "Card is valid"
                }
                print(json.dumps(response_data))
                client.publish(topic, json.dumps(response_data))
            except Passenger.DoesNotExist:
                response_data = {
                    "response": "Card is invalid_1"
                }
                print(json.dumps(response_data))
                client.publish(topic, json.dumps(response_data))
            except Card.DoesNotExist:
                response_data = {
                    "response": "Card is invalid_2"
                }
                print(json.dumps(response_data))
                client.publish(topic, json.dumps(response_data))

    # 🔹 Handle the message for task ID 3 
    elif task_ID == 3:
        nic = message.get('nic')
        start = message.get('station_id')
        end = message.get('this_station')
        amount = message.get('amount')

        print(f"Received message for task ID 3: NIC={nic}, Start={start}, End={end}, Amount={amount}")

        try:
            min_station = min(int(start), int(end))
            max_station = max(int(start), int(end))
            route = str(min_station) + "-" + str(max_station)

            # Fetch the price from the database
            try:
                price = TransportFees.objects.get(route=route).amount
                new_amount = int(amount) - price
                
                passenger = Passenger.objects.get(nic_number=nic)
                card = Card.objects.get(nic_number=passenger)

                # Update the card balance
                card.balance = new_amount
                card.save()

            except TransportFees.DoesNotExist:
                response_data = {
                    "response": "Route not found"
                }
                print(json.dumps(response_data))
                client.publish(topic, json.dumps(response_data))
                return

            # Save the transaction
            transaction = Transaction.objects.create(
                card_num=card,
                S_station=start,
                E_station=end,
                amount=price
            )
            transaction.save()

            # Publish the new amount back to the topic
            response_data = {
                "response": {
                    "new_amount": new_amount
                }
            }
            print(json.dumps(response_data))
            client.publish(topic, json.dumps(response_data))

        except Passenger.DoesNotExist:
            response_data = {
                "response": "Passenger with this NIC does not exist"
            }
            print(json.dumps(response_data))
            client.publish(topic, json.dumps(response_data))

        except Card.DoesNotExist:
            response_data = {
                "response": "No card found for this NIC"
            }
            print(json.dumps(response_data))
            client.publish(topic, json.dumps(response_data))

        except Exception as e:
            response_data = {
                "response": f"Error: {str(e)}"
            }
            print(json.dumps(response_data))
            client.publish(topic, json.dumps(response_data))

    

def start_mqtt_client():
    client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message

    # Configure TLS/SSL with debugging
    client.tls_set(
        ca_certs=settings.MQTT_CA_PATH,
        certfile=settings.MQTT_CERT_PATH,
        keyfile=settings.MQTT_KEY_PATH,
        tls_version=2
    )
    client.tls_insecure_set(True)  # To avoid SSL verification errors (test only, not recommended for prod)

    try:
        print("Connecting to MQTT broker...")
        client.connect(settings.MQTT_BROKER_URL, settings.MQTT_BROKER_PORT)
        print("Connected successfully.")
    except Exception as e:
        print(f"Connection failed: {e}")
        
    client.loop_start()
    return client
