# AI
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.schemas import RadarReport, DecisionResponse
from app.db import get_db
from app.repo import load_bases_and_inventory
from app.engagement_state import clear_active_engagement, get_active_engagement
from app.logic.engagement import process_radar_report_with_engagement

app = FastAPI(title="Threat Classification & Interception API")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/debug/db-data")
def debug_db_data(db: Session = Depends(get_db)):
    bases, inventory = load_bases_and_inventory(db)
    return {"bases": bases, "inventory": inventory}

@app.post("/radar/report", response_model=DecisionResponse)
def radar_report(report: RadarReport):
    report_dict = report.model_dump()
    bases, inventory = load_bases_and_inventory(next(get_db()))
    result = process_radar_report_with_engagement(report_dict, bases, inventory)
    return result

@app.post("/engagement/reset")
def reset_engagement():
    clear_active_engagement()
    return {"status": "ok", "message": "Active engagement cleared."}


@app.get("/engagement/active")
def get_engagement_active():
    active = get_active_engagement()
    return {"active_engagement": active}