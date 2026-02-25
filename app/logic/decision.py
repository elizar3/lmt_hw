import math
from app.logic.classify import ThreatLevel, classify_threat
from app.logic.geo import latlon_to_local_xy_m, destination_point


# convert target speed and heading to X/Y velocity (m/s)
# heading 0 = north, 90 = east, 180 = south, 270 = west
def target_velocity_xy(speed_ms, heading_deg):
    heading_rad = math.radians(heading_deg % 360)
    vx = speed_ms * math.sin(heading_rad)  # east-west
    vy = speed_ms * math.cos(heading_rad)  # north-south
    return vx, vy


# solve intercept time t (seconds) for a moving target
def solve_intercept_time_s(target_x, target_y, target_z, target_vx, target_vy, target_vz, interceptor_speed_ms):

    if interceptor_speed_ms <= 0:
        return None
    
    # AI
    # Quadratic coefficients from:
    # |target + v_target * t| = interceptor_speed * t
    a = target_vx**2 + target_vy**2 + target_vz**2 - interceptor_speed_ms**2        # target speed vs interceptor speed
    b = 2 * (target_x * target_vx + target_y * target_vy + target_z * target_vz)    # target position vs velocity
    c = target_x**2 + target_y**2 + target_z**2                                     # initial squared distance to target

    # target is at the base
    if c == 0:
        return 0.0
    
    eps = 1e-9

    # near linear case when target speed is close to interceptor speed
    if abs(a) < eps:
        if abs(b) < eps:
            return None  # no solution, target moving at interceptor speed but not towards/away
        t = -c / b
        return t if t >= 0 else None
    
    discriminant = b**2 - 4*a*c
    if discriminant < 0:
        return None  # no real solution, target too fast to intercept
    
    sqrt_disc = math.sqrt(discriminant)

    t1 = (-b - sqrt_disc) / (2*a)
    t2 = (-b + sqrt_disc) / (2*a)

    valid_times = [t for t in (t1, t2) if t >= 0]
    if not valid_times:
        return None  # both solutions are negative, interception in the past
    
    return min(valid_times)


def estimate_cost_eur(interceptor, time_to_intercept_s, burst_shots=100):
    model = interceptor["cost_model"]
    value = interceptor["cost_value_eur"]

    # drone and rocket
    if model == "fixed":
        return value
    # fighter jet
    elif model == "per_minute":
        minutes = max(1, math.ceil(time_to_intercept_s / 60))
        return value * minutes
    # 50Cal
    elif model == "per_shot":
        return value * burst_shots
    else:
        raise ValueError(f"Unknown cost model: {model}")
    

# check base+interceptor pairs against moving target
def evaluate_candidate(base, interceptor, report):

    # 1. check altitude
    if report["altitude_m"] > interceptor["max_altitude_m"]:
        return None  # cannot reach target at this altitude
    
    # 2. target velocity
    target_vx, target_vy = target_velocity_xy(report["speed_ms"], report["heading_deg"])

    # 3. base position in local XY relatove to target's current position
    target_to_base_x, target_to_base_y = latlon_to_local_xy_m(report["latitude"], report["longitude"],base["latitude"], base["longitude"])

    # base -> target vector at t=0
    rel_x = -target_to_base_x
    rel_y = -target_to_base_y
    rel_z = report["altitude_m"]
    target_vz = 0

    # 4. solve intercept time
    t = solve_intercept_time_s(rel_x, rel_y, rel_z, target_vx, target_vy, target_vz, interceptor["speed_ms"])
    if t is None:
        return None  # cannot intercept
    
    # 5. interceptor travel distance until intercept
    interceptor_travel_distance_m = interceptor["speed_ms"] * t

    # interceptor range
    if interceptor_travel_distance_m > interceptor["range_m"]:
        return None  # out of range
    
    # 6. target displacement by time t, conver to lat/lon
    target_travel_distance_m = report["speed_ms"] * t
    intercept_lat, intercept_lon = destination_point(report["latitude"], report["longitude"], report["heading_deg"], target_travel_distance_m)

    # 7. estimate cost
    estimated_cost_eur = estimate_cost_eur(interceptor, t)

    return {
        "base": base["name"],
        "interceptor": interceptor["name"],
        "intercept_time_s": t,
        "interceptor_travel_distance_m": interceptor_travel_distance_m,
        "estimated_cost_eur": estimated_cost_eur,
        "intercept_lat": intercept_lat,
        "intercept_lon": intercept_lon,
    }


# main decision function
def choose_interception(report, bases, inventory):
    classification = classify_threat(report["speed_ms"], report["altitude_m"])

    # if not a threat, do not intercept
    if classification == ThreatLevel.NOT_THREAT:
        return {
            "classification": classification.value,
            "decision": None,
            "reason": "Target classified as not a threat, no interception needed."
        }
    
    candidates = []

    # try all base+interceptor combinations
    for base in bases:
        base_name = base["name"]
        interceptors = inventory.get(base_name, [])

        for interceptor in interceptors:
            candidate = evaluate_candidate(base, interceptor, report)
            if candidate is not None:
                candidates.append(candidate)

    if not candidates:
        return {
            "classification": classification.value,
            "decision": None,
            "reason": "No viable interception options found."
        }
    
    # cheapest first, then fastest intercept, then shortest distance
    candidates.sort(key=lambda c: (c["estimated_cost_eur"], c["intercept_time_s"], c["interceptor_travel_distance_m"]))

    best = candidates[0]

    return {
        "classification": classification.value,
        "decision": {
            "base": best["base"],
            "interceptor": best["interceptor"],
            "intercept_latitude": round(best["intercept_lat"], 6),
            "intercept_longitude": round(best["intercept_lon"], 6),
            "intercept_time_s": round(best["intercept_time_s"], 2),
            "interceptor_travel_distance_m": round(best["interceptor_travel_distance_m"], 2),
            "estimated_cost_eur": round(best["estimated_cost_eur"], 2),
        },
        "reason": "Lowest cost viable interception option selected."
    }
