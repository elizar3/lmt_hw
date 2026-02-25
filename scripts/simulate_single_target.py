# scripts/simulate_single_target.py
#
# Simulates one moving target:
# - random start near Riga/Liepaja/Daugavpils
# - random speed, altitude, heading
# - sends radar report every second
# - moves target forward using same speed + heading
# - stops when intercepted (approximation) or no viable interception exists
#
# Run from repo root:
#   python scripts/simulate_single_target.py
#
# Examples:
#   python scripts/simulate_single_target.py --interval 1 --max-steps 120
#   python scripts/simulate_single_target.py --mode threat
#   python scripts/simulate_single_target.py --url http://localhost:8000/radar/report

import argparse
import random
import time
from datetime import datetime, timezone
from math import radians, sin, cos, asin, atan2, degrees

import httpx


EARTH_RADIUS_M = 6_371_000

BASES = [
    {"name": "Riga", "latitude": 56.97475845607155, "longitude": 24.1670070219384},
    {"name": "Liepaja", "latitude": 56.516083346891044, "longitude": 21.0182217849017},
    {"name": "Daugavpils", "latitude": 55.87409588616014, "longitude": 26.51864225209475},
]


def now_unix_seconds():
    return time.time()


def destination_point(lat, lon, bearing_deg, distance_m):
    """
    Move from (lat, lon) by distance_m at bearing_deg.
    Bearing: 0=north, 90=east, 180=south, 270=west.
    """
    if distance_m == 0:
        return lat, lon

    bearing_rad = radians(bearing_deg % 360)
    lat_rad = radians(lat)
    lon_rad = radians(lon)

    angular_distance = distance_m / EARTH_RADIUS_M

    dest_lat_rad = asin(
        sin(lat_rad) * cos(angular_distance)
        + cos(lat_rad) * sin(angular_distance) * cos(bearing_rad)
    )
    dest_lon_rad = lon_rad + atan2(
        sin(bearing_rad) * sin(angular_distance) * cos(lat_rad),
        cos(angular_distance) - sin(lat_rad) * sin(dest_lat_rad),
    )

    return degrees(dest_lat_rad), degrees(dest_lon_rad)


def random_start_near_base(max_offset_km=4.0, allowed_base_names=None, min_offset_km=0.0):
    """
    Pick one of the 3 bases (or a filtered subset) and generate a random start point near it.
    """
    if allowed_base_names is None:
        candidate_bases = BASES
    else:
        candidate_bases = [b for b in BASES if b["name"] in allowed_base_names]

    if not candidate_bases:
        raise ValueError("No bases available for the requested spawn filter")

    base = random.choice(candidate_bases)

    # Keep min <= max
    if min_offset_km > max_offset_km:
        min_offset_km, max_offset_km = max_offset_km, min_offset_km

    distance_m = random.uniform(min_offset_km * 1000, max_offset_km * 1000)
    bearing_deg = random.randint(0, 359)

    lat, lon = destination_point(
        base["latitude"],
        base["longitude"],
        bearing_deg,
        distance_m,
    )
    return base, lat, lon


