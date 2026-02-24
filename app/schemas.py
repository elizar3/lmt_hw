from typing import Optional
from pydantic import BaseModel

# radar input (one report)
class RadarReport(BaseModel):
    speed_ms: float
    altitude_m: float
    heading_deg: float
    latitude: float
    longitude: float
    report_time: float

class InterceptDecision(BaseModel):
    # system choice
    base: str
    interceptor: str

    # predicted interception point
    intercept_latitude: float
    intercept_longitude: float

    # debug fields
    intercept_time_s: float
    interceptor_travel_distance_m: float
    estimated_cost_eur: float

class DecisionResponse(BaseModel):
    # overall result for one radar report
    classification: str
    decision: Optional[InterceptDecision] = None
    reason: str