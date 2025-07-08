from .models import Card, Passenger, Transaction

def process_task_id_3(payload):
    nic = payload.get('nic')
    start = payload.get('start')
    end = payload.get('end')
    price = payload.get('amount')

    # Validate required data
    if not all([nic, start, end, price]):
        return {"error": "Missing data"}

    try:
        # Fetch the passenger using NIC
        passenger = Passenger.objects.get(nic_number=nic)

        # Fetch the card linked to the passenger
        card = Card.objects.get(nic_number=passenger)

        # Check if balance is sufficient
        if card.balance < price:
            return {"error": "Insufficient balance"}

        # Deduct amount and update balance
        card.balance -= price
        card.save()

        # Create a transaction record
        Transaction.objects.create(
            card_num=card,
            S_station=str(start),
            E_station=str(end),
            amount=price
        )

        return {"new_amount": card.balance}

    except Passenger.DoesNotExist:
        return {"error": "Passenger not found"}
    except Card.DoesNotExist:
        return {"error": "Card not found"}
    except Exception as e:
        return {"error": str(e)}

