# AI

import math

from app.logic.decision import (
    target_velocity_xy,
    solve_intercept_time_s,
    estimate_cost_eur,
    evaluate_candidate,
    choose_interception,
)


# --- Shared Latvia data (matching your task) ---

BASES = [
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
    "range_m": 350000,
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

INVENTORY = {
    "Riga": [INTERCEPTOR_DRONE, FIGHTER_JET, ROCKET, CAL_50],
    "Daugavpils": [INTERCEPTOR_DRONE, ROCKET, CAL_50],  # no fighter jet
    "Liepaja": [INTERCEPTOR_DRONE, CAL_50],             # only drone + 50Cal
}


# --- Unit tests for helper functions ---

def test_target_velocity_xy_cardinal_headings():
    vx, vy = target_velocity_xy(100, 0)   # north
    assert math.isclose(vx, 0.0, abs_tol=1e-9)
    assert math.isclose(vy, 100.0, abs_tol=1e-9)

    vx, vy = target_velocity_xy(100, 90)  # east
    assert math.isclose(vx, 100.0, abs_tol=1e-9)
    assert math.isclose(vy, 0.0, abs_tol=1e-9)

    vx, vy = target_velocity_xy(100, 180)  # south
    assert math.isclose(vx, 0.0, abs_tol=1e-9)
    assert math.isclose(vy, -100.0, abs_tol=1e-9)

    vx, vy = target_velocity_xy(100, 270)  # west
    assert math.isclose(vx, -100.0, abs_tol=1e-9)
    assert math.isclose(vy, 0.0, abs_tol=1e-9)


def test_solve_intercept_time_stationary_target():
    # Target is 1000 m away, not moving; interceptor 100 m/s => 10 s
    t = solve_intercept_time_s(
        target_x=1000,
        target_y=0,
        target_z=0,
        target_vx=0,
        target_vy=0,
        target_vz=0,
        interceptor_speed_ms=100,
    )
    assert t is not None
    assert math.isclose(t, 10.0, rel_tol=1e-9)


def test_solve_intercept_time_target_too_fast_moving_away():
    # Target is ahead and moving away faster than interceptor => impossible
    t = solve_intercept_time_s(
        target_x=1000,
        target_y=0,
        target_z=0,
        target_vx=100,
        target_vy=0,
        target_vz=0,
        interceptor_speed_ms=50,
    )
    assert t is None


def test_solve_intercept_time_target_already_at_base():
    t = solve_intercept_time_s(
        target_x=0,
        target_y=0,
        target_z=0,
        target_vx=25,
        target_vy=10,
        target_vz=0,
        interceptor_speed_ms=80,
    )
    assert t == 0.0


def test_estimate_cost_models():
    assert estimate_cost_eur(INTERCEPTOR_DRONE, 10) == 10000
    assert estimate_cost_eur(ROCKET, 1) == 300000

    # Fighter jet per started minute
    assert estimate_cost_eur(FIGHTER_JET, 1) == 1000
    assert estimate_cost_eur(FIGHTER_JET, 60) == 1000
    assert estimate_cost_eur(FIGHTER_JET, 61) == 2000

    # 50Cal per shot with default burst_shots=100
    assert estimate_cost_eur(CAL_50, 5) == 100
    assert estimate_cost_eur(CAL_50, 5, burst_shots=10) == 10


# --- Unit tests for evaluate_candidate ---

def test_evaluate_candidate_rejects_altitude_too_high():
    base = {"name": "TestBase", "latitude": 56.0, "longitude": 24.0}
    interceptor = {
        "name": "Low ceiling",
        "speed_ms": 100,
        "range_m": 10000,
        "max_altitude_m": 500,
        "cost_model": "fixed",
        "cost_value_eur": 1,
    }
    report = {
        "speed_ms": 20,
        "altitude_m": 1000,   # too high
        "heading_deg": 90,
        "latitude": 56.0,
        "longitude": 24.0,
        "report_time": 0,
    }

    assert evaluate_candidate(base, interceptor, report) is None


def test_evaluate_candidate_stationary_target_intercept_point_is_current_target():
    # Target stationary, so intercept point should equal report lat/lon
    base = {"name": "NearbyBase", "latitude": 56.001, "longitude": 24.0}
    interceptor = {
        "name": "Test interceptor",
        "speed_ms": 100,
        "range_m": 10000,
        "max_altitude_m": 5000,
        "cost_model": "fixed",
        "cost_value_eur": 123,
    }
    report = {
        "speed_ms": 0,          # stationary target
        "altitude_m": 500,
        "heading_deg": 90,
        "latitude": 56.0,
        "longitude": 24.0,
        "report_time": 0,
    }

    candidate = evaluate_candidate(base, interceptor, report)
    assert candidate is not None
    assert candidate["base"] == "NearbyBase"
    assert candidate["interceptor"] == "Test interceptor"
    assert math.isclose(candidate["intercept_lat"], report["latitude"], abs_tol=1e-9)
    assert math.isclose(candidate["intercept_lon"], report["longitude"], abs_tol=1e-9)
    assert candidate["interceptor_travel_distance_m"] > 0
    assert candidate["estimated_cost_eur"] == 123


def test_evaluate_candidate_rejects_when_interceptor_cannot_catch_up():
    # Base is west of target; target moves east faster than interceptor => impossible
    base = {"name": "WestBase", "latitude": 0.0, "longitude": -0.01}
    interceptor = {
        "name": "Slow interceptor",
        "speed_ms": 20,
        "range_m": 100000,
        "max_altitude_m": 5000,
        "cost_model": "fixed",
        "cost_value_eur": 1,
    }
    report = {
        "speed_ms": 50,          # faster than interceptor
        "altitude_m": 500,
        "heading_deg": 90,       # moving east, away from WestBase
        "latitude": 0.0,
        "longitude": 0.0,
        "report_time": 0,
    }

    assert evaluate_candidate(base, interceptor, report) is None


# --- Integration-ish tests for choose_interception ---

def test_choose_interception_not_threat_returns_no_decision():
    report = {
        "speed_ms": 10,        # < 15 => not_threat
        "altitude_m": 500,
        "heading_deg": 90,
        "latitude": 56.516083346891044,
        "longitude": 21.0182217849017,
        "report_time": 0,
    }

    result = choose_interception(report, BASES, INVENTORY)

    assert result["classification"] == "not_threat"
    assert result["decision"] is None


def test_choose_interception_liepaja_close_target_prefers_50cal():
    # At Liepaja base coordinates, 50Cal is feasible and cheapest (100 EUR assumed burst)
    report = {
        "speed_ms": 20,       # caution
        "altitude_m": 500,    # within 50Cal altitude
        "heading_deg": 45,
        "latitude": 56.516083346891044,
        "longitude": 21.0182217849017,
        "report_time": 0,
    }

    result = choose_interception(report, BASES, INVENTORY)

    assert result["classification"] == "caution"
    assert result["decision"] is not None
    assert result["decision"]["base"] == "Liepaja"
    assert result["decision"]["interceptor"] == "50Cal"
    assert result["decision"]["estimated_cost_eur"] == 100.0


def test_choose_interception_daugavpils_very_high_altitude_uses_local_rocket():
    # Daugavpils has no fighter jet.
    # Very high altitude removes drone + 50Cal + fighter jet (fighter max altitude 15000).
    # Rocket should be selected from Daugavpils.
    report = {
        "speed_ms": 100,
        "altitude_m": 20000,  # above fighter jet max altitude
        "heading_deg": 180,
        "latitude": 55.87409588616014,
        "longitude": 26.51864225209475,
        "report_time": 0,
    }

    result = choose_interception(report, BASES, INVENTORY)

    assert result["classification"] == "threat"
    assert result["decision"] is not None
    assert result["decision"]["base"] == "Daugavpils"
    assert result["decision"]["interceptor"] == "Rocket"


def test_choose_interception_moving_direction_can_change_best_base():
    # Synthetic scenario to prove movement matters:
    # target starts in the middle, moves EAST.
    # East base is ahead of target; West base is behind.
    # Same interceptor cost/speed/range at both bases => East should win by faster intercept time.
    bases = [
        {"name": "West", "latitude": 0.0, "longitude": -0.01},
        {"name": "East", "latitude": 0.0, "longitude": 0.01},
    ]

    same_interceptor = {
        "name": "Cheap interceptor",
        "speed_ms": 120,
        "range_m": 100000,
        "max_altitude_m": 5000,
        "cost_model": "fixed",
        "cost_value_eur": 1000,
    }

    inventory = {
        "West": [same_interceptor],
        "East": [same_interceptor],
    }

    report = {
        "speed_ms": 100,      # moving target
        "altitude_m": 1000,
        "heading_deg": 90,    # east
        "latitude": 0.0,
        "longitude": 0.0,
        "report_time": 0,
    }

    result = choose_interception(report, bases, inventory)

    assert result["classification"] == "threat"
    assert result["decision"] is not None
    assert result["decision"]["base"] == "East"
    assert result["decision"]["interceptor"] == "Cheap interceptor"