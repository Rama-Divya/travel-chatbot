import speech_recognition as sr
import pyttsx3
import re
import json
import os
from uuid import uuid4
from weather import get_weather
from places import get_top_attractions

# Initialize text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)

# Database setup
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
        details = f"Flight: {booking['airline']} to {booking['destination']}"
    
    return (
        f"✅ Booking confirmed!\n"
        f"Confirmation ID: {booking['id']}\n"
        f"Name: {booking['user']}\n"
        f"Type: {booking['type'].title()}\n"
        f"{details}\n"
        f"Date: {booking['date']}\n"
        "Thank you for choosing our service!"
    )

# Number mappings for voice commands
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10
}

# Expanded yes/no recognition with intent detection
POSITIVE_WORDS = ["yes", "yeah", "yep", "sure", "ok", "okay", "affirmative", "absolutely", "book it", "confirm"]
NEGATIVE_WORDS = ["no", "nah", "nope", "negative", "cancel", "stop", "don't", "not"]
YES_NO_WORDS = POSITIVE_WORDS + NEGATIVE_WORDS

ORDINAL_WORDS = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"
}

# Hotel and flight data providers
def get_hotel_options(city):
    if not city:
        return []
    return [
        {"name": f"Grand {city} Hotel", "price": "$150/night", "rating": 4.5, "address": f"123 Main St, {city}"},
        {"name": f"{city} Plaza", "price": "$200/night", "rating": 4.2, "address": f"456 Center Ave, {city}"},
        {"name": f"Cozy {city} Inn", "price": "$120/night", "rating": 3.9, "address": f"789 Side Rd, {city}"}
    ]

def get_flight_options(destination):
    if not destination:
        return []
    return [
        {"airline": "SkyHigh Airlines", "departure": "08:00 AM", "arrival": "11:00 AM", "duration": "3h", "price": "$250"},
        {"airline": "Global Airways", "departure": "02:00 PM", "arrival": "06:30 PM", "duration": "4h 30m", "price": "$320"}
    ]

# Voice input/output functions
def speak_output(text):
    print(f"Assistant: {text}")
    engine.say(text)
    engine.runAndWait()

def list_options(options_list, item_type, city):
    options_text = f"Here are the available {item_type} options in {city}:\n"
    for i, option in enumerate(options_list, 1):
        if item_type == "hotel":
            options_text += f"{ORDINAL_WORDS.get(i, str(i))}. {option['name']} - {option['price']} - Rating: {option['rating']}\n"
        elif item_type == "flight":
            options_text += f"{ORDINAL_WORDS.get(i, str(i))}. {option['airline']} - Departs at {option['departure']} for {option['price']}\n"
    return options_text

