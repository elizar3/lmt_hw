# AI
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from app.schemas import RadarReport, DecisionResponse
from app.logic.decision import choose_interception

from app.db import get_db
from app.repo import load_bases_and_inventory

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
    result = choose_interception(report_dict, bases, inventory)
    return result