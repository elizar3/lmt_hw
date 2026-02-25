from app.engagement_state import get_active_engagement, set_active_engagement, clear_active_engagement
from app.logic.classify import classify_threat, ThreatLevel
from app.logic.decision import choose_interception


def process_radar_report_with_engagement(report, bases, inventory):
    # 1. classify current report
    classification = classify_threat(report["speed_ms"], report["altitude_m"])

    # 2. if not threat, clear any existing engagement
    if classification == ThreatLevel.NOT_THREAT:
        clear_active_engagement()
        return {
            "classification": classification.value,
            "decision": None,
            "reason": "Target classified as not a threat.",
            "action": "no_action",
        }

    # 3. check if interceptor already active
    active = get_active_engagement()

    if active is not None and active.get("status") == "engaged":
        # how much time since launch
        elapsed_s = report["report_time"] - active["launch_time"]

        # protect against weird timestamps
        if elapsed_s < 0:
            elapsed_s = 0

        remaining_s = active["predicted_intercept_time_s"] - elapsed_s

        # if intercept time has passed, consider target as intercepted
        if remaining_s <= 0:
            finished_decision = {
                "base": active["base"],
                "interceptor": active["interceptor"],
                "intercept_latitude": active["predicted_intercept_latitude"],
                "intercept_longitude": active["predicted_intercept_longitude"],
                "intercept_time_s": round(active["predicted_intercept_time_s"], 2),
                "interceptor_travel_distance_m": round(active["interceptor_travel_distance_m"], 2),
                "estimated_cost_eur": round(active["estimated_cost_eur"], 2),
            }

            clear_active_engagement()

            return {
                "classification": classification.value,
                "decision": finished_decision,
                "reason": "Target intercepted (predicted intercept time has passed).",
                "action": "intercepted",
            }

        # otherwise keep tracking
        total_time_s = active["predicted_intercept_time_s"]
        if total_time_s <= 0:
            progress = 1.0
        else:
            progress = elapsed_s / total_time_s

        if progress < 0:
            progress = 0
        elif progress > 1:
            progress = 1

        current_interceptor_altitude_m = progress * active["predicted_intercept_altitude_m"]

        tracking_decision = {
            "base": active["base"],
            "interceptor": active["interceptor"],
            "intercept_latitude": active["predicted_intercept_latitude"],
            "intercept_longitude": active["predicted_intercept_longitude"],
            "intercept_time_s": round(remaining_s, 2),
            "interceptor_travel_distance_m": round(active["interceptor_travel_distance_m"], 2),
            "estimated_cost_eur": round(active["estimated_cost_eur"], 2),
            "current_interceptor_altitude_m": round(current_interceptor_altitude_m, 2),
            "intercept_altitude_m": round(active["predicted_intercept_altitude_m"], 2),
        }

        return {
            "classification": classification.value,
            "decision": tracking_decision,
            "reason": "Interceptor already engaged, tracking target.",
            "action": "tracking_existing",
        }

    # 4. if no active interceptor, choose one
    result = choose_interception(report, bases, inventory)

    # if no viable options, return as-is
    if result["decision"] is None:
        result["action"] = "no_action"
        return result

    # save launch as active engagement
    decision = result["decision"]
    engagement = {
        "status": "engaged",
        "base": decision["base"],
        "interceptor": decision["interceptor"],
        "launch_time": report["report_time"],
        "predicted_intercept_time_s": float(decision["intercept_time_s"]),
        "predicted_intercept_latitude": float(decision["intercept_latitude"]),
        "predicted_intercept_longitude": float(decision["intercept_longitude"]),
        "predicted_intercept_altitude_m": float(report["altitude_m"]),
        "interceptor_travel_distance_m": float(decision["interceptor_travel_distance_m"]),
        "estimated_cost_eur": float(decision["estimated_cost_eur"]),
    }

    set_active_engagement(engagement)

    result["action"] = "launch"
    result["reason"] = "No active interceptor, launching new one based on decision."
    return result