# Improved city extraction with multi-word support
def extract_city(text):
    if not text:
        return None
    
    # Enhanced patterns with better city recognition
    patterns = [
        r"\b(?:in|at|for|near|to)\s+([a-zA-Z\s]{3,})\b",
        r"\b(?:hotels?|flights?|weather|places?|attractions?)\s+(?:in|at|for|near|to)?\s*([a-zA-Z\s]{3,})\b",
        r"\b(?:book|find|show)\s+(?:a\s+)?(?:hotel|flight)\s+(?:in|at|for|near|to)?\s*([a-zA-Z\s]{3,})\b",
        r"\b([A-Z][a-zA-Z\s]{3,})\b"
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            city = match.group(1).strip()
            # Improved stop words removal
            city = re.sub(r'\b(?:please|today|now|book|find|show|attractions?|places?|hotels?|flights?|weather)\b', 
                         '', city, flags=re.IGNORECASE).strip()
            city = re.sub(r'\s+\b(?:in|at|for|near|to)\b$', '', city, flags=re.IGNORECASE).strip()
            if city and len(city) > 2:  # Filter out short invalid matches
                return city.title()
    return None

def get_voice_input(prompt="Speak now...", max_attempts=3, expected=None, timeout=10, phrase_limit=8):
    recognizer = sr.Recognizer()
    for attempt in range(max_attempts):
        with sr.Microphone() as source:
            print(f"🎤 {prompt} (Attempt {attempt + 1} of {max_attempts})")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
                text = recognizer.recognize_google(audio).lower()
                print(f"🗣️ You said: {text}")
                
                if expected:
                    # Check for exact matches
                    if text in expected:
                        return text
                    
                    # Check for partial matches
                    for word in expected:
                        if word in text:
                            return word
                    
                    # Check for positive/negative intent
                    if any(pos in text for pos in POSITIVE_WORDS):
                        return "yes"
                    if any(neg in text for neg in NEGATIVE_WORDS):
                        return "no"
                return text
            except sr.UnknownValueError:
                print("Could not understand audio.")
                speak_output("Sorry, I didn't catch that. Please try again.")
            except sr.RequestError as e:
                print(f"Could not request results; {e}")
                speak_output("There was an error with the speech recognition service.")
            except sr.WaitTimeoutError:
                print("Listening timed out.")
                speak_output("I didn't hear anything. Please try again.")
    
    speak_output("Switching to text input for this step.")
    return input("✍️ Please type your response: ").lower()

def convert_to_number(word):
    return NUMBER_WORDS.get(word.strip().lower(), None) if word else None

# Booking workflow
def ask_for_booking(item_type, item_data, city, is_voice=False):
    if is_voice:
        speak_output(f"Do you want to book this {item_type}? Please say yes or no.")
        response = get_voice_input("Confirm booking?", expected=YES_NO_WORDS, phrase_limit=5)
    else:
        response = input("✍️ Book this? (yes/no): ").lower()

    # Enhanced yes/no detection with intent analysis
    if any(pos in response for pos in POSITIVE_WORDS):
        return proceed_with_booking(item_type, item_data, city, is_voice)
    elif any(neg in response for neg in NEGATIVE_WORDS):
        return "Booking cancelled."
    
    # Fallback: Ask to confirm with a gesture
    if is_voice:
        speak_output("I'm having trouble understanding. Please nod for yes or shake your head for no.")
        response = get_voice_input("Confirm booking? (say yes/no or nod/shake head)", expected=YES_NO_WORDS, max_attempts=2)
        if any(pos in response for pos in POSITIVE_WORDS):
            return proceed_with_booking(item_type, item_data, city, is_voice)
    
    return "Booking cancelled."

def proceed_with_booking(item_type, item_data, city, is_voice):
    # Handle missing city name
    if not city:
        if is_voice:
            speak_output("Which city is this for? Please say the city name.")
            city_response = get_voice_input("Say the city name", phrase_limit=6)
            city = extract_city(city_response) or city_response.title()
        else:
            city = input("✍️ Enter city name: ").title()
    
    if not city:
        return "Booking cancelled. City not provided."
    
    # Get user name
    if is_voice:
        speak_output("Please say your full name for the booking.")
        name = get_voice_input("Your full name", phrase_limit=7)
    else:
        name = input("✍️ Enter your full name: ")
    
    if not name:
        return "Booking cancelled. No name provided."
    
    booking = {
        "id": str(uuid4())[:8].upper(),
        "type": item_type,
        "user": name,
        "date": "Today"
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
            "destination": city, 
            "departure": item_data.get('departure', 'N/A'),
            "price": item_data.get('price', 'N/A')
        })
    
    result = save_booking(booking)
    if is_voice:
        speak_output(result)
    return result

def handle_number_selection(options, item_type, city, is_voice):
    options_text = list_options(options, item_type, city)
    speak_output(options_text)
    
    valid_choices = list(ORDINAL_WORDS.values())[:len(options)] + [str(i) for i in range(1, len(options)+1)] + ["cancel"]
    prompt = f"Please say {ORDINAL_WORDS.get(1, 'first')} through {ORDINAL_WORDS.get(len(options), str(len(options)))} or 'cancel'"
    speak_output(prompt)
    
    choice = get_voice_input("Select option", expected=valid_choices, phrase_limit=5)
    
    if choice == "cancel":
        return "Selection cancelled."
    
    choice_num = convert_to_number(choice)
    if choice_num is not None and 1 <= choice_num <= len(options):
        selected = options[choice_num - 1]
    else:
        speak_output("I'll select the first option for you.")
        selected = options[0]
    
    return ask_for_booking(item_type, selected, city, is_voice)

