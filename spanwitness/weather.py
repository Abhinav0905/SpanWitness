"""Optional official alert context, with explicit unavailable and example states."""
from datetime import datetime, timezone
import httpx


async def nws_context(latitude: float, longitude: float) -> dict:
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Latitude or longitude is outside its valid range.")
    url = f"https://api.weather.gov/alerts/active?point={latitude:.4f},{longitude:.4f}"
    result = {"status": "unavailable", "source_kind": "live_nws", "source_url": url,
              "checked_at": datetime.now(timezone.utc).isoformat(), "fire_weather_alert": False,
              "alerts": [], "meaning": "Unavailable context does not establish low fire danger."}
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "SpanWitness/0.1 OpenCV-research-prototype", "Accept": "application/geo+json"})
            response.raise_for_status()
            features = response.json().get("features", [])
        for feature in features:
            if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
                continue
            properties = feature["properties"]
            event = properties.get("event", "")
            if event in {"Red Flag Warning", "Fire Weather Watch"}:
                result["alerts"].append({"event": event, "headline": properties.get("headline"),
                                         "expires": properties.get("expires"), "url": properties.get("@id", feature.get("id"))})
        result.update(status="available", fire_weather_alert=bool(result["alerts"]),
                      meaning="Official alert context. An absence of alerts is not an asset-specific risk assessment.")
    except (httpx.HTTPError, ValueError, TypeError):
        pass
    return result
