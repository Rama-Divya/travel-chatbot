import requests

def get_top_attractions(city, api_key):
    try:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": f"top tourist attractions in {city}",
            "key": "AIzaSyBd8aydUboM4gf82uyCtFpVTu4sc17fRIY"
        }
        response = requests.get(url, params=params)
        data = response.json()

        if "results" in data:
            top_places = [place["name"] for place in data["results"][:5]]
            return top_places
        else:
            return ["No attractions found or error occurred."]
    except Exception as e:
        return [f"API error: {str(e)}"]