def generate_balanced_target_profile():
    """
    Generate a target that is LIKELY to make one interceptor type the best choice.

    This is not a guarantee, but it strongly increases variety across runs.

    Profiles:
    - 50Cal
    - Interceptor drone
    - Fighter jet
    - Rocket
    """
    desired = random.choice(["50Cal", "Interceptor drone", "Fighter jet", "Rocket"])

    # Random heading for all profiles (any 0..359 is valid)
    heading_deg = random.randint(0, 359)

    # -------------------------
    # 50Cal profile
    # -------------------------
    # Make it low enough altitude and very close to a base that has 50Cal.
    # Liepaja is ideal because it has only drone + 50Cal, and 50Cal is cheaper.
    if desired == "50Cal":
        base, lat, lon = random_start_near_base(
            min_offset_km=0.05,   # 50 m
            max_offset_km=1.5,    # within 50Cal range (2 km)
            allowed_base_names=["Liepaja", "Daugavpils", "Riga"],
        )
        speed_ms = random.uniform(16, 180)      # actionable (not_threat avoided)
        altitude_m = random.uniform(200, 1800)  # within 50Cal max altitude 2000

    # -------------------------
    # Interceptor drone profile
    # -------------------------
    # Spawn near Liepaja so fighter/rocket are not available there.
    # Keep it outside 50Cal range (>2 km) but inside drone range (<30 km).
    elif desired == "Interceptor drone":
        base, lat, lon = random_start_near_base(
            min_offset_km=3.0,    # outside 50Cal range
            max_offset_km=20.0,   # inside drone range 30 km
            allowed_base_names=["Liepaja"],
        )
        speed_ms = random.uniform(16, 140)
        altitude_m = random.uniform(200, 1800)  # drone max altitude 2000

    # -------------------------
    # Fighter jet profile
    # -------------------------
    # Spawn near Riga (has fighter), high enough to exclude drone/50Cal,
    # but below fighter max altitude. Keep within fighter range.
    elif desired == "Fighter jet":
        base, lat, lon = random_start_near_base(
            min_offset_km=20.0,   # avoid cheap short-range 50Cal
            max_offset_km=120.0,  # comfortably within fighter range 350 km
            allowed_base_names=["Riga"],
        )
        speed_ms = random.uniform(60, 350)       # threat-ish, but can be any >15
        altitude_m = random.uniform(2500, 12000) # >2000 excludes drone/50Cal; <15000 fits fighter

    # -------------------------
    # Rocket profile
    # -------------------------
    # Force rocket by altitude > fighter max altitude (15000) but <= rocket max altitude.
    # Spawn near a base that has rockets.
    else:  # desired == "Rocket"
        base, lat, lon = random_start_near_base(
            min_offset_km=2.0,
            max_offset_km=60.0,  # inside rocket range 100 km
            allowed_base_names=["Riga", "Daugavpils"],
        )
        speed_ms = random.uniform(60, 400)
        altitude_m = random.uniform(16000, 28000)  # above fighter max altitude, below rocket max altitude

    target = {
        "latitude": lat,
        "longitude": lon,
        "speed_ms": round(speed_ms, 2),
        "altitude_m": round(altitude_m, 2),
        "heading_deg": heading_deg,
        "source_base_for_spawn": base["name"],
        "intended_interceptor_profile": desired,  # for visibility in printout
    }
    return target


def generate_initial_target(mode="balanced", max_offset_km=4.0):
    """
    Generate one target with random starting position near a random base.

    mode:
      - balanced : generate profile likely to favor one interceptor type (50Cal/drone/fighter/rocket)
      - mixed    : can be anything
      - caution  : speed in (15, 50]
      - threat   : speed > 50
    """
    # New balanced mode (recommended for demos)
    if mode == "balanced":
        return generate_balanced_target_profile()

    # Original behavior for other modes
    base, lat, lon = random_start_near_base(max_offset_km=max_offset_km)

    heading_deg = random.randint(0, 359)  # any heading is valid

    if mode == "caution":
        speed_ms = random.uniform(16, 50)
        altitude_m = random.uniform(200, 3000)
    elif mode == "threat":
        speed_ms = random.uniform(51, 400)
        altitude_m = random.uniform(200, 12000)
    else:
        # mixed
        speed_ms = random.uniform(0, 400)
        altitude_m = random.uniform(0, 12000)

    target = {
        "latitude": lat,
        "longitude": lon,
        "speed_ms": round(speed_ms, 2),
        "altitude_m": round(altitude_m, 2),
        "heading_deg": heading_deg,
        "source_base_for_spawn": base["name"],
        "intended_interceptor_profile": None,
    }
    return target


def build_report(target):
    """
    Convert current target state into the API request format.
    """
    return {
        "speed_ms": target["speed_ms"],
        "altitude_m": target["altitude_m"],
        "heading_deg": target["heading_deg"],
        "latitude": round(target["latitude"], 6),
        "longitude": round(target["longitude"], 6),
        "report_time": now_unix_seconds(),
    }


def move_target_forward(target, seconds):
    """
    Update target position using its constant speed and heading.
    Altitude, speed, and heading remain constant (as clarified by task owner).
    """
    distance_m = target["speed_ms"] * seconds
    new_lat, new_lon = destination_point(
        target["latitude"],
        target["longitude"],
        target["heading_deg"],
        distance_m,
    )
    target["latitude"] = new_lat
    target["longitude"] = new_lon


