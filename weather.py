import requests
API_KEY = "419c43c96821bf08a5d536944bcfcb01"

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
        "appid": API_KEY,
        "units": "metric"
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        if response.status_code == 200:
            temperature = data["main"]["temp"]
            description = data["weather"][0]["description"]
            return f"The weather in {city.title()} is {description} with a temperature of {temperature}°C."
        elif response.status_code == 404:
            return f"⚠️ City '{city}' not found. Please check the spelling."
        else:
            return f"❌ Couldn't fetch weather for {city}. Error: {data.get('message', 'Unknown error')}"
    
    except requests.exceptions.RequestException as e:
        return f" Network error: {str(e)}"
    except Exception as e:
        return f"⚠️ Unexpected error: {str(e)}"

# 🧪 Test the function directly if running weather.py standalone
if __name__ == "__main__":
    city = input(" Enter city name: ")
    result = get_weather(city)
    print("📢", result)