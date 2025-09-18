from typing import Any, Dict, List

class IngestorAgent:
    name = "ingestor"

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        user = payload.get("user_profile", {}) or {}
        logs = payload.get("daily_logs", []) or []
        targets = payload.get("targets", {}) or {}
        missing: List[str] = []

        prof = {
            "age": user.get("age"),
            "sex": user.get("sex"),
            "height_cm": user.get("height_cm"),
            "weight_kg": user.get("weight_kg"),
            "goal": user.get("goal"),
            "constraints": user.get("constraints") or None,
        }
        for k in ["age","sex","height_cm","weight_kg","goal"]:
            if prof.get(k) is None:
                missing.append(f"user_profile.{k}")

        norm_logs: List[Dict[str, Any]] = []
        for row in logs:
            if not row.get("date"):
                missing.append("daily_logs[].date")
            workouts = []
            for w in row.get("workouts", []) or []:
                workouts.append({
                    "type": w.get("type") or "other",
                    "minutes": int(w.get("minutes") or 0),
                    "intensity_1_5": int(w.get("intensity_1_5") or 1),
                })
            norm_logs.append({
                "date": row.get("date"),
                "sleep_hours": row.get("sleep_hours"),
                "steps": row.get("steps"),
                "workouts": workouts,
                "calories_in": row.get("calories_in"),
                "water_liters": row.get("water_liters"),
                "mood_1_5": row.get("mood_1_5"),
                "notes": (row.get("notes") or "")[:140],
            })

        norm_targets = {
            "sleep_h": targets.get("sleep_h"),
            "steps": targets.get("steps"),
            "workouts_per_week": targets.get("workouts_per_week"),
            "calories_in": targets.get("calories_in"),
            "water_liters": targets.get("water_liters"),
        }

        ok = (len(missing) == 0) and (len(norm_logs) > 0)
        return {
            "status": "ok" if ok else "needs_input",
            "missing_fields": [] if ok else missing,
            "normalized_profile": prof,
            "normalized_logs": norm_logs,
            "normalized_targets": norm_targets,
        }