# Main query handler
def handle_query(text, is_voice=False):
    if not text:
        return "Please provide a query"
    
    text_lower = text.lower()
    city = extract_city(text)

    # Weather queries
    if "weather" in text_lower:
        if not city:
            if is_voice:
                speak_output("Which city's weather would you like to know?")
                city_response = get_voice_input("Say city name", phrase_limit=6)
                city = extract_city(city_response) or city_response.title()
            else:
                return "City not specified."
        return get_weather(city) if city else "City not recognized."

    # Hotel queries
    if any(k in text_lower for k in ["hotel", "stay", "accommodation", "lodging"]):
        if not city:
            if is_voice:
                speak_output("Which city would you like hotels in?")
                city_response = get_voice_input("Say city name", phrase_limit=6)
                city = extract_city(city_response) or city_response.title()
            else:
                return "City not specified."
        hotels = get_hotel_options(city)
        if not hotels:
            return f"No hotels found in {city}."
        if is_voice:
            return handle_number_selection(hotels, "hotel", city, is_voice)
        return list_options(hotels, "hotel", city)

    # Flight queries
    if any(k in text_lower for k in ["flight", "airline", "fly", "ticket"]):
        if not city:
            if is_voice:
                speak_output("Which city would you like to fly to?")
                city_response = get_voice_input("Say city name", phrase_limit=6)
                city = extract_city(city_response) or city_response.title()
            else:
                return "Destination not specified."
        flights = get_flight_options(city)
        if not flights:
            return f"No flights found to {city}."
        if is_voice:
            return handle_number_selection(flights, "flight", city, is_voice)
        return list_options(flights, "flight", city)

    # Attractions queries
    if any(k in text_lower for k in ["places", "attractions", "things to do", "sightseeing"]):
        if not city:
            if is_voice:
                speak_output("Which city would you like to explore?")
                city_response = get_voice_input("Say city name", phrase_limit=6)
                city = extract_city(city_response) or city_response.title()
            else:
                return "City not specified."
        places = get_top_attractions(city) if city else []
        if not places:
            return f"No attractions found in {city}."
        return f"Top attractions in {city}:\n" + "\n".join(f"- {place}" for place in places)

    # Booking management
    if any(k in text_lower for k in ["booking", "reservation", "my bookings"]):
        bookings = load_bookings()
        if not bookings:
            return "No bookings yet."
        
        response = "Your bookings:\n"
        for i, booking in enumerate(bookings, 1):
            if booking['type'] == 'hotel':
                details = f"Hotel: {booking.get('hotel', 'N/A')} in {booking.get('city', 'N/A')}"
            elif booking['type'] == 'flight':
                details = f"Flight: {booking.get('airline', 'N/A')} to {booking.get('destination', 'N/A')}"
            else:
                details = "Unknown booking type"
            response += f"{i}. {details} (ID: {booking['id']})\n"
        return response

    return "Sorry, I didn't understand. Try asking about weather, flights, hotels, or places."

# Main application loop
def main():
    speak_output("Hello! I'm your voice travel assistant. How can I help you today?")
    
    while True:
        spoken = get_voice_input("You can ask about flights, hotels, weather, or attractions. Say 'exit' to quit.")
        if not spoken:
            speak_output("Please try again.")
            continue
            
        spoken_lower = spoken.lower()
        if "exit" in spoken_lower or "quit" in spoken_lower or "goodbye" in spoken_lower:
            speak_output("Goodbye! Have a great trip!")
            break
            
        print(f"🗣️ You said: {spoken}")
        response = handle_query(spoken, is_voice=True)
        print("💬", response)
        speak_output(response)

if __name__ == "__main__":
    main()