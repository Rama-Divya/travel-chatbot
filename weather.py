import gradio as gr
import speech_recognition as sr
import re
import random
import string
import requests
from uuid import uuid4
from datetime import datetime
import pyttsx3
import json
import os
import time

# Initialize speech recognition and text-to-speech
recognizer = sr.Recognizer()
engine = pyttsx3.init()
engine.setProperty('rate', 150)

# API Keys
GEOAPIFY_KEY = "484e5851895a4b54bcdabcb4c1f5e34d"
OPENWEATHER_API_KEY = "419c43c96821bf08a5d536944bcfcb01"

# ------ Core Functionality ------
# Number word to digit mapping
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

# Initialize data storage
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
    
    # Ensure all required fields are present
    if booking['type'] == 'flight':
        booking.setdefault('destination', booking.get('city', 'Unknown destination'))
        booking.setdefault('flight_number', 'N/A')
        booking.setdefault('departure', 'N/A')
        booking.setdefault('arrival', 'N/A')
    
    bookings.append(booking)
    with open(DATABASE_FILE, 'w') as f:
        json.dump({"bookings": bookings}, f, indent=2)
    return format_booking_confirmation(booking)

def get_hotel_options(city):
    if not city:
        return []
    
    # Popular hotels in major cities
    popular_hotels = {
        "New York": [
            {"name": "The Plaza Hotel", "price": "$450/night", "rating": 4.8, "address": "768 5th Ave, New York"},
            {"name": "The Ritz-Carlton", "price": "$520/night", "rating": 4.9, "address": "50 Central Park S, New York"},
            {"name": "Crosby Street Hotel", "price": "$380/night", "rating": 4.7, "address": "79 Crosby St, New York"}
        ],
        "Paris": [
            {"name": "Hôtel Ritz Paris", "price": "$720/night", "rating": 4.9, "address": "15 Pl. Vendôme, Paris"},
            {"name": "Le Meurice", "price": "$680/night", "rating": 4.8, "address": "228 Rue de Rivoli, Paris"},
            {"name": "Hôtel Plaza Athénée", "price": "$850/night", "rating": 4.9, "address": "25 Av. Montaigne, Paris"}
        ],
        "Tokyo": [
            {"name": "The Ritz-Carlton Tokyo", "price": "$620/night", "rating": 4.9, "address": "Tokyo Midtown 9-7-1 Akasaka"},
            {"name": "Park Hyatt Tokyo", "price": "$580/night", "rating": 4.8, "address": "3-7-1-2 Nishishinjuku, Shinjuku"},
            {"name": "Mandarin Oriental Tokyo", "price": "$750/night", "rating": 4.9, "address": "2-1-1 Nihonbashi Muromachi"}
        ],
        "Dubai": [
            {"name": "Burj Al Arab Jumeirah", "price": "$1,200/night", "rating": 4.9, "address": "Jumeirah St, Dubai"},
            {"name": "Atlantis The Palm", "price": "$850/night", "rating": 4.8, "address": "Crescent Rd, Dubai"},
            {"name": "Armani Hotel Dubai", "price": "$780/night", "rating": 4.7, "address": "Burj Khalifa, Dubai"}
        ]
    }
    
    # Return popular hotels if available, else generic ones
    if city in popular_hotels:
        return popular_hotels[city]
    else:
        return [
            {"name": f"Grand {city} Hotel", "price": "$150/night", "rating": 4.5, "address": f"123 Main St, {city}"},
            {"name": f"{city} Plaza", "price": "$200/night", "rating": 4.2, "address": f"456 Center Ave, {city}"},
            {"name": f"Cozy {city} Inn", "price": "$120/night", "rating": 3.9, "address": f"789 Side Rd, {city}"}
        ]

