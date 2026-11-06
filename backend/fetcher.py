import requests
import os
from itertools import zip_longest
from dotenv import load_dotenv

load_dotenv()

def interleave_by_source(*batches):
    """Round-robin across sources so one feed can't take every processing slot."""
    return [e for group in zip_longest(*batches) for e in group if e is not None]

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

def _ring_centroid(ring):
    """Area-weighted (shoelace) centroid of a [lon, lat] ring. Returns (area, lon, lat)."""
    area = cx = cy = 0.0
    for p0, p1 in zip(ring, ring[1:] + ring[:1]):
        cross = p0[0] * p1[1] - p1[0] * p0[1]
        area += cross
        cx += (p0[0] + p1[0]) * cross
        cy += (p0[1] + p1[1]) * cross
    if area == 0:
        # Degenerate ring (collinear points): fall back to the vertex average
        return 0.0, sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    area /= 2
    return abs(area), cx / (6 * area), cy / (6 * area)

def _geometry_centroid(geo):
    """Return (lat, lon) for a Polygon or MultiPolygon, or None if there's no usable geometry."""
    # Planar math on lon/lat: rings crossing the antimeridian (western Alaska) give a wrong centroid
    if not geo or not geo.get("coordinates"):
        return None
    if geo.get("type") == "Polygon":
        outer_rings = [geo["coordinates"][0]]
    elif geo.get("type") == "MultiPolygon":
        outer_rings = [poly[0] for poly in geo["coordinates"] if poly]
    else:
        return None
    centroids = [_ring_centroid(r) for r in outer_rings if r]
    if not centroids:
        return None
    # For MultiPolygons, use the largest part so the point lands inside a real alert area
    _, lon, lat = max(centroids, key=lambda c: c[0])
    return lat, lon

def fetch_weather_alerts():
    try:
        url = "https://api.weather.gov/alerts/active?status=actual&message_type=alert"
        headers = {"User-Agent": "CrisisIQ/1.0 (contact@crisisiq.dev)"}
        r = requests.get(url, timeout=10, headers=headers)
        data = r.json()
        events = []
        for feature in data.get("features", [])[:8]:
            props = feature["properties"]
            centroid = _geometry_centroid(feature.get("geometry"))
            if centroid:
                lat, lon = centroid
            else:
                # Approximate: alerts without geometry only reference NWS zones
                # (affectedZones / geocode.UGC). They're placed near the center of the
                # contiguous US until zone resolution is added in a separate PR.
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