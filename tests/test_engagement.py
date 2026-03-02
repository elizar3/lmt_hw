# AI

from app.engagement_state import clear_active_engagement, get_active_engagement
from app.logic.engagement import process_radar_report_with_engagement


# Same base/interceptor setup as the rest of the project tests

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
    "Daugavpils": [INTERCEPTOR_DRONE, ROCKET, CAL_50],
    "Liepaja": [INTERCEPTOR_DRONE, CAL_50],
}


def setup_function():
    """
    Clear in-memory engagement state before each test.
    """
    clear_active_engagement()


def teardown_function():
    """
    Clear in-memory engagement state after each test too,
    so tests stay independent.
    """
    clear_active_engagement()


def make_report(report_time):
    """
    One stable test target:
    - near Riga
    - altitude above drone/50Cal limit
    - inside fighter jet limits
    - should create a real engagement with non-zero intercept time
    """
    return {
        "speed_ms": 100,
        "altitude_m": 5000,
        "heading_deg": 90,
        "latitude": 56.95,
        "longitude": 24.0,
        "report_time": report_time,
    }


def test_first_actionable_report_launches_interceptor():
    report = make_report(report_time=1000.0)

    result = process_radar_report_with_engagement(report, BASES, INVENTORY)

    assert result["classification"] == "threat"
    assert result["decision"] is not None
    assert result["action"] == "launch"

    active = get_active_engagement()
    assert active is not None
    assert active["status"] == "engaged"
    assert active["base"] == result["decision"]["base"]
    assert active["interceptor"] == result["decision"]["interceptor"]


def test_second_report_tracks_existing_engagement_instead_of_launching_new_one():
    first_report = make_report(report_time=1000.0)
    first_result = process_radar_report_with_engagement(first_report, BASES, INVENTORY)

    assert first_result["action"] == "launch"

    # Send same target again 1 second later
    second_report = make_report(report_time=1001.0)
    second_result = process_radar_report_with_engagement(second_report, BASES, INVENTORY)

    assert second_result["classification"] == "threat"
    assert second_result["decision"] is not None
    assert second_result["action"] == "tracking_existing"

    # Should still be the same interceptor/base as the original launch
    assert second_result["decision"]["base"] == first_result["decision"]["base"]
    assert second_result["decision"]["interceptor"] == first_result["decision"]["interceptor"]

    # Remaining time should be smaller than original predicted time
    assert second_result["decision"]["intercept_time_s"] < first_result["decision"]["intercept_time_s"]


def test_engagement_eventually_becomes_intercepted_after_predicted_time_passes():
    first_report = make_report(report_time=1000.0)
    first_result = process_radar_report_with_engagement(first_report, BASES, INVENTORY)

    assert first_result["action"] == "launch"
    original_intercept_time = first_result["decision"]["intercept_time_s"]

    # Send another report after the predicted intercept time has passed
    later_report = make_report(report_time=1000.0 + original_intercept_time + 1.0)
    later_result = process_radar_report_with_engagement(later_report, BASES, INVENTORY)

    assert later_result["classification"] == "threat"
    assert later_result["decision"] is not None
    assert later_result["action"] == "intercepted"

    # After interception, active engagement should be cleared
    assert get_active_engagement() is None


def test_not_threat_clears_existing_engagement():
    first_report = make_report(report_time=1000.0)
    first_result = process_radar_report_with_engagement(first_report, BASES, INVENTORY)

    assert first_result["action"] == "launch"
    assert get_active_engagement() is not None

    # Low speed => not_threat
    not_threat_report = {
        "speed_ms": 10,
        "altitude_m": 500,
        "heading_deg": 90,
        "latitude": 56.95,
        "longitude": 24.0,
        "report_time": 1001.0,
    }

    result = process_radar_report_with_engagement(not_threat_report, BASES, INVENTORY)

    assert result["classification"] == "not_threat"
    assert result["decision"] is None
    assert result["action"] == "no_action"
    assert get_active_engagement() is None


def test_tracking_response_shows_interceptor_altitude_progress_if_available():
    first_report = make_report(report_time=1000.0)
    first_result = process_radar_report_with_engagement(first_report, BASES, INVENTORY)

    assert first_result["action"] == "launch"

    second_report = make_report(report_time=1001.0)
    second_result = process_radar_report_with_engagement(second_report, BASES, INVENTORY)

    assert second_result["action"] == "tracking_existing"
    assert second_result["decision"] is not None

    # If you added altitude tracking fields, check them.
    # If these fields are not implemented yet, you can remove this test.
    assert "current_interceptor_altitude_m" in second_result["decision"]
    assert "intercept_altitude_m" in second_result["decision"]

    current_alt = second_result["decision"]["current_interceptor_altitude_m"]
    target_alt = second_result["decision"]["intercept_altitude_m"]

    assert current_alt >= 0
    assert target_alt >= 0
    assert current_alt <= target_alt