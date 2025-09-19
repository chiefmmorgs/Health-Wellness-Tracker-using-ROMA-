from dotenv import load_dotenv
from pathlib import Path
import os, sys, json, traceback
from typing import Optional, Dict, Any

# ---- Load .env from the REPO ROOT ----
_here = Path(__file__).resolve()
_root = _here.parent
load_dotenv(dotenv_path=_root / ".env")

# ---- CRITICAL: Set up LiteLLM/OpenRouter BEFORE any imports ----
# This ensures ROMA uses OpenRouter instead of OpenAI
openrouter_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_key:
    print("WARNING: OPENROUTER_API_KEY not set. Please add it to your .env file")
    print("Get your free API key at: https://openrouter.ai/keys")
    sys.exit(1)

# Set up LiteLLM configuration for OpenRouter
os.environ["LITELLM_API_KEY"] = openrouter_key
os.environ["LITELLM_API_BASE"] = "https://openrouter.ai/api/v1"
os.environ["OPENROUTER_BASE_URL"] = "https://openrouter.ai/api/v1"

# Force OpenRouter as default provider
os.environ["AGNO_DEFAULT_PROVIDER"] = "openrouter"
os.environ["AGNO_DEFAULT_MODEL"] = "openrouter/deepseek/deepseek-chat"

# IMPORTANT: Set a dummy OpenAI key to prevent errors
os.environ["OPENAI_API_KEY"] = "sk-dummy-key-for-openrouter"

# ---- FastAPI app with simple local agents ----
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import your local health runner
from roma_engine.runner import HealthRunner

app = FastAPI(title="Health Wellness Tracker", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# Use your local HealthRunner instead of ROMA's runner
runner = HealthRunner()

class HealthEntry(BaseModel):
    meal_log: Optional[str] = Field(None, example="Rice and beans for lunch")
    exercise_log: Optional[str] = Field(None, example="20 min walk")
    sleep_log: Optional[str] = Field(None, example="6h")
    mood_log: Optional[str] = Field(None, example="Tired")
    water_intake_l: Optional[float] = Field(None, example=2.5)
    extras: Optional[Dict[str, Any]] = None

class AnalysisOut(BaseModel):
    analysis: Dict[str, Any]

@app.get("/")
def health():
    return {
        "status": "ok",
        "endpoints": {
            "/": "Health check",
            "/version": "System info",
            "/analyze": "Analyze health entry (POST)",
            "/weekly-report": "Generate weekly report (POST)",
            "/example": "Get example payload"
        }
    }

@app.get("/version")
def version():
    return {
        "cwd": str(Path.cwd()),
        "repo_root": str(_root),
        "openrouter_key_set": bool(os.environ.get("OPENROUTER_API_KEY")),
        "provider": os.getenv("AGNO_DEFAULT_PROVIDER"),
        "model": os.getenv("AGNO_DEFAULT_MODEL"),
        "dummy_openai_key_set": bool(os.environ.get("OPENAI_API_KEY")),
    }

@app.get("/example")
def example():
    """Ready-to-use example payload for /weekly-report"""
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
                "date": "2025-09-15",
                "sleep_hours": 6.8,
                "steps": 7200,
                "workouts": [{"type": "push", "minutes": 35, "intensity_1_5": 3}],
                "calories_in": 2550,
                "water_liters": 2.0,
                "mood_1_5": 3,
                "notes": "desk day",
            },
            {
                "date": "2025-09-16",
                "sleep_hours": 7.1,
                "steps": 8100,
                "workouts": [],
                "calories_in": 2450,
                "water_liters": 2.3,
                "mood_1_5": 4,
                "notes": "light walk",
            },
            {
                "date": "2025-09-17",
                "sleep_hours": 7.8,
                "steps": 9500,
                "workouts": [{"type": "cardio", "minutes": 25, "intensity_1_5": 4}],
                "calories_in": 2300,
                "water_liters": 2.8,
                "mood_1_5": 5,
                "notes": "great day",
            }
        ],
    }

@app.post("/weekly-report")
async def weekly_report(payload: Dict[str, Any] = Body(...)):
    """Generate weekly health report using local agents"""
    try:
        # Use your local HealthRunner
        result = runner.run(payload)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "trace_tail": tb[-1000:],
            },
        )

@app.post("/analyze", response_model=AnalysisOut)
async def analyze_entry(entry: HealthEntry = Body(...)):
    """Simple analysis of a single health entry"""
    data = entry.model_dump(exclude_none=True)
    
    # Convert single entry to weekly format for the runner
    daily_log = {
        "date": "2025-09-19",
        "sleep_hours": None,
        "steps": None,
        "workouts": [],
        "calories_in": None,
        "water_liters": entry.water_intake_l,
        "mood_1_5": None,
        "notes": ""
    }
    
    # Parse the logs
    if entry.sleep_log:
        try:
            hours = float(entry.sleep_log.replace('h', '').strip())
            daily_log["sleep_hours"] = hours
        except:
            pass
    
    if entry.exercise_log:
        daily_log["workouts"] = [{"type": "general", "minutes": 20, "intensity_1_5": 3}]
    
    if entry.mood_log:
        mood_map = {"tired": 2, "ok": 3, "good": 4, "great": 5}
        daily_log["mood_1_5"] = mood_map.get(entry.mood_log.lower(), 3)
        daily_log["notes"] = entry.mood_log
    
    # Create a minimal payload for the runner
    payload = {
        "user_profile": {
            "age": 30,  # Default values
            "sex": "U",
            "height_cm": 170,
            "weight_kg": 70,
            "goal": "maintain",
        },
        "targets": {
            "sleep_h": 8,
            "steps": 8000,
            "workouts_per_week": 3,
            "calories_in": 2000,
            "water_liters": 2.5,
        },
        "daily_logs": [daily_log]
    }
    
    try:
        result = runner.run(payload)
        
        # Create a simplified analysis
        analysis = {
            "daily_summary": {
                "logged_items": list(data.keys()),
                "sleep": f"{daily_log['sleep_hours']}h" if daily_log['sleep_hours'] else "not logged",
                "activity": "logged" if daily_log['workouts'] else "not logged",
                "hydration": f"{daily_log['water_liters']}L" if daily_log['water_liters'] else "not logged",
            },
            "recommendations": result.get("next_actions", ["Log more data for better insights"]),
            "status": result.get("status", "ok")
        }
        
        return {"analysis": analysis}
    except Exception as e:
        return {"analysis": {"error": str(e), "status": "error"}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
