# api.py — full replacement

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, List
from roma_engine.runner import HealthRunner

# Dev-friendly docs ON; safe to disable in prod by setting openapi_url=None
app = FastAPI(
    title="Health Tracker API",
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
)

runner = HealthRunner()


class Payload(BaseModel):
    user_profile: Dict[str, Any]
    targets: Dict[str, Any]
    daily_logs: List[Dict[str, Any]]


@app.get("/")
def home():
    return {
        "name": "Health Tracker",
        "docs": "/docs",
        "report_endpoint": "/weekly-report",
        "example_endpoint": "/example",
        "healthcheck": "/health",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/example")
def example():
    # Ready-to-use example payload you can paste into /weekly-report
    return {
        "user_profile": {
            "age": 28,
            "sex": "M",
            "height_cm": 177,
            "weight_kg": 79,
            "goal": "fat loss",
            "constraints": "knee pain on runs",
        },
        "targets": {
            "sleep_h": 7.5,
            "steps": 9000,
            "workouts_per_week": 3,
            "calories_in": 2400,
            "water_liters": 2.5,
        },
        "daily_logs": [
            {
                "date": "2025-09-08",
                "sleep_hours": 6.8,
                "steps": 7200,
                "workouts": [{"type": "push", "minutes": 35, "intensity_1_5": 3}],
                "calories_in": 2550,
                "water_liters": 2.0,
                "mood_1_5": 3,
                "notes": "desk day",
            },
            {
                "date": "2025-09-09",
                "sleep_hours": 7.1,
                "steps": 8100,
                "workouts": [],
                "calories_in": 2450,
                "water_liters": 2.3,
                "mood_1_5": 4,
                "notes": "light walk",
            },
        ],
    }


@app.post("/weekly-report")
def weekly_report(payload: Payload):
    # Hand off to ROMA runner; returns the final structured report JSON
    return runner.run(payload.dict())


