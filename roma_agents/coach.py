from typing import Any, Dict

class CoachAgent:
    name = "coach"

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        logs = payload["normalized_logs"]
        targets = payload["normalized_targets"]
        m = payload["metrics"]

        adh = m["adherence"]
        pairs = [(k, (v if v is not None else -1)) for k, v in adh.items()]
        pairs.sort(key=lambda x: x[1])
        weakest = pairs[0][0] if pairs else None

        daily = []
        for day in logs:
            tips = []
            if day.get("sleep_hours") is not None and targets.get("sleep_h") and day["sleep_hours"] < targets["sleep_h"]:
                tips.append("Go to bed 20 min earlier tonight")
            if day.get("steps") is not None and targets.get("steps") and day["steps"] < targets["steps"]:
                tips.append("Add a 10-minute brisk walk")
            if day.get("water_liters") is not None and targets.get("water_liters") and day["water_liters"] < targets["water_liters"]:
                tips.append("Drink 1 glass after each bathroom break")
            if day.get("calories_in") is not None and targets.get("calories_in") and day["calories_in"] > targets["calories_in"]:
                tips.append("Swap one snack for fruit or yogurt")
            daily.append({"date": day["date"], "tips": tips[:3]})

        focus = []
        if weakest == "sleep": focus.append("Sleep: add 15–20 minutes per night")
        if weakest == "steps": focus.append("Movement: one short walk daily")
        if weakest == "calories_in": focus.append("Food: one lighter swap per day")
        if weakest == "water": focus.append("Hydration: 1 extra glass per meal")
        if weakest == "workouts": focus.append("Training: schedule 1 short session")

        return {"status": "ok", "daily_suggestions": daily, "weekly_focus": focus[:2]}
