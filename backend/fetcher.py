import requests
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_earthquakes():
    try:
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
        r = requests.get(url, timeout=10)
        data = r.json()
        events = []
        for feature in data["features"][:10]:
            props = feature["properties"]
            coords = feature["geometry"]["coordinates"]
            if props.get("mag") and coords:
                events.append({
                    "source": "USGS",
                    "title": f"M{props['mag']} Earthquake — {props.get('place', 'Unknown')}",
                    "description": f"Magnitude {props['mag']} earthquake near {props.get('place', 'Unknown')}. Depth: {coords[2]}km.",
                    "latitude": coords[1],
                    "longitude": coords[0],
                    "raw_magnitude": props["mag"],
                    "place": props.get("place", "Unknown"),
                })
        return events
    except Exception as e:
        print(f"USGS fetch error: {e}")
        return []

def fetch_weather_alerts():
    try:
        url = "https://api.weather.gov/alerts/active?status=actual&message_type=alert"
        headers = {"User-Agent": "CrisisIQ/1.0 (contact@crisisiq.dev)"}
        r = requests.get(url, timeout=10, headers=headers)
        data = r.json()
        events = []
        for feature in data.get("features", [])[:8]:
            props = feature["properties"]
            geo = feature.get("geometry")
            if geo and geo.get("coordinates"):
                coords = geo["coordinates"]
                if isinstance(coords[0], list):
                    lat = coords[0][1] if len(coords[0]) > 1 else 39.0
                    lon = coords[0][0] if len(coords[0]) > 0 else -98.0
                else:
                    lat, lon = 39.0, -98.0
            else:
                lat, lon = 39.0, -98.0
            events.append({
                "source": "NOAA",
                "title": props.get("headline", "Weather Alert"),
                "description": props.get("description", "")[:500],
                "latitude": lat,
                "longitude": lon,
                "severity_raw": props.get("severity", "Unknown"),
                "event_type_raw": props.get("event", "Weather"),
            })
        return events
    except Exception as e:
        print(f"NOAA fetch error: {e}")
        return []

def fetch_news_disasters():
    try:
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            return []
        url = f"https://newsapi.org/v2/everything?q=disaster+emergency+flood+earthquake+wildfire&sortBy=publishedAt&pageSize=5&apiKey={api_key}"
        r = requests.get(url, timeout=10)
        data = r.json()
        events = []
        for article in data.get("articles", []):
            if article.get("title") and "[Removed]" not in article.get("title", ""):
                events.append({
                    "source": "NewsAPI",
                    "title": article["title"][:200],
                    "description": (article.get("description") or "")[:500],
                    "latitude": 37.0902 + (hash(article["title"]) % 10 - 5),
                    "longitude": -95.7129 + (hash(article["title"]) % 20 - 10),
                })
        return events
    except Exception as e:
        print(f"NewsAPI fetch error: {e}")
        return []