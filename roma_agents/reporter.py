from typing import Any, Dict

class ReporterAgent:
    name = "reporter"

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        m = payload["metrics"]
        focus = payload["weekly_focus"]

        wins, gaps = [], []
        if m["sleep_avg_h"] is not None:
            (wins if m["sleep_avg_h"] >= 7 else gaps).append("Sleep avg")
        if m["steps_avg"] is not None:
            (wins if m["steps_avg"] >= 8000 else gaps).append("Steps avg")

        kpis = [
            {"name": "Sleep avg (h)", "value": m["sleep_avg_h"]},
            {"name": "Steps avg", "value": m["steps_avg"]},
            {"name": "Workouts", "value": m["workouts_count"]},
        ]
        weekly_plan = {
            "focus": focus,
            "checkpoints": [
                {"day": "Mon", "action": "Plan 3 short walks"},
                {"day": "Thu", "action": "Lights out 20 min earlier"},
                {"day": "Sat", "action": "1 bodyweight session, 20 min"},
            ],
        }
        pairs = sorted([(k, v if v is not None else -1) for k,v in m["adherence"].items()], key=lambda x: x[1])
        next_actions = []
        for k,_ in pairs[:2]:
            if k == "sleep":
                next_actions.append("Set a fixed bedtime alarm tonight")
            elif k == "steps":
                next_actions.append("Add 10-minute afternoon walk today")
            elif k == "calories_in":
                next_actions.append("Swap one snack for fruit today")
            elif k == "water":
                next_actions.append("Carry a 500ml bottle all day")
            elif k == "workouts":
                next_actions.append("Book one 20-minute session this week")

        return {
            "status": "ok",
            "week_summary": {"wins": wins, "gaps": gaps, "kpis": kpis},
            "weekly_plan": weekly_plan,
            "next_actions": next_actions[:2]
        }
