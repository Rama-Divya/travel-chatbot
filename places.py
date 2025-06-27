import json
import os

def get_top_attractions(city):
    try:
        file_path = os.path.join(os.path.dirname(__file__), "attractions_data.json")
        with open(file_path, "r", encoding="utf-8") as f:
            attractions = json.load(f)
        
        city = city.title()
        if city in attractions:
            return attractions[city][:5]
        else:
            return [f"No data found for {city}. Try another city."]
    except Exception as e:
        return [f"Error loading attractions: {str(e)}"]