def get_flight_options(destination):
    if not destination:
        return []
    
    # Popular flight routes
    popular_routes = {
        "New York": [
            {"airline": "Delta Airlines", "departure": "07:30 AM", "arrival": "10:45 AM", "price": "$320"},
            {"airline": "American Airlines", "departure": "02:15 PM", "arrival": "05:30 PM", "price": "$350"},
            {"airline": "United Airlines", "departure": "06:00 PM", "arrival": "09:15 PM", "price": "$300"}
        ],
        "Paris": [
            {"airline": "Air France", "departure": "09:45 AM", "arrival": "11:30 PM", "price": "$780"},
            {"airline": "British Airways", "departure": "01:20 PM", "arrival": "03:00 AM", "price": "$820"},
            {"airline": "Lufthansa", "departure": "05:30 PM", "arrival": "07:10 AM", "price": "$750"}
        ],
        "Tokyo": [
            {"airline": "ANA Airlines", "departure": "10:30 AM", "arrival": "03:45 PM", "price": "$950"},
            {"airline": "Japan Airlines", "departure": "02:00 PM", "arrival": "07:15 PM", "price": "$980"},
            {"airline": "Singapore Airlines", "departure": "08:30 PM", "arrival": "01:45 AM", "price": "$920"}
        ],
        "Dubai": [
            {"airline": "Emirates", "departure": "08:15 AM", "arrival": "07:45 PM", "price": "$880"},
            {"airline": "Etihad Airways", "departure": "12:30 PM", "arrival": "12:00 AM", "price": "$850"},
            {"airline": "Qatar Airways", "departure": "04:45 PM", "arrival": "04:15 AM", "price": "$820"}
        ]
    }
    
    # Return popular flights if available, else generic ones
    if destination in popular_routes:
        return popular_routes[destination]
    else:
        return [
            {
                "airline": "SkyHigh Airlines",
                "departure": "08:00 AM",
                "arrival": "11:00 AM",
                "price": "$250"
            },
            {
                "airline": "Global Airways",
                "departure": "02:00 PM",
                "arrival": "06:30 PM",
                "price": "$320"
            }
        ]

def get_weather(city):
    """
    Fetches current weather data for a given city using OpenWeatherMap API.

    Args:
        city (str): Name of the city to get weather for.

    Returns:
        str: A formatted weather report or error message.
    """
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": OPENWEATHER_API_KEY,
        "units": "metric"
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        if response.status_code == 200:
            temperature = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]
            description = data["weather"][0]["description"].title()
            icon_code = data["weather"][0]["icon"]
            
            # Get weather icon based on code
            weather_icons = {
                "01": "☀️",  # clear sky
                "02": "⛅",  # few clouds
                "03": "☁️",  # scattered clouds
                "04": "☁️",  # broken clouds
                "09": "🌧️",  # shower rain
                "10": "🌦️",  # rain
                "11": "⛈️",  # thunderstorm
                "13": "❄️",  # snow
                "50": "🌫️"   # mist
            }
            icon = weather_icons.get(icon_code[:2], "🌡️")
            
            return (
                f"{icon} Weather in {city.title()}:\n"
                f"• Current: {description}\n"
                f"• Temperature: {temperature}°C (Feels like {feels_like}°C)\n"
                f"• Humidity: {humidity}%\n"
                f"• Wind: {wind_speed} m/s"
            )
        elif response.status_code == 404:
            return f"⚠️ City '{city}' not found. Please check the spelling."
        else:
            return f"❌ Couldn't fetch weather for {city}. Error: {data.get('message', 'Unknown error')}"
    
    except requests.exceptions.RequestException as e:
        return f" Network error: {str(e)}"
    except Exception as e:
        return f"⚠️ Unexpected error: {str(e)}"

def get_top_attractions(city):
    """Get top tourist attractions using Geoapify API"""
    if not city:
        return []
    
    try:
        # Step 1: Get coordinates of the city
        geocode_url = f"https://api.geoapify.com/v1/geocode/search?text={city}&apiKey={GEOAPIFY_KEY}"
        geo_resp = requests.get(geocode_url, timeout=10).json()
        features = geo_resp.get("features", [])
        
        if not features:
            return [f"Could not find location for '{city}'."]
        
        coords = features[0]["geometry"]["coordinates"]
        lon, lat = coords[0], coords[1]

        # Step 2: Get points of interest near the city
        pois_url = f"https://api.geoapify.com/v2/places?categories=tourism.sights&filter=circle:{lon},{lat},10000&limit=5&apiKey={GEOAPIFY_KEY}"
        pois_resp = requests.get(pois_url, timeout=10).json()
        places = pois_resp.get("features", [])

        if not places:
            return [f"No attractions found in '{city}'."]
        
        # Extract and return attraction names
        attractions = []
        for place in places:
            if "name" in place["properties"]:
                attractions.append(place["properties"]["name"])
            if len(attractions) >= 5:  # Limit to 5 attractions
                break
                
        return attractions if attractions else [f"No attractions found in '{city}'."]
    
    except requests.exceptions.Timeout:
        return ["The request timed out. Please try again later."]
    except Exception as e:
        return [f"Error getting attractions: {str(e)}"]

