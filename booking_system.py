# booking_system.py
import json
import os
from uuid import uuid4

DATABASE_FILE = "bookings.json"

def init_db():
    if not os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'w') as f:
            json.dump({"bookings": []}, f)

def load_bookings():
    try:
        with open(DATABASE_FILE, 'r') as f:
            return json.load(f)["bookings"]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_booking(booking):
    init_db()
    bookings = load_bookings()
    bookings.append(booking)
    with open(DATABASE_FILE, 'w') as f:
        json.dump({"bookings": bookings}, f, indent=2)
    return generate_confirmation(booking)

def generate_confirmation(booking):
    details = ""
    if booking['type'] == 'hotel':
        details = f"Hotel: {booking['hotel']} in {booking['city']}"
    elif booking['type'] == 'flight':
        details = f"Flight: {booking['airline']} {booking.get('flight_number', '')} to {booking['destination']}"
    
    return (
        f"✅ Booking confirmed!\n"
        f"Confirmation ID: {booking['id']}\n"
        f"Name: {booking['user']}\n"
        f"Type: {booking['type'].title()}\n"
        f"{details}\n"
        f"Date: {booking['date']}\n"
        "Thank you for choosing our service!"
    )