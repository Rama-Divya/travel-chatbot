import speech_recognition as sr
import pyttsx3
import re
from weather import get_weather
from booking_system import save_booking, load_bookings
from places import get_top_attractions
from uuid import uuid4

# Google API key for places
GOOGLE_API_KEY = "AIzaSyBd8aydUboM4gf82uyCtFpVTu4sc1"

engine = pyttsx3.init()

def get_hotel_options(city):
    """Mock hotel data - replace with real API calls"""
    mock_hotels = [
        {
            "name": f"Grand {city} Hotel",
            "price": "$150/night",
            "rating": 4.5,
            "address": f"123 Main St, {city}"
        },
        {
            "name": f"{city} Plaza",
            "price": "$200/night",
            "rating": 4.2,
            "address": f"456 Center Ave, {city}"
        },
        {
            "name": f"Cozy {city} Inn",
            "price": "$120/night",
            "rating": 3.9,
            "address": f"789 Side Rd, {city}"
        }
    ]
    return mock_hotels

def get_flight_options(destination):
    """Mock flight data - replace with real API calls"""
    mock_flights = [
        {
            "airline": "SkyHigh Airlines",
            "flight_number": "SH" + str(100 + hash(destination) % 900),
            "departure": "08:00 AM",
            "arrival": "11:00 AM",
            "duration": "3h",
            "price": "$250"
        },
        {
            "airline": "Global Airways",
            "flight_number": "GA" + str(200 + hash(destination) % 800),
            "departure": "02:00 PM",
            "arrival": "06:30 PM",
            "duration": "4h 30m",
            "price": "$320"
        }
    ]
    return mock_flights

def speak_output(text):
    engine.say(text)
    engine.runAndWait()

def get_voice_input(prompt="Speak now...", max_attempts=2):
    recognizer = sr.Recognizer()
    for attempt in range(max_attempts):
        with sr.Microphone() as source:
            print(f"🎤 {prompt} (Attempt {attempt + 1} of {max_attempts})")
            speak_output(prompt)
            audio = recognizer.listen(source)
        try:
            text = recognizer.recognize_google(audio)
            return text
        except (sr.UnknownValueError, sr.RequestError):
            speak_output("Sorry, I didn't catch that.")
    speak_output("Voice not detected. Please type your response.")
    return input("Enter manually: ").strip()

def extract_city(text):
    if not text:
        return None
    match = re.search(r"in\s+([a-zA-Z\s]+)", text.lower())
    if match:
        city = match.group(1).strip()
        city = re.sub(r"\b(today|now|please|tomorrow)\b", "", city).strip()
        return city.title() if city else None
    elif text.strip().isalpha():
        return text.strip().title()
    return None

def ask_for_booking(item_type, item_data, city):
    speak_output(f"Do you want to book this {item_type}? Say yes or no.")
    response = get_voice_input("Say yes to confirm booking.")
    
    if "yes" in response.lower():
        name = get_voice_input("Please say your name for booking.")
        booking = {
            "id": str(uuid4())[:8].upper(),
            "type": item_type,
            "user": name,
            "date": "Today",
        }
        
        if item_type == "hotel":
            booking.update({
                "hotel": item_data['name'],
                "city": city,
                "price": item_data.get('price', 'N/A')
            })
        elif item_type == "flight":
            booking.update({
                "airline": item_data['airline'],
                "flight_number": item_data.get("flight_number", "N/A"),
                "destination": city,
                "departure": item_data.get('departure', 'N/A'),
                "arrival": item_data.get('arrival', 'N/A'),
                "price": item_data.get('price', 'N/A')
            })
        
        result = save_booking(booking)
        speak_output(result)
        print(result)
        return result
    return "Booking cancelled."