def send_report(url, report, timeout_s=5.0):
    """
    Send one radar report to API.
    Returns: (status_code_or_none, parsed_json_or_text)
    """
    try:
        response = httpx.post(url, json=report, timeout=timeout_s)
        try:
            body = response.json()
        except Exception:
            body = response.text
        return response.status_code, body
    except Exception as e:
        return None, f"Request failed: {e}"


def print_step(step_no, target, report, status_code, result):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    print("=" * 90)
    print(f"[{ts}] Step {step_no}")
    print(
        "Target state:",
        {
            "spawned_near": target["source_base_for_spawn"],
            "intended_profile": target.get("intended_interceptor_profile"),
            "lat": round(target["latitude"], 6),
            "lon": round(target["longitude"], 6),
            "speed_ms": target["speed_ms"],
            "altitude_m": target["altitude_m"],
            "heading_deg": target["heading_deg"],
        },
    )
    print("Radar report:", report)

    print("API response:")
    if status_code is None:
        print(result)
        return

    print(f"HTTP {status_code}")

    if isinstance(result, dict):
        print(
            {
                "classification": result.get("classification"),
                "decision": result.get("decision"),
                "reason": result.get("reason"),
            }
        )
    else:
        print(result)


def should_stop(result, interval_s):
    """
    Decide whether the simulation should stop.

    Rules (simple and practical):
    - If no decision for a non-not_threat target => outside reach / no viable option
    - If decision exists and intercept_time_s <= interval => treat as intercepted before next radar tick
    """
    if not isinstance(result, dict):
        return False, None

    classification = result.get("classification")
    decision = result.get("decision")

    # If API says no action needed because not_threat, we can keep running OR stop.
    # Here we keep running only if the user started a "mixed" target and wants to observe.
    # For simplicity, we stop because the track is not actionable.
    if classification == "not_threat":
        return True, "Target classified as not_threat."

    if decision is None:
        return True, "No viable interception option found."

    intercept_time_s = decision.get("intercept_time_s")
    if isinstance(intercept_time_s, (int, float)) and intercept_time_s <= interval_s:
        return True, f"Predicted interception in <= {interval_s}s (treated as intercepted)."

    return False, None


def reset_engagement(url_base="http://localhost:8000", timeout_s=5.0):
    try:
        response = httpx.post(f"{url_base}/engagement/reset", timeout=timeout_s)
        try:
            body = response.json()
        except Exception:
            body = response.text
        return response.status_code, body
    except Exception as e:
        return None, f"Reset failed: {e}"


def main():
    parser = argparse.ArgumentParser(description="Simulate one moving radar target and report every second.")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/radar/report",
        help="Radar API endpoint (default: http://localhost:8000/radar/report)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between radar reports (default: 1.0)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=120,
        help="Maximum number of reports to send before stopping (default: 120)",
    )
    parser.add_argument(
        "--max-offset-km",
        type=float,
        default=4.0,
        help="Spawn target within this many km of a random base (default: 4)",
    )
    parser.add_argument(
        "--mode",
        choices=["balanced", "mixed", "caution", "threat"],
        default="balanced",
        help="Target generation mode (default: balanced)",
    )

    args = parser.parse_args()

    # Generate one target and keep its speed/heading/altitude constant
    target = generate_initial_target(mode=args.mode, max_offset_km=args.max_offset_km)

    # Try to reset API engagement state before a new simulation run
    base_url = args.url.rsplit("/radar/report", 1)[0]
    reset_status, reset_body = reset_engagement(base_url)
    print("Engagement reset:", reset_status, reset_body)

    print("Starting single-target simulation")
    print(f"API URL: {args.url}")
    print(f"Interval: {args.interval}s | Max steps: {args.max_steps}")
    print(f"Spawn radius: {args.max_offset_km} km | Mode: {args.mode}")
    print("Target keeps constant speed, heading, and altitude.")
    print("Press Ctrl+C to stop.\n")

    try:
        for step in range(1, args.max_steps + 1):
            report = build_report(target)
            status_code, result = send_report(args.url, report)

            print_step(step, target, report, status_code, result)

            # Stop if intercepted (approx) or no viable option
            if status_code == 200:
                stop, reason = should_stop(result, args.interval)
                if stop:
                    print("\nSimulation stopped:", reason)
                    break

            # Move target for the next radar tick
            move_target_forward(target, args.interval)

            # Wait until next report
            if step < args.max_steps:
                time.sleep(args.interval)
        else:
            print("\nSimulation stopped: reached max steps.")

    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    main()