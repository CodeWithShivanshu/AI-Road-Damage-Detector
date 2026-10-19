"""
RoadVision AI - GPS & Location Telemetry Manager
Integrates Clair Google Maps API and device geolocation for route mapping and hazard tagging.
"""

import time
import math
import requests
from typing import Dict, Any, List, Tuple, Optional
from app.core.config import Settings

settings = Settings()


class GPSManager:
    """Manages vehicle GPS coordinates, route history, simulation, and Clair/Google Maps geocoding."""

    def __init__(self, start_lat: float = 28.6139, start_lng: float = 77.2090, location_name: str = "New Delhi, India"):
        self.lat = start_lat
        self.lng = start_lng
        self.heading = 45.0  # degrees (North-East)
        self.speed_kmh = 36.0  # ~10 m/s
        self.location_name = location_name
        self.last_update_time = time.time()
        self.is_manual_device_gps = False
        
        # Route path tracking: list of dicts with lat, lng, timestamp
        self.route_points: List[Dict[str, Any]] = [
            {"lat": round(self.lat, 6), "lng": round(self.lng, 6), "timestamp": time.time()}
        ]
        self.last_point_record_time = time.time()

    def set_anchor(self, lat: float, lng: float, location_name: str = "") -> Dict[str, Any]:
        """Sets a new starting location anchor (e.g., when searching a new city)."""
        self.lat = float(lat)
        self.lng = float(lng)
        if location_name:
            self.location_name = location_name
        self.route_points = [
            {"lat": round(self.lat, 6), "lng": round(self.lng, 6), "timestamp": time.time()}
        ]
        self.last_update_time = time.time()
        self.last_point_record_time = time.time()
        return self.get_current_location()

    def update_device_location(self, lat: float, lng: float, heading: Optional[float] = None, speed: Optional[float] = None) -> Dict[str, Any]:
        """Receives live GPS updates from user's smartphone or browser geolocation."""
        self.lat = float(lat)
        self.lng = float(lng)
        self.is_manual_device_gps = True
        if heading is not None:
            self.heading = float(heading)
        if speed is not None:
            self.speed_kmh = float(speed) * 3.6  # convert m/s to km/h if needed
        self.last_update_time = time.time()

        # Add point to route history every 1.5 seconds or significant distance
        now = time.time()
        if now - self.last_point_record_time >= 1.5:
            self.route_points.append({
                "lat": round(self.lat, 6),
                "lng": round(self.lng, 6),
                "timestamp": now
            })
            self.last_point_record_time = now
            if len(self.route_points) > 1000:
                self.route_points.pop(0)

        return self.get_current_location()

    def step_simulation(self) -> Tuple[float, float]:
        """Simulates smooth forward vehicle movement along a road when hardware GPS is not streaming."""
        if self.is_manual_device_gps:
            return self.lat, self.lng

        now = time.time()
        dt = min(2.0, now - self.last_update_time)
        if dt < 0.2:
            return self.lat, self.lng

        self.last_update_time = now
        # Add slight natural curvature to route
        self.heading += (math.sin(now * 0.15) * 1.8)
        rad = math.radians(self.heading)

        # 36 km/h = 10 m/s. 1 deg lat ~ 111,000 meters.
        meters_moved = (self.speed_kmh / 3.6) * dt
        d_lat = (meters_moved * math.cos(rad)) / 111000.0
        d_lng = (meters_moved * math.sin(rad)) / (111000.0 * math.cos(math.radians(self.lat)))

        self.lat += d_lat
        self.lng += d_lng

        if now - self.last_point_record_time >= 1.5:
            self.route_points.append({
                "lat": round(self.lat, 6),
                "lng": round(self.lng, 6),
                "timestamp": now
            })
            self.last_point_record_time = now
            if len(self.route_points) > 1000:
                self.route_points.pop(0)

        return self.lat, self.lng

    def get_current_location(self) -> Dict[str, Any]:
        """Returns the current GPS telemetry."""
        if not self.is_manual_device_gps:
            self.step_simulation()

        return {
            "lat": round(self.lat, 6),
            "lng": round(self.lng, 6),
            "heading": round(self.heading, 1),
            "speed_kmh": round(self.speed_kmh, 1),
            "location_name": self.location_name,
            "is_live_device": self.is_manual_device_gps,
            "route_points_count": len(self.route_points)
        }

    def get_route_points(self) -> List[Dict[str, Any]]:
        return self.route_points

    def get_hazard_location(self, cx: float = 320.0, frame_w: int = 640) -> Tuple[float, float]:
        """Calculates precise geographical coordinate for a pothole, factoring in lateral lane offset."""
        cur = self.get_current_location()
        base_lat = cur["lat"]
        base_lng = cur["lng"]
        heading = cur.get("heading", 45.0)

        norm_x = (cx - (frame_w / 2.0)) / (frame_w / 2.0) if frame_w > 0 else 0.0
        lateral_m = norm_x * 4.0

        rad_perp = math.radians(heading + 90.0)
        offset_lat = (lateral_m * math.cos(rad_perp)) / 111000.0
        offset_lng = (lateral_m * math.sin(rad_perp)) / (111000.0 * math.cos(math.radians(base_lat)))

        return round(base_lat + offset_lat, 6), round(base_lng + offset_lng, 6)

    def search_places(self, query: str, country: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Searches places using Clair Google Maps Search API.
        Falls back to OpenStreetMap Nominatim if Clair does not provide exact coordinates.
        """
        results: List[Dict[str, Any]] = []
        clean_q = query.strip()
        if not clean_q:
            return results

        # 1. Attempt Clair Google Maps Search API
        try:
            headers = {"Authorization": f"Bearer {settings.GOOGLE_MAPS_API_KEY}"}
            params = {"q": clean_q}
            if country:
                params["country"] = country

            res = requests.get(settings.CLAIR_MAPS_API_URL, headers=headers, params=params, timeout=15)
            if res.status_code == 200:
                data = res.json()
                raw_results = data.get("results", [])
                for item in raw_results:
                    lat = item.get("latitude")
                    lng = item.get("longitude")
                    if lat is not None and lng is not None:
                        results.append({
                            "title": item.get("title") or clean_q,
                            "address": item.get("address") or item.get("title") or clean_q,
                            "latitude": float(lat),
                            "longitude": float(lng),
                            "rating": item.get("rating"),
                            "source": "google_maps_clair"
                        })
        except Exception as e:
            print(f"[GPSManager] Clair API search failed: {e}")

        # 2. If no valid coordinates found via Clair, use Nominatim geocoding fallback
        if not results:
            search_terms = [clean_q]
            if " in " in clean_q.lower():
                loc_part = clean_q.lower().split(" in ")[-1].strip()
                if loc_part and loc_part not in search_terms:
                    search_terms.append(loc_part)
            elif " near " in clean_q.lower():
                loc_part = clean_q.lower().split(" near ")[-1].strip()
                if loc_part and loc_part not in search_terms:
                    search_terms.append(loc_part)

            for term in search_terms:
                if results:
                    break
                try:
                    nom_headers = {"User-Agent": "RoadVisionAI/1.0"}
                    nom_res = requests.get(
                        "https://nominatim.openstreetmap.org/search",
                        params={"q": term, "format": "json", "limit": 5},
                        headers=nom_headers,
                        timeout=5
                    )
                    if nom_res.status_code == 200:
                        for item in nom_res.json():
                            results.append({
                                "title": item.get("display_name", "").split(",")[0],
                                "address": item.get("display_name", ""),
                                "latitude": float(item.get("lat")),
                                "longitude": float(item.get("lon")),
                                "rating": None,
                                "source": "osm_nominatim"
                            })
                except Exception as e:
                    print(f"[GPSManager] Nominatim fallback search failed for '{term}': {e}")

        return results


# Global singleton instance
gps_tracker = GPSManager()
