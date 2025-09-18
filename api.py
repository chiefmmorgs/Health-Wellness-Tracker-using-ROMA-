from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, List
from app import run_pipeline

app = FastAPI(title="Health Tracker API")

class Payload(BaseModel):
    user_profile: Dict[str, Any]
    targets: Dict[str, Any]
    daily_logs: List[Dict[str, Any]]

@app.get("/")
def home():
    return {
        "name": "ROMA Health Tracker",
        "docs": "/docs",
        "report_endpoint": "/weekly-report"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/example")
def example():
    return {
      "user_profile": {"age": 28, "sex": "M", "height_cm": 177, "weight_kg": 79, "goal": "fat loss"},
      "targets": {"sleep_h": 7.5, "steps": 9000, "workouts_per_week": 3, "calories_in": 2400, "water_liters": 2.5},
      "daily_logs": [
        {"date": "2025-09-08", "sleep_hours": 6.8, "steps": 7200,
         "workouts": [{"type":"push","minutes":35,"intensity_1_5":3}],
         "calories_in": 2550, "water_liters": 2.0},
        {"date": "2025-09-09", "sleep_hours": 7.1, "steps": 8100,
         "workouts": [], "calories_in": 2450, "water_liters": 2.3}
      ]
    }

@app.post("/weekly-report")
def weekly_report(payload: Payload):
    return run_pipeline(payload.dict())

