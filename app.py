# api.py — location-agnostic ROMA integration

from dotenv import load_dotenv
from pathlib import Path
import os, sys, importlib, inspect, pkgutil, json, traceback
from typing import Optional, Dict, Any

# ---- Load .env from the REPO ROOT (walk up until we see .git or roma-core) ----
_here = Path(__file__).resolve()
_root = _here
for _ in range(6):
    if (_root / ".git").exists() or (_root / "roma-core").exists():
        break
    _root = _root.parent
load_dotenv(dotenv_path=_root / ".env")

# ---- Force OpenRouter; block OpenAI fallback (so missing OPENAI_API_KEY never breaks) ----
os.environ.pop("OPENAI_API_KEY", None)
os.environ.setdefault("AGNO_DEFAULT_PROVIDER", "openrouter")
os.environ.setdefault("AGNO_DEFAULT_MODEL", "openrouter/deepseek/deepseek-chat-v3.1:free")
if os.getenv("OPENROUTER_API_KEY") and not os.getenv("LITELLM_API_KEY"):
    os.environ["LITELLM_API_KEY"] = os.environ["OPENROUTER_API_KEY"]
os.environ.setdefault("LITELLM_API_BASE", "https://openrouter.ai/api/v1")
os.environ.setdefault("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# ---- Make editable install optional (if not installed, add roma-core/src to sys.path) ----
roma_src = _root / "roma-core" / "src"
if roma_src.exists() and str(roma_src) not in sys.path:
    sys.path.insert(0, str(roma_src))

# ---- Import ROMA after env is set/path prepared ----
import sentientresearchagent as sra  # provided by SentientResearchAgent

def pick_runner():
    hits = []
    for _, modname, _ in pkgutil.walk_packages(sra.__path__, sra.__name__ + "."):
        if not any(k in modname.lower() for k in ["agent", "runner", "framework"]):
            continue
        try:
            m = importlib.import_module(modname)
        except Exception:
            continue
        for name, obj in vars(m).items():
            if isinstance(obj, type) and callable(getattr(obj, "run", None)):
                score = ("runner" in name.lower()) * 2 + ("agent" in name.lower())
                try:
                    sig = inspect.signature(obj)
                    if any(p.name == "config" for p in sig.parameters.values()):
                        score += 1
                except Exception:
                    pass
                hits.append((score, f"{modname}.{name}", obj))
    if not hits:
        raise RuntimeError("No runner with .run(...) found in sentientresearchagent")
    hits.sort(reverse=True)
    _, fqname, cls = hits[0]
    return cls, fqname

RunnerClass, chosen_runner = pick_runner()

# ---- Resolve agent config robustly (env override + glob) ----
# Allow override: TRACKER_AGENT_CONFIG=/abs/or/relative/path.yaml
cfg_override = os.getenv("TRACKER_AGENT_CONFIG")
if cfg_override:
    AGENT_CONFIG = str((Path(cfg_override).resolve()))
else:
    # Common locations (both from repo root and from src/)
    candidates = [
        _root / "src" / "sentientresearchagent" / "hierarchical_agent_framework" / "agent_configs" / "tracker_agent.yaml",
        _root / "sentientresearchagent" / "hierarchical_agent_framework" / "agent_configs" / "tracker_agent.yaml",
    ]
    AGENT_CONFIG = None
    for c in candidates:
        if c.exists():
            AGENT_CONFIG = str(c)
            break
    if not AGENT_CONFIG:
        raise FileNotFoundError("tracker_agent.yaml not found. Set TRACKER_AGENT_CONFIG env or create the file under src/.../agent_configs/")

# ---- FastAPI app ----
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="Health Wellness Tracker (ROMA)", version="0.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Instantiate runner (with config path we resolved)
try:
    runner = RunnerClass(config=AGENT_CONFIG)
except TypeError:
    runner = RunnerClass()

class HealthEntry(BaseModel):
    meal_log: Optional[str] = Field(None, example="Rice and beans for lunch")
    exercise_log: Optional[str] = Field(None, example="20 min walk")
    sleep_log: Optional[str] = Field(None, example="6h")
    mood_log: Optional[str] = Field(None, example="Tired")
    extras: Optional[Dict[str, Any]] = None

class AnalysisOut(BaseModel):
    analysis: Dict[str, Any]

@app.get("/version")
def version():
    return {
        "cwd": str(Path.cwd()),
        "here": str(_here),
        "repo_root": str(_root),
        "runner": chosen_runner,
        "agent_config": AGENT_CONFIG,
        "openrouter_key_set": bool(os.environ.get("OPENROUTER_API_KEY")),
        "provider": os.getenv("AGNO_DEFAULT_PROVIDER"),
        "model": os.getenv("AGNO_DEFAULT_MODEL"),
        "has_openai_key": bool(os.environ.get("OPENAI_API_KEY")),
    }

@app.get("/")
def health():
    return {"ok": True}

@app.post("/analyze", response_model=AnalysisOut)
async def analyze_entry(entry: HealthEntry = Body(...)):
    data = entry.model_dump(exclude_none=True)

    sys_prompt = (
        "You are a wellness assistant. Given daily logs, return JSON with keys "
        '"daily_summary" and "recommendations". Keep it concise and actionable.'
    )
    user_lines = [f"{k}: {v}" for k, v in data.items() if k in {"meal_log","exercise_log","sleep_log","mood_log"} and v]
    user_msg = "\n".join(user_lines) or json.dumps(data, ensure_ascii=False)

    # Try wrapped messages first (many runners expect this)
    messages_list = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_msg},
    ]
    call_hints = {
        "provider": "openrouter",
        "model": os.getenv("AGNO_DEFAULT_MODEL", "openrouter/deepseek/deepseek-chat-v3.1:free"),
        "api_base": os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
    }

    try:
        res = runner.run({"messages": messages_list, **call_hints})
        return {"analysis": res if isinstance(res, dict) else {"model_output": res}}
    except Exception:
        try:
            res = runner.run(messages_list)  # bare list
            return {"analysis": res if isinstance(res, dict) else {"model_output": res}}
        except Exception:
            try:
                res = runner.run({**data, **call_hints})  # raw dict
                return {"analysis": res if isinstance(res, dict) else {"model_output": res}}
            except Exception as e3:
                tb = traceback.format_exc()
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": str(e3),
                        "hint": "Tried wrapped messages, bare list, raw dict with OpenRouter hints.",
                        "agent_config": AGENT_CONFIG,
                        "trace_tail": tb[-2000:],
                    },
                )