# Improved city extraction with multi-word support
def extract_city(text):
    if not text:
        return None
    
    patterns = [
        r"\b(?:in|at|for|near|to)\s+([a-zA-Z\s]{3,})\b",
        r"\b(?:hotels?|flights?|weather|places?|attractions?)\s+(?:in|at|for|near|to)?\s*([a-zA-Z\s]+)\b",
        r"\b(?:book|find|show)\s+(?:a\s+)?(?:hotel|flight)\s+(?:in|at|for|near|to)?\s*([a-zA-Z\s]+)\b",
        r"\b([A-Z][a-zA-Z\s]{3,})\b"
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            city = match.group(1).strip()
            city = re.sub(r'\b(?:please|today|now|book|find|show|attractions?|places?)\b', '', city, flags=re.IGNORECASE).strip()
            city = re.sub(r'\s+\b(?:in|at|for|near|to)\b$', '', city, flags=re.IGNORECASE).strip()
            if city and len(city) > 2:  # Filter out short invalid matches
                return city.title()
    return None

def ui_listen():
    with sr.Microphone() as source:
        try:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
            text = recognizer.recognize_google(audio).lower()
            print(f"Heard: {text}")
            return text
        except sr.UnknownValueError:
            print("Could not understand audio.")
            return None
        except Exception as e:
            print(f"Listening error: {e}")
            return None

def convert_to_number(word):
    return NUMBER_WORDS.get(str(word).lower().strip(), None)

def format_booking_confirmation(booking):
    if booking['type'] == 'hotel':
        return f"""✅ Hotel Booking Confirmed!
ID: {booking['id']}
Name: {booking['user']}
Hotel: {booking['hotel']}
City: {booking['city']}
Price: {booking['price']}
Address: {booking.get('address', 'N/A')}
Check-in: Today"""
    else:
        return f"""✅ Flight Booking Confirmed!
ID: {booking['id']}
Name: {booking['user']}
Flight: {booking['airline']} {booking.get('flight_number', 'N/A')}
Destination: {booking.get('destination', booking.get('city', 'Unknown'))}
Departure: {booking.get('departure', 'N/A')} | Arrival: {booking.get('arrival', 'N/A')}
Price: {booking['price']}"""

def list_options(options_list, item_type, city):
    options_text = f"Here are the available {item_type} options in {city}:\n"
    for i, option in enumerate(options_list, 1):
        if item_type == "hotel":
            options_text += f"{ORDINAL_WORDS.get(i, str(i))}. {option['name']} - {option['price']} - Rating: {option['rating']}\n"
        elif item_type == "flight":
            options_text += f"{ORDINAL_WORDS.get(i, str(i))}. {option['airline']} - Departs at {option['departure']} for {option['price']}\n"
    return options_text

# ------ Gradio Application ------
def handle_flow(user_input, chat_history, context):
    # Clear context when starting over
    if user_input.lower() in ['restart', 'clear', 'new', 'reset']:
        context.clear()
        return chat_history + [(user_input, "How can I help you with your travel plans?")], context
    
    # Handle weather query
    if "weather" in user_input.lower():
        city = extract_city(user_input) or context.get('city')
        if not city:
            context['awaiting_city'] = True
            context['intent'] = 'weather'
            return chat_history + [(user_input, "Which city's weather would you like to know?")], context
        
        response = get_weather(city)
        context['city'] = city  # Remember city for context
        return chat_history + [(user_input, response)], context
    
    # Handle hotel booking flow
    if any(k in user_input.lower() for k in ["hotel", "stay", "accommodation"]):
        # Reset booking context
        context.pop('awaiting_selection', None)
        context.pop('awaiting_confirmation', None)
        context.pop('selected_item', None)
        context.pop('awaiting_name', None)
        
        # Extract city from current input
        city = extract_city(user_input)
        if city:
            context['city'] = city
        
        if not context.get('city'):
            context['awaiting_city'] = True
            context['intent'] = 'hotel'
            return chat_history + [(user_input, "Which city would you like to book a hotel in?")], context
        
        hotels = get_hotel_options(context['city'])
        if not hotels:
            return chat_history + [(user_input, f"Sorry, no hotels found in {context['city']}")], context
        
        context.update({
            'hotels': hotels,
            'awaiting_selection': True,
            'booking_type': 'hotel'
        })
        options = list_options(hotels, "hotel", context['city'])
        return chat_history + [(user_input, f"{options}\n\nWhich would you like? (1-{len(hotels)})")], context
    
    # Handle flight booking flow
    elif any(k in user_input.lower() for k in ["flight", "fly", "airline"]):
        # Reset booking context
        context.pop('awaiting_selection', None)
        context.pop('awaiting_confirmation', None)
        context.pop('selected_item', None)
        context.pop('awaiting_name', None)
        
        # Extract city from current input
        city = extract_city(user_input)
        if city:
            context['city'] = city
        
        if not context.get('city'):
            context['awaiting_city'] = True
            context['intent'] = 'flight'
            return chat_history + [(user_input, "Which city would you like to fly to?")], context
        
        flights = get_flight_options(context['city'])
        if not flights:
            return chat_history + [(user_input, f"Sorry, no flights available to {context['city']}")], context
        
        context.update({
            'flights': flights,
            'awaiting_selection': True,
            'booking_type': 'flight'
        })
        options = list_options(flights, "flight", context['city'])
        return chat_history + [(user_input, f"{options}\n\nWhich would you like? (1-{len(flights)})")], context
    
    # Handle selection of a hotel or flight
    elif context.get('awaiting_selection'):
        selection = convert_to_number(user_input)
        items = context.get('flights') or context.get('hotels')
        
        if selection and 1 <= selection <= len(items):
            selected = items[selection-1]
            context.update({
                'selected_item': selected,
                'awaiting_confirmation': True,
                'awaiting_selection': False
            })
            price = selected.get('price', '$0')
            item_name = selected.get('name', selected.get('airline'))
            return chat_history + [(user_input, f"Selected: {item_name} for {price}\n\nConfirm booking? (yes/no)")], context
        
        return chat_history + [(user_input, f"Please select a number between 1-{len(items)}")], context
    
    # Handle booking confirmation
    elif context.get('awaiting_confirmation'):
        if any(yes_word in user_input.lower() for yes_word in POSITIVE_WORDS):
            context['awaiting_name'] = True
            context.pop('awaiting_confirmation', None)
            return chat_history + [(user_input, "Please provide your full name:")], context
        elif any(neg_word in user_input.lower() for neg_word in NEGATIVE_WORDS):
            context.clear()
            return chat_history + [(user_input, "Booking cancelled. How else can I help?")], context
        else:
            return chat_history + [(user_input, "Please respond with 'yes' or 'no' to confirm booking")], context
    
    # Handle name collection for booking
    elif context.get('awaiting_name'):
        try:
            # Ensure we have all required context
            if 'selected_item' not in context or 'city' not in context or 'booking_type' not in context:
                error_msg = "Booking failed due to missing information. Please start over."
                return chat_history + [(user_input, error_msg)], {}
            
            booking = {
                "id": str(uuid4())[:8].upper(),
                "type": context['booking_type'],
                "user": user_input,
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            
            if context['booking_type'] == 'hotel':
                booking.update({
                    "hotel": context['selected_item']['name'],
                    "city": context['city'],
                    "price": context['selected_item']['price'],
                    "address": context['selected_item'].get('address', 'N/A'),
                    "rating": context['selected_item'].get('rating', 'N/A')
                })
            else:
                booking.update({
                    "airline": context['selected_item']['airline'],
                    "flight_number": context['selected_item'].get('flight_number', 'N/A'),
                    "destination": context['city'],  # Ensure destination is set
                    "departure": context['selected_item'].get('departure', 'N/A'),
                    "arrival": context['selected_item'].get('arrival', 'N/A'),
                    "price": context['selected_item']['price']
                })
            
            result = save_booking(booking)
            # Return response and clear context
            return chat_history + [(user_input, result)], {}
        except Exception as e:
            error_msg = f"Error creating booking: {str(e)}"
            return chat_history + [(user_input, error_msg)], {}
    
    # Handle city input
    elif context.get('awaiting_city'):
        city = extract_city(user_input)
        if city:
            context['city'] = city
            context.pop('awaiting_city', None)
            # Recall the original intent
            intent = context.get('intent', '')
            if intent == 'hotel':
                return handle_flow("book hotel", chat_history, context)
            elif intent == 'flight':
                return handle_flow("book flight", chat_history, context)
            elif intent == 'attractions':
                return handle_flow("show attractions", chat_history, context)
            elif intent == 'weather':
                return handle_flow("weather", chat_history, context)
        return chat_history + [(user_input, "Sorry, I didn't get that. Please provide a valid city name.")], context
    
    # Handle attractions query
    elif any(k in user_input.lower() for k in ["attractions", "places", "sightseeing", "what to see", "things to do"]):
        city = extract_city(user_input) or context.get('city')
        if not city:
            context['awaiting_city'] = True
            context['intent'] = 'attractions'
            return chat_history + [(user_input, "Which city would you like attraction information for?")], context
        
        attractions = get_top_attractions(city)
        if not attractions:
            return chat_history + [(user_input, f"Sorry, no attraction information for {city}")], context
        
        context['city'] = city
        attractions_list = "\n- " + "\n- ".join(attractions)
        return chat_history + [(user_input, f"Top attractions in {city}:{attractions_list}")], context
    
    # Handle bookings query
    elif any(k in user_input.lower() for k in ["bookings", "reservations", "my trips"]):
        bookings = load_bookings()
        if not bookings:
            return chat_history + [(user_input, "You have no bookings yet.")], context
        
        booking_list = []
        for i, b in enumerate(bookings, 1):
            # Get common fields
            booking_id = b.get('id', 'N/A')
            user_name = b.get('user', 'Unknown')
            
            if b['type'] == 'hotel':
                # Get hotel-specific fields
                hotel = b.get('hotel', 'Unknown hotel')
                city = b.get('city', 'Unknown city')
                price = b.get('price', '?')
                booking_list.append(f"{i}. 🏨 ID: {booking_id} | {user_name}: {hotel} in {city} ({price})")
            else:
                # Get flight-specific fields
                airline = b.get('airline', 'Unknown airline')
                destination = b.get('destination', b.get('city', 'Unknown destination'))
                price = b.get('price', '?')
                booking_list.append(f"{i}. ✈️ ID: {booking_id} | {user_name}: {airline} to {destination} ({price})")
        
        return chat_history + [(user_input, "Your bookings:\n" + "\n".join(booking_list))], context
    
    # Default response for other queries
    else:
        return chat_history + [(user_input, """I can help with:
- Booking hotels 🏨
- Finding flights ✈️
- Local attractions 🏛️
- Weather information 🌤️
- Viewing bookings 📋

For example: 
"Book a hotel in Paris" 
"Show flights to Tokyo"
"What's the weather in London?"
"Top attractions in New York"
"View my bookings".""")], context

def handle_voice(chat_history, context):
    user_input = ui_listen()
    if not user_input:
        return chat_history + [("", "Sorry, I didn't catch that. Please try again.")], context
    return handle_flow(user_input, chat_history, context)

def handle_text(user_input, chat_history, context):
    if not user_input.strip():
        return chat_history, "", context
    new_history, new_context = handle_flow(user_input, chat_history, context)
    return new_history, "", new_context

def speak_response(chat_history):
    if chat_history:
        last_response = chat_history[-1][1]
        engine.say(last_response)
        engine.runAndWait()

def get_current_time():
    return datetime.now().strftime("%H:%M")

def get_current_date():
    return datetime.now().strftime("%d-%m-%Y")

# Custom CSS for Copilot2Trip-like design
copilot_css = """
:root {
    --primary: #2563eb;
    --primary-dark: #1d4ed8;
    --secondary: #f97316;
    --dark: #1e293b;
    --light: #f8fafc;
    --gray: #94a3b8;
    --card-bg: rgba(255, 255, 255, 0.92);
    --glass: rgba(255, 255, 255, 0.1);
}

body {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    min-height: 100vh;
    padding: 20px;
    color: white;
}

.gradio-container {
    max-width: 1200px;
    margin: 0 auto;
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important;
}

#hero {
    text-align: center;
    padding: 30px 20px 20px;
    margin-bottom: 20px;
}

#hero h1 {
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 10px;
    background: linear-gradient(to right, #38bdf8, #60a5fa);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}

#hero p {
    font-size: 1.1rem;
    max-width: 700px;
    margin: 0 auto 20px;
    color: #cbd5e1;
    opacity: 0.9;
    line-height: 1.6;
}

#features {
    display: flex;
    justify-content: center;
    gap: 15px;
    margin: 20px 0;
    flex-wrap: wrap;
}

.feature-card {
    background: var(--glass);
    border-radius: 16px;
    padding: 20px 15px;
    width: 160px;
    text-align: center;
    transition: all 0.3s ease;
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    cursor: pointer;
}

.feature-card:hover {
    transform: translateY(-5px);
    background: rgba(30, 41, 59, 0.5);
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
}

.feature-card i {
    font-size: 2.2rem;
    margin-bottom: 12px;
    color: #60a5fa;
}

.feature-card h3 {
    font-weight: 600;
    margin-bottom: 6px;
    color: white;
    font-size: 1.1rem;
}

.feature-card p {
    font-size: 0.9rem;
    color: #94a3b8;
    margin: 0;
}

.gradio-chatbot {
    min-height: 400px;
    border-radius: 20px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    background: rgba(15, 23, 42, 0.7) !important;
    backdrop-filter: blur(10px);
    padding: 15px !important;
    margin-top: 20px;
}

.gradio-chatbot .message {
    padding: 14px 18px !important;
    border-radius: 18px !important;
    margin: 10px 0 !important;
    line-height: 1.5 !important;
    font-size: 1.05rem;
}

.gradio-button {
    background: var(--primary) !important;
    color: white !important;
    border-radius: 14px !important;
    padding: 12px 24px !important;
    font-weight: 600 !important;
    border: none !important;
    transition: all 0.3s ease !important;
    font-size: 0.95rem !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25) !important;
}

.gradio-button:hover {
    background: var(--primary-dark) !important;
    transform: translateY(-3px);
    box-shadow: 0 6px 20px rgba(37, 99, 235, 0.35) !important;
}

.secondary-button {
    background: rgba(255, 255, 255, 0.1) !important;
    color: white !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

.dark-button {
    background: rgba(30, 41, 59, 0.8) !important;
}

.examples-container {
    background: rgba(15, 23, 42, 0.5);
    border-radius: 16px;
    padding: 20px;
    margin: 25px 0;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.examples-header {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 15px;
    color: #60a5fa;
    display: flex;
    align-items: center;
    gap: 10px;
}

.examples-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}

.example-pill {
    background: rgba(30, 41, 59, 0.7);
    border-radius: 50px;
    padding: 8px 18px;
    cursor: pointer;
    transition: all 0.3s ease;
    font-size: 0.95rem;
    border: 1px solid rgba(96, 165, 250, 0.3);
    color: #e2e8f0;
    font-weight: 500;
}

.example-pill:hover {
    background: #3b82f6;
    color: white;
    border-color: #3b82f6;
    transform: translateY(-2px);
}

.gradio-input {
    border-radius: 16px !important;
    padding: 16px 22px !important;
    font-size: 1.05rem !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    background: rgba(15, 23, 42, 0.7) !important;
    color: white !important;
    transition: all 0.3s ease !important;
}

.gradio-input:focus {
    border-color: #60a5fa !important;
    box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.2) !important;
    outline: none;
}

.gradio-input::placeholder {
    color: #94a3b8 !important;
}

.input-container {
    background: rgba(15, 23, 42, 0.5);
    border-radius: 16px;
    padding: 18px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 20px;
}

.actions-container {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 15px;
}

.chat-message.user {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
    color: white !important;
    border-radius: 22px 22px 5px 22px !important;
    margin-left: 20% !important;
    border: none !important;
}

.chat-message.bot {
    background: rgba(30, 41, 59, 0.7) !important;
    border: 1px solid rgba(96, 165, 250, 0.2) !important;
    border-radius: 22px 22px 22px 5px !important;
    margin-right: 20% !important;
    color: #e2e8f0 !important;
}

#footer {
    text-align: center;
    margin-top: 30px;
    color: #64748b;
    font-size: 0.9rem;
    padding: 15px;
}

.avatar {
    border-radius: 12px !important;
}

.status-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 20px;
    background: rgba(15, 23, 42, 0.5);
    border-radius: 16px;
    margin-bottom: 15px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.status-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.95rem;
}

.weather-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    color: #60a5fa;
    font-weight: 500;
}

.language-selector {
    background: rgba(30, 41, 59, 0.7);
    border-radius: 50px;
    padding: 6px 15px;
    font-size: 0.9rem;
    border: 1px solid rgba(96, 165, 250, 0.3);
    color: #e2e8f0;
}

@media (max-width: 768px) {
    .feature-card {
        width: calc(50% - 15px);
    }
    
    .gradio-chatbot {
        min-height: 350px;
    }
    
    .status-bar {
        flex-wrap: wrap;
        gap: 10px;
    }
}
"""

# Initialize time and date
current_time = get_current_time()
current_date = get_current_date()

with gr.Blocks(title="✈️ Travel Assistant", theme=gr.themes.Soft(), css=copilot_css) as app:
    # Hero Section
    with gr.Column(elem_id="hero"):
        gr.Markdown("""
        <h1>Your intelligent travel companion</h1>
        <p>for seamless trip planning</p>
        """)
    
    # Status Bar
    with gr.Row(elem_classes="status-bar"):
        with gr.Column(elem_classes="status-item"):
            gr.Markdown(f"""
            <div class="weather-indicator">
                <span>☔ Rain coming 9:18 PM</span>
            </div>
            """)
        
        with gr.Column(elem_classes="status-item"):
            gr.Markdown(f"""
            <div style="display: flex; align-items: center; gap: 10px;">
                <span>🔍 Search</span>
                <span class="language-selector">ENG IN</span>
            </div>
            """)
        
        with gr.Column(elem_classes="status-item"):
            gr.Markdown(f"""
            <div>
                <div style="font-size: 1.1rem; font-weight: 500;">{current_time}</div>
                <div style="font-size: 0.9rem;">{current_date}</div>
            </div>
            """)
    
    # Feature Cards
    with gr.Row(elem_id="features"):
        hotels_card = gr.Column(elem_classes="feature-card")
        with hotels_card:
            gr.Markdown("""
            <i>🏨</i>
            <h3>Hotels</h3>
            <p>Find perfect stays</p>
            """)
        
        flights_card = gr.Column(elem_classes="feature-card")
        with flights_card:
            gr.Markdown("""
            <i>✈️</i>
            <h3>Flights</h3>
            <p>Book your journey</p>
            """)
        
        weather_card = gr.Column(elem_classes="feature-card")
        with weather_card:
            gr.Markdown("""
            <i>🌤️</i>
            <h3>Weather</h3>
            <p>Check conditions</p>
            """)
        
        attractions_card = gr.Column(elem_classes="feature-card")
        with attractions_card:
            gr.Markdown("""
            <i>🏛️</i>
            <h3>Attractions</h3>
            <p>Discover experiences</p>
            """)
    
    context_state = gr.State({})
    
    # Chat Interface
    chatbot = gr.Chatbot(
        height=400,
        show_copy_button=True,
        avatar_images=(
            "https://cdn-icons-png.flaticon.com/512/1144/1144760.png",  # User
            "https://cdn-icons-png.flaticon.com/512/4712/4712035.png"   # Assistant
        ),
        elem_classes="gradio-chatbot"
    )
    
    # Input Area
    with gr.Column(elem_classes="input-container"):
        with gr.Row():
            text_input = gr.Textbox(
                placeholder="Ask about hotels, flights, weather, or attractions...",
                show_label=False,
                container=False,
                elem_classes="gradio-input",
                scale=5
            )
            voice_btn = gr.Button("🎤 Speak", variant="primary", elem_classes="gradio-button", scale=1)
            submit_btn = gr.Button("Send", variant="primary", elem_classes="gradio-button", scale=1)
        
        with gr.Row(elem_classes="actions-container"):
            speak_btn = gr.Button("🔊 Speak Response", variant="secondary", elem_classes="gradio-button secondary-button")
            clear_btn = gr.Button("🧹 Clear Chat", variant="secondary", elem_classes="gradio-button secondary-button")
            restart_btn = gr.Button("🔄 Restart", variant="secondary", elem_classes="gradio-button secondary-button")
            bookings_btn = gr.Button("📋 My Bookings", variant="secondary", elem_classes="gradio-button dark-button")
    
    # Examples Section
    with gr.Column(elem_classes="examples-container"):
        gr.Markdown("**Try these examples:**", elem_classes="examples-header")
        with gr.Row(elem_classes="examples-row"):
            example1 = gr.Markdown('<div class="example-pill">Book a hotel in Tokyo</div>')
            example2 = gr.Markdown('<div class="example-pill">Show flights to Paris</div>')
            example3 = gr.Markdown('<div class="example-pill">What\'s the weather in London?</div>')
            example4 = gr.Markdown('<div class="example-pill">Top attractions in New York</div>')
            example5 = gr.Markdown('<div class="example-pill">Find a luxury hotel in Dubai</div>')
    
    # Footer
    gr.Markdown("""
    <div id="footer">
        <p>✈️ Travel Assistant v2.0 • Your AI travel companion</p>
    </div>
    """)
    
    # Event Handling
    voice_btn.click(
        handle_voice,
        inputs=[chatbot, context_state],
        outputs=[chatbot, context_state]
    )
    
    text_input.submit(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )
    
    submit_btn.click(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )
    
    speak_btn.click(
        speak_response,
        inputs=[chatbot],
        outputs=[]
    )
    
    clear_btn.click(
        fn=lambda: ([], {}, ""),
        inputs=[],
        outputs=[chatbot, context_state, text_input]
    )
    
    restart_btn.click(
        fn=lambda: ([], {}, ""),
        inputs=[],
        outputs=[chatbot, context_state, text_input]
    )
    
    bookings_btn.click(
        fn=lambda: ("show my bookings", [], {}),
        inputs=[],
        outputs=[text_input, chatbot, context_state]
    ).then(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )
    
    # Feature card click handlers
    hotels_card.click(
        fn=lambda: ("book hotel", [], {}),
        inputs=[],
        outputs=[text_input, chatbot, context_state]
    ).then(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )
    
    flights_card.click(
        fn=lambda: ("book flight", [], {}),
        inputs=[],
        outputs=[text_input, chatbot, context_state]
    ).then(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )
    
    weather_card.click(
        fn=lambda: ("weather", [], {}),
        inputs=[],
        outputs=[text_input, chatbot, context_state]
    ).then(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )
    
    attractions_card.click(
        fn=lambda: ("show attractions", [], {}),
        inputs=[],
        outputs=[text_input, chatbot, context_state]
    ).then(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )
    
    # Example pill click handlers
    example1.click(
        fn=lambda: ("Book a hotel in Tokyo", [], {}),
        inputs=[],
        outputs=[text_input, chatbot, context_state]
    ).then(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )
    
    example2.click(
        fn=lambda: ("Show flights to Paris", [], {}),
        inputs=[],
        outputs=[text_input, chatbot, context_state]
    ).then(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )
    
    example3.click(
        fn=lambda: ("What's the weather in London?", [], {}),
        inputs=[],
        outputs=[text_input, chatbot, context_state]
    ).then(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )
    
    example4.click(
        fn=lambda: ("Top attractions in New York", [], {}),
        inputs=[],
        outputs=[text_input, chatbot, context_state]
    ).then(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )
    
    example5.click(
        fn=lambda: ("Find a luxury hotel in Dubai", [], {}),
        inputs=[],
        outputs=[text_input, chatbot, context_state]
    ).then(
        handle_text,
        inputs=[text_input, chatbot, context_state],
        outputs=[chatbot, text_input, context_state]
    )

if __name__ == "__main__":
    app.launch()