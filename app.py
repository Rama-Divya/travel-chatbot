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

# Initialize speech recognition and text-to-speech
recognizer = sr.Recognizer()
engine = pyttsx3.init()
engine.setProperty('rate', 150)

# Geoapify API Key
GEOAPIFY_KEY = "484e5851895a4b54bcdabcb4c1f5e34d"

# ------ Core Functionality ------
# Number word to digit mapping
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10
}

YES_NO_WORDS = ["yes", "no", "yeah", "yep", "sure", "no", "nope", "nah"]

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
    return [
        {"name": f"Grand {city} Hotel", "price": "$150/night", "rating": 4.5, "address": f"123 Main St, {city}"},
        {"name": f"{city} Plaza", "price": "$200/night", "rating": 4.2, "address": f"456 Center Ave, {city}"},
        {"name": f"Cozy {city} Inn", "price": "$120/night", "rating": 3.9, "address": f"789 Side Rd, {city}"}
    ]

def get_flight_options(destination):
    if not destination:
        return []
    return [
        {
            "airline": "SkyHigh Airlines",
            "flight_number": f"SH{random.randint(100,999)}",
            "departure": "08:00 AM",
            "arrival": "11:00 AM",
            "duration": "3h",
            "price": "$250",
            "seats": list(string.ascii_uppercase[:10])
        },
        {
            "airline": "Global Airways",
            "flight_number": f"GA{random.randint(100,999)}", 
            "departure": "02:00 PM",
            "arrival": "06:30 PM",
            "duration": "4h 30m",
            "price": "$320",
            "seats": list(string.ascii_uppercase[:10])
        }
    ]

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
    
    # Extract city from input if not already in context
    city = extract_city(user_input) or context.get('city')
    
    # Handle weather query
    if "weather" in user_input.lower():
        # Get city from user input if not already set
        query_city = extract_city(user_input) or context.get('city')
        if not query_city:
            context['awaiting_city'] = True
            context['intent'] = 'weather'
            return chat_history + [(user_input, "Which city's weather would you like to know?")], context
        
        # Mock weather response
        weather_responses = [
            f"The weather in {query_city} is sunny with a high of 75°F",
            f"Expect cloudy skies in {query_city} with a chance of rain, 68°F",
            f"{query_city} is currently experiencing clear skies, 82°F"
        ]
        response = random.choice(weather_responses)
        context['city'] = query_city  # Remember city for context
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
        if any(yes_word in user_input.lower() for yes_word in ["yes", "yeah", "yep", "sure"]):
            context['awaiting_name'] = True
            context.pop('awaiting_confirmation', None)
            return chat_history + [(user_input, "Please provide your full name:")], context
        else:
            context.clear()
            return chat_history + [(user_input, "Booking cancelled. How else can I help?")], context
    
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
    
    # Handle bookings query - UPDATED TO INCLUDE BOOKING ID AND NAME
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

with gr.Blocks(title="✈️ AI Travel Assistant", theme=gr.themes.Soft()) as app:
    gr.Markdown("""
    <div style="text-align: center;">
        <h1>✈️ AI Travel Assistant</h1>
        <p><b>Book hotels, flights, and explore attractions</b></p>
        <p><i>Speak or type your request below</i></p>
    </div>
    """)
    
    context_state = gr.State({})
    
    with gr.Row():
        chatbot = gr.Chatbot(
            height=500,
            bubble_full_width=False,
            show_copy_button=True,
            avatar_images=(
                "https://cdn-icons-png.flaticon.com/512/1995/1995485.png", 
                "https://cdn-icons-png.flaticon.com/512/4712/4712035.png"
            )
        )
    
    with gr.Row():
        with gr.Column(scale=1):
            voice_btn = gr.Button("🎤 Speak", variant="primary")
        with gr.Column(scale=4):
            text_input = gr.Textbox(placeholder="e.g., 'Book a hotel in Paris' or 'What's the weather in Tokyo?'", show_label=False)
        with gr.Column(scale=1):
            speak_btn = gr.Button("🔊 Speak Response")
    
    with gr.Row():
        clear_btn = gr.Button("🧹 Clear Chat", variant="secondary")
        restart_btn = gr.Button("🔄 Restart Conversation", variant="secondary")
    
    gr.Examples(
        examples=[
            ["Book a hotel in Tokyo"],
            ["Show flights to Paris"],
            ["What's the weather in London?"],
            ["Top attractions in New York"],
            ["View my bookings"]
        ],
        inputs=text_input,
        label="Try these examples:"
    )
    
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

if __name__ == "__main__":
    app.launch()