from enum import Enum

class ThreatLevel(str, Enum):
    NOT_THREAT = "not_threat"
    POTENTIAL_THREAT = "potential_threat"
    CAUTION = "caution"
    THREAT = "threat"

def classify_threat(speed_ms, altitude_m):
    if speed_ms < 15 or altitude_m < 200:
        return ThreatLevel.NOT_THREAT
    elif speed_ms > 50:
        return ThreatLevel.THREAT
    elif speed_ms > 15:
        return ThreatLevel.CAUTION
    else:
        return ThreatLevel.POTENTIAL_THREAT
