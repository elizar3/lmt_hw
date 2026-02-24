# AI

# API tests for FastAPI endpoints.
# These tests DO NOT use the real MySQL database.
# Instead, we "mock" (replace) the DB-loading function so tests stay simple and fast.

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app, get_db


# -------------------------
# Test data (same structure as your real app uses)
# -------------------------

TEST_BASES = [
    {"name": "Riga", "latitude": 56.97475845607155, "longitude": 24.1670070219384},
    {"name": "Liepaja", "latitude": 56.516083346891044, "longitude": 21.0182217849017},
    {"name": "Daugavpils", "latitude": 55.87409588616014, "longitude": 26.51864225209475},
]

INTERCEPTOR_DRONE = {
    "name": "Interceptor drone",
    "speed_ms": 80,
    "range_m": 30000,
    "max_altitude_m": 2000,
    "cost_model": "fixed",
    "cost_value_eur": 10000,
}

FIGHTER_JET = {
    "name": "Fighter jet",
    "speed_ms": 700,
    "range_m": 3500,
    "max_altitude_m": 15000,
    "cost_model": "per_minute",
    "cost_value_eur": 1000,
}

ROCKET = {
    "name": "Rocket",
    "speed_ms": 1500,
    "range_m": 100000,
    "max_altitude_m": 30000,
    "cost_model": "fixed",
    "cost_value_eur": 300000,
}

CAL_50 = {
    "name": "50Cal",
    "speed_ms": 900,
    "range_m": 2000,
    "max_altitude_m": 2000,
    "cost_model": "per_shot",
    "cost_value_eur": 1,
}

TEST_INVENTORY = {
    "Riga": [INTERCEPTOR_DRONE, FIGHTER_JET, ROCKET, CAL_50],
    "Daugavpils": [INTERCEPTOR_DRONE, ROCKET, CAL_50],
    "Liepaja": [INTERCEPTOR_DRONE, CAL_50],
}


# -------------------------
# Helpers for test setup
# -------------------------

class DummyDB:
    """
    Fake DB object.
    We do not use it directly, but FastAPI expects something from the DB dependency.
    """
    pass


def override_get_db():
    """
    Replace the real DB session dependency with a fake object.
    This prevents tests from trying to connect to MySQL.
    """
    yield DummyDB()


def fake_load_bases_and_inventory(_db):
    """
    Replace the repository function that normally reads from MySQL.
    Returns fixed test data instead.
    """
    return TEST_BASES, TEST_INVENTORY


def setup_test_app(monkeypatch):
    """
    Prepare the app for API tests:
    1) Override DB dependency
    2) Replace DB-reading function with fake data
    3) Return TestClient
    """
    # Replace FastAPI dependency (DB session)
    app.dependency_overrides[get_db] = override_get_db

    # Replace the function imported in app.main
    monkeypatch.setattr(main_module, "load_bases_and_inventory", fake_load_bases_and_inventory)

    return TestClient(app)


# -------------------------
# Tests
# -------------------------

def test_health_endpoint(monkeypatch):
    """
    Very simple smoke test:
    confirms the API process is alive.
    """
    client = setup_test_app(monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_debug_db_data_endpoint_returns_stubbed_data(monkeypatch):
    """
    Checks that the debug endpoint returns the fake data from our mocked repo.
    This proves the route wiring works.
    """
    client = setup_test_app(monkeypatch)

    response = client.get("/debug/db-data")

    assert response.status_code == 200

    data = response.json()
    assert "bases" in data
    assert "inventory" in data

    # Basic shape checks
    assert len(data["bases"]) == 3
    assert "Riga" in data["inventory"]
    assert "Liepaja" in data["inventory"]
    assert "Daugavpils" in data["inventory"]


def test_radar_report_not_threat_returns_no_decision(monkeypatch):
    """
    If speed < 15 OR altitude < 200, classification should be not_threat.
    In that case, decision should be None.
    """
    client = setup_test_app(monkeypatch)

    payload = {
        "speed_ms": 10,  # below 15 => not_threat
        "altitude_m": 500,
        "heading_deg": 90,
        "latitude": 56.516083346891044,
        "longitude": 21.0182217849017,
        "report_time": 0,
    }

    response = client.post("/radar/report", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert data["classification"] == "not_threat"
    assert data["decision"] is None
    assert "reason" in data


def test_radar_report_caution_near_liepaja_returns_decision(monkeypatch):
    """
    A moving target near Liepaja at low altitude should usually be interceptable.
    We check that:
    - classification is caution
    - a decision exists
    - response includes the expected fields
    """
    client = setup_test_app(monkeypatch)

    payload = {
        "speed_ms": 20,   # >15 and <=50 => caution
        "altitude_m": 500,
        "heading_deg": 45,
        "latitude": 56.516083346891044,
        "longitude": 21.0182217849017,
        "report_time": 0,
    }

    response = client.post("/radar/report", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert data["classification"] == "caution"
    assert data["decision"] is not None

    decision = data["decision"]

    # Check required fields (don't over-test exact values here)
    assert "base" in decision
    assert "interceptor" in decision
    assert "intercept_latitude" in decision
    assert "intercept_longitude" in decision
    assert "intercept_time_s" in decision
    assert "interceptor_travel_distance_m" in decision
    assert "estimated_cost_eur" in decision

    # Sanity checks
    assert decision["intercept_time_s"] >= 0
    assert decision["interceptor_travel_distance_m"] >= 0
    assert decision["estimated_cost_eur"] >= 0


def test_radar_report_invalid_payload_returns_422(monkeypatch):
    """
    FastAPI + Pydantic should reject invalid request bodies.
    Here we omit a required field (heading_deg).
    """
    client = setup_test_app(monkeypatch)

    invalid_payload = {
        "speed_ms": 20,
        "altitude_m": 500,
        # "heading_deg" missing
        "latitude": 56.5,
        "longitude": 21.0,
        "report_time": 0,
    }

    response = client.post("/radar/report", json=invalid_payload)

    assert response.status_code == 422