def handle_query(text):
    text = text.lower()
    city = extract_city(text)

    if "weather" in text:
        if not city:
            city = extract_city(get_voice_input("Say the city for weather."))
        if city:
            return get_weather(city)
        else:
            return "No city provided for weather."

    elif "hotel" in text or "stay" in text:
        if not city:
            city = extract_city(get_voice_input("Which city are you looking for hotels in?"))
        if city:
            hotels = get_hotel_options(city)
            if not hotels:
                return f"No hotels found in {city}."
                
            result = f"Top hotels in {city}:\n"
            for i, hotel in enumerate(hotels[:3], 1):
                result += f"{i}. {hotel['name']} - {hotel['price']} - {hotel['rating']}⭐\n"
            
            speak_output(f"Found hotels in {city}. Here are top options.")
            print(result)
            
            speak_output("Which hotel would you like? Say 1, 2, or 3.")
            choice = get_voice_input("Select hotel by number")
            
            try:
                choice_idx = int(choice.strip()) - 1
                selected_hotel = hotels[choice_idx]
            except (ValueError, IndexError):
                speak_output("Booking the top recommendation.")
                selected_hotel = hotels[0]
            
            return ask_for_booking("hotel", selected_hotel, city)
        else:
            return "Please specify a city for hotels."

    elif "flight" in text or "fly" in text:
        if not city:
            city = extract_city(get_voice_input("Where would you like to fly to?"))
        if city:
            flights = get_flight_options(city)
            if not flights:
                return f"No flights available to {city}."
                
            result = f"Flights to {city}:\n"
            for i, flight in enumerate(flights[:3], 1):
                result += (f"{i}. {flight['airline']} {flight['flight_number']}\n"
                         f"   Depart: {flight['departure']} | Arrive: {flight['arrival']}\n"
                         f"   Price: {flight['price']}\n")
            
            speak_output(f"Found flights to {city}. Here are options:")
            print(result)
            
            speak_output("Which flight would you prefer? Say 1, 2, or 3.")
            choice = get_voice_input("Select flight by number")
            
            try:
                choice_idx = int(choice.strip()) - 1
                selected_flight = flights[choice_idx]
            except (ValueError, IndexError):
                speak_output("Booking the first available flight.")
                selected_flight = flights[0]
            
            return ask_for_booking("flight", selected_flight, city)
        else:
            return "Please specify a destination city."

    elif "places" in text or "attractions" in text:
        if not city:
            city = extract_city(get_voice_input("Which city's attractions interest you?"))
        if city:
            places = get_top_attractions(city, GOOGLE_API_KEY)
            return f"Top attractions in {city}:\n" + "\n".join(places)
        else:
            return "No city provided for attractions."
    
    elif "my bookings" in text or "reservations" in text:
        bookings = load_bookings()
        if not bookings:
            return "You have no bookings yet."
        
        result = "Your Bookings:\n" + "="*50 + "\n"
        for booking in bookings:
            if booking['type'] == 'hotel':
                result += (f"ID: {booking['id']}\n"
                          f"Hotel: {booking['hotel']} in {booking['city']}\n"
                          f"Date: {booking['date']}\n"
                          f"Price: {booking.get('price', 'N/A')}\n\n")
            else:
                result += (f"ID: {booking['id']}\n"
                          f"Flight: {booking['airline']} {booking.get('flight_number', '')}\n"
                          f"To: {booking['destination']}\n"
                          f"Date: {booking['date']}\n"
                          f"Price: {booking.get('price', 'N/A')}\n\n")
        result += "="*50
        return result

    else:
        return "Sorry, I didn't understand. Try: weather, hotel, flight, or places."

def main():
    speak_output("Hello! I'm your voice travel assistant.")
    while True:
        spoken = get_voice_input("How can I help? Say 'exit' to quit.")
        if not spoken:
            speak_output("Please try again.")
            continue
        if "exit" in spoken.lower() or "quit" in spoken.lower():
            speak_output("Goodbye! Happy travels!")
            break
            
        print(f"🗣️ You said: {spoken}")
        response = handle_query(spoken)
        print("💬", response)
        speak_output(response)

if __name__ == "__main__":
    main()