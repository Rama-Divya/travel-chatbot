# places.py
import requests

API_KEY = "484e5851895a4b54bcdabcb4c1f5e34d"

def get_top_attractions(city):
    try:
        # Step 1: Get coordinates of the city
        geocode_url = f"https://api.geoapify.com/v1/geocode/search?text={city}&apiKey={API_KEY}"
        geo_resp = requests.get(geocode_url).json()
        features = geo_resp.get("features")
        if not features:
            return [f"Could not find location for '{city}'."]
        
        coords = features[0]["geometry"]["coordinates"]
        lon, lat = coords[0], coords[1]

        # Step 2: Get points of interest near the city
        pois_url = f"https://api.geoapify.com/v2/places?categories=tourism.sights&filter=circle:{lon},{lat},10000&limit=5&apiKey={API_KEY}"
        pois_resp = requests.get(pois_url).json()
        places = pois_resp.get("features", [])

        if not places:
            return [f"No attractions found in '{city}'."]
        
        return [place["properties"]["name"] for place in places if "name" in place["properties"]]
    
    except Exception as e:
        return [f"Error getting attractions: {e}"]
