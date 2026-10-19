"""
Unit tests for GPS and Location Telemetry Manager
"""

import pytest
from backend.location import GPSManager


def test_gps_manager_initialization():
    mgr = GPSManager(start_lat=28.6139, start_lng=77.2090, location_name="New Delhi")
    loc = mgr.get_current_location()
    assert round(loc["lat"], 2) == 28.61
    assert round(loc["lng"], 2) == 77.21
    assert loc["location_name"] == "New Delhi"
    assert loc["is_live_device"] is False


def test_gps_manager_device_update():
    mgr = GPSManager()
    loc = mgr.update_device_location(37.7749, -122.4194, heading=90.0, speed=12.5)
    assert loc["lat"] == 37.7749
    assert loc["lng"] == -122.4194
    assert loc["heading"] == 90.0
    assert loc["is_live_device"] is True


def test_gps_manager_set_anchor():
    mgr = GPSManager()
    loc = mgr.set_anchor(19.0760, 72.8777, "Mumbai")
    assert loc["lat"] == 19.076
    assert loc["lng"] == 72.8777
    assert loc["location_name"] == "Mumbai"
    assert len(mgr.get_route_points()) >= 1


def test_gps_manager_simulation_step():
    mgr = GPSManager(start_lat=28.6139, start_lng=77.2090)
    lat1, lng1 = mgr.lat, mgr.lng
    # Advance time slightly
    mgr.last_update_time -= 1.0
    lat2, lng2 = mgr.step_simulation()
    # Should have moved forward
    assert (lat2 != lat1) or (lng2 != lng1)
