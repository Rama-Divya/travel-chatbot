import speech_recognition as sr
import pyttsx3
import re
from weather import get_weather
from booking_system import save_booking, load_bookings
from places import get_top_attractions
from uuid import uuid4

engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Slower speech rate for better understanding

def get_hotel_options(city):
    if not city:
        return []
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
    if not destination:
        return []
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
    print(f"Assistant: {text}")  # Add logging
    engine.say(text)
    engine.runAndWait()

def extract_city(text):
    """Improved city extraction"""
    if not text:
        return None
    
    # More robust patterns
    patterns = [
        r"\b(?:in|at|for|near|to)\s+([a-zA-Z\s]+?)\b",
        r"\b(?:hotels?|flights?|weather|places?|attractions?)\s+(?:in|at|for|near|to)?\s*([a-zA-Z\s]+)\b",
        r"\b(?:book|find|show)\s+(?:a\s+)?(?:hotel|flight)\s+(?:in|at|for|near|to)?\s*([a-zA-Z\s]+)\b",
        r"\b([A-Z][a-zA-Z]{3,})\b"  # Standalone city names
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            city = match.group(1).strip()
            city = re.sub(r'\b(?:please|today|now|book|find|show)\b', '', city, flags=re.IGNORECASE).strip()
            if city:
                return city.title()
    return None

def get_voice_input(prompt="Speak now...", max_attempts=2):
    recognizer = sr.Recognizer()
    for attempt in range(max_attempts):
        with sr.Microphone() as source:
            print(f"🎤 {prompt} (Attempt {attempt + 1} of {max_attempts})")
            recognizer.adjust_for_ambient_noise(source)
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                text = recognizer.recognize_google(audio)
                return text
            except (sr.UnknownValueError, sr.RequestError) as e:
                print(f"Voice recognition error: {str(e)}")
                speak_output("Sorry, I didn't catch that. Please try again.")
    return None

def ask_for_booking(item_type, item_data, city, is_voice=False):
    if is_voice:
        speak_output(f"Do you want to book this {item_type}? Say yes or no.")
        response = get_voice_input("Say yes to confirm booking.")
    else:
        return f"Reply 'yes' to book {item_type} at {item_data['name']} in {city}"

    if response and "yes" in response.lower():
        if is_voice:
            name = get_voice_input("Please say your name for booking.")
        else:
            return "Please provide your name for booking"
        
        if not name:
            return "Booking cancelled. No name provided."
            
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
        if is_voice:
            speak_output(result)
        return result
    return "Booking cancelled."

def process_booking_command(text, is_voice=False):
    """Process booking commands in the format: book flight 1 to Paris for John Doe"""
    match = re.match(r"book\s+(flight|hotel)\s+(\d+)\s+to\s+([a-zA-Z\s]+)\s+for\s+([a-zA-Z\s]+)", text, re.IGNORECASE)
    if not match:
        return "Invalid booking format. Use: 'book flight/hotel [number] to [city] for [name]'"
    
    item_type = match.group(1).lower()
    choice = int(match.group(2))
    city = match.group(3).strip().title()
    name = match.group(4).strip()
    
    # Get the options
    if item_type == "flight":
        options = get_flight_options(city)
    elif item_type == "hotel":
        options = get_hotel_options(city)
    else:
        return f"Invalid item type: {item_type}"
    
    if not options:
        return f"No {item_type} options found for {city}."
    
    # Validate choice number
    if choice < 1 or choice > len(options):
        return f"Invalid choice number. Please select between 1 and {len(options)}"
    
    selected = options[choice-1]
    
    # Create the booking
    booking = {
        "id": str(uuid4())[:8].upper(),
        "type": item_type,
        "user": name,
        "date": "Today",
    }

    if item_type == "hotel":
        booking.update({
            "hotel": selected['name'],
            "city": city,
            "price": selected.get('price', 'N/A')
        })
    elif item_type == "flight":
        booking.update({
            "airline": selected['airline'],
            "flight_number": selected.get("flight_number", "N/A"),
            "destination": city,
            "departure": selected.get('departure', 'N/A'),
            "arrival": selected.get('arrival', 'N/A'),
            "price": selected.get('price', 'N/A')
        })

    result = save_booking(booking)
    if is_voice:
        speak_output(result)
    return result

def handle_query(text, is_voice=False):
    """Handle queries for both CLI and Gradio interfaces"""
    if not text:
        return "Please provide a query"
        
    # First check if it's a booking command
    if re.match(r"book\s+(flight|hotel)\s+(\d+)\s+to\s+([a-zA-Z\s]+)\s+for\s+([a-zA-Z\s]+)", text, re.IGNORECASE):
        return process_booking_command(text, is_voice)
        
    original_text = text
    text_lower = text.lower()
    city = extract_city(original_text)
    
    # Help command
    if "help" in text_lower or "what can you do" in text_lower:
        help_msg = ("I can help with:\n"
                   "- Weather forecasts (e.g., 'weather in London')\n"
                   "- Hotel bookings (e.g., 'hotels in Paris')\n"
                   "- Flight information (e.g., 'flights to Tokyo')\n"
                   "- Tourist attractions (e.g., 'places in Rome')\n"
                   "- Your bookings (e.g., 'show my bookings')")
        return help_msg
    
    # Weather
    if "weather" in text_lower:
        if not city:
            if is_voice:
                # Ask for city explicitly
                speak_output("Which city's weather would you like to know?")
                city_text = get_voice_input("Say the city name")
                city = extract_city(city_text) if city_text else None
            if not city:
                return "Please specify a city for weather information."
        return get_weather(city)
    
    # Hotels
    elif "hotel" in text_lower or "stay" in text_lower or "accommodation" in text_lower:
        if not city:
            if is_voice:
                # Ask for city explicitly
                speak_output("Which city are you looking for hotels in?")
                city_text = get_voice_input("Say the city name")
                city = extract_city(city_text) if city_text else None
            if not city:
                return "Please specify a city for hotel options."
        
        hotels = get_hotel_options(city)
        if not hotels:
            return f"No hotels found in {city}."
        
        result = f"🏨 Hotels in {city}:\n" + "\n".join(
            [f"{i}. {h['name']} - {h['price']} - Rating: {h['rating']}⭐" 
             for i, h in enumerate(hotels[:3], 1)])
        
        if is_voice:
            speak_output(f"Found hotels in {city}. Here are top options:")
            print(result)
            speak_output("Which hotel would you like? Say 1, 2, or 3.")
            choice = get_voice_input("Select hotel by number")
            try:
                choice_idx = int(choice.strip()) - 1
                selected_hotel = hotels[choice_idx]
            except (ValueError, IndexError):
                speak_output("Booking the top recommendation.")
                selected_hotel = hotels[0]
            return ask_for_booking("hotel", selected_hotel, city, is_voice)
        else:
            return result + "\n\nTo book, use command: 'book hotel [number] to [city] for [your name]'"
    
    # Flights
    elif "flight" in text_lower or "fly" in text_lower or "airline" in text_lower:
        if not city:
            if is_voice:
                # Ask for city explicitly
                speak_output("Where would you like to fly to?")
                city_text = get_voice_input("Say the destination city")
                city = extract_city(city_text) if city_text else None
            if not city:
                return "Please specify a destination city."
        
        flights = get_flight_options(city)
        if not flights:
            return f"No flights available to {city}."
        
        result = f"✈️ Flights to {city}:\n" + "\n".join(
            [f"{i}. {f['airline']} {f['flight_number']}\n"
             f"   Depart: {f['departure']} | Arrive: {f['arrival']}\n"
             f"   Duration: {f['duration']} | Price: {f['price']}"
             for i, f in enumerate(flights[:3], 1)])
        
        if is_voice:
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
            return ask_for_booking("flight", selected_flight, city, is_voice)
        else:
            return result + "\n\nTo book, use command: 'book flight [number] to [city] for [your name]'"
    
    # Places
    elif "places" in text_lower or "attractions" in text_lower or "visit" in text_lower or "see" in text_lower:
        if not city:
            if is_voice:
                # Ask for city explicitly
                speak_output("Which city would you like to explore?")
                city_text = get_voice_input("Say the city name")
                city = extract_city(city_text) if city_text else None
            if not city:
                return "Please specify a city to explore."
        
        places = get_top_attractions(city)
        if not places:
            return f"No attractions found in {city}."
            
        return f"🏛️ Top attractions in {city}:\n" + "\n".join(places)
    
    # Bookings
    elif "my bookings" in text_lower or "reservations" in text_lower or "bookings" in text_lower:
        bookings = load_bookings()
        if not bookings:
            return "You have no bookings yet."

        result = "📋 Your Bookings:\n" + "="*50 + "\n"
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
        return ("Sorry, I didn't understand. I can help with:\n"
                "- Weather forecasts\n"
                "- Hotel bookings\n"
                "- Flight information\n"
                "- Tourist attractions\n"
                "- Your bookings\n\n"
                "Try: 'hotels in London' or 'weather in Tokyo'")

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
        response = handle_query(spoken, is_voice=True)
        print("💬", response)
        if response:  # Only speak if there's a response
            speak_output(response)

if __name__ == "__main__":
    main()
    