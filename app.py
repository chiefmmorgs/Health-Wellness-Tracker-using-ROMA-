from __future__ import annotations
import json

def ingest(data):
    user = data.get("user_profile", {}) or {}
    logs = data.get("daily_logs", []) or []
    targets = data.get("targets", {}) or {}
    missing = []

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

    norm_logs = []
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

    ok = len(missing) == 0 and len(norm_logs) > 0
    return {
        "ok": ok,
        "missing_fields": missing if not ok else [],
        "profile": prof,
        "logs": norm_logs,
        "targets": norm_targets,
    }

def _avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs)/len(xs), 2) if xs else None

def metrics(profile, logs, targets):
    sleep_avg = _avg([d.get("sleep_hours") for d in logs])
    steps_avg = _avg([d.get("steps") for d in logs])
    water_avg = _avg([d.get("water_liters") for d in logs])
    workouts_count = sum(len(d.get("workouts",[])) for d in logs)
    minutes_total = sum(sum(w["minutes"] for w in d.get("workouts",[])) for d in logs)
    cals_avg = _avg([d.get("calories_in") for d in logs])

    bmi = None
    try:
        h = (profile["height_cm"] or 0)/100
        if h and profile["weight_kg"]:
            bmi = round(profile["weight_kg"]/(h*h), 2)
    except:
        pass

    def tdee():
        age = profile.get("age")
        sex = profile.get("sex")
        w = profile.get("weight_kg")
        hcm = profile.get("height_cm")
        if None in (age, sex, w, hcm) or steps_avg is None:
            return None
        bmr = 10*w + 6.25*hcm - 5*age + (5 if str(sex).upper().startswith("M") else -161)
        if steps_avg < 5000:
            af = 1.2
        elif steps_avg < 8000:
            af = 1.35
        elif steps_avg < 12000:
            af = 1.5
        else:
            af = 1.7
        return round(bmr*af, 0)

    t = tdee()
    cal_bal = round(cals_avg - t, 0) if (cals_avg is not None and t is not None) else None

    def adhere(actual, target, higher=True):
        if actual is None or target is None or target == 0:
            return None
        if higher:
            ratio = min(actual/target, 1.0)
        else:
            ratio = min(target/max(actual,1), 1.0) if actual > 0 else 1.0
        return int(round(ratio*100))

    adherence = {
        "sleep": adhere(sleep_avg, targets.get("sleep_h"), True),
        "steps": adhere(steps_avg, targets.get("steps"), True),
        "workouts": adhere(workouts_count, targets.get("workouts_per_week"), True),
        "calories_in": adhere(cals_avg, targets.get("calories_in"), False),
        "water": adhere(water_avg, targets.get("water_liters"), True),
    }

    return {
        "bmi": bmi,
        "sleep_avg_h": sleep_avg,
        "steps_avg": steps_avg,
        "water_avg_l": water_avg,
        "workouts_count": workouts_count,
        "minutes_total": minutes_total,
        "calorie_balance_est": cal_bal,
        "adherence": adherence
    }

def coach(logs, targets, m):
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
    if weakest == "sleep":
        focus.append("Sleep: add 15–20 minutes per night")
    if weakest == "steps":
        focus.append("Movement: one short walk daily")
    if weakest == "calories_in":
        focus.append("Food: one lighter swap per day")
    if weakest == "water":
        focus.append("Hydration: 1 extra glass per meal")
    if weakest == "workouts":
        focus.append("Training: schedule 1 short session")
    return {"daily_suggestions": daily, "weekly_focus": focus[:2]}

def report(m, focus):
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
        "week_summary": {"wins": wins, "gaps": gaps, "kpis": kpis},
        "weekly_plan": weekly_plan,
        "next_actions": next_actions[:2]
    }

def run_pipeline(user_input):
    ing = ingest(user_input)
    if not ing["ok"]:
        return {
            "status": "needs_input",
            "missing_fields": ing["missing_fields"],
            "week_summary": {},
            "daily_suggestions": [],
            "weekly_plan": {},
            "next_actions": []
        }
    met = metrics(ing["profile"], ing["logs"], ing["targets"])
    coa = coach(ing["logs"], ing["targets"], met)
    rep = report(met, coa["weekly_focus"])
    return {
        "status": "ok",
        "missing_fields": [],
        "week_summary": rep["week_summary"],
        "daily_suggestions": coa["daily_suggestions"],
        "weekly_plan": rep["weekly_plan"],
        "next_actions": rep["next_actions"]
    }

if __name__ == "__main__":
    example_input = {
        "user_profile": { "age": 28, "sex": "M", "height_cm": 177, "weight_kg": 79, "goal": "fat loss", "constraints": "knee pain on runs" },
        "targets": { "sleep_h": 7.5, "steps": 9000, "workouts_per_week": 3, "calories_in": 2400, "water_liters": 2.5 },
        "daily_logs": [
            { "date": "2025-09-08", "sleep_hours": 6.8, "steps": 7200, "workouts": [{ "type": "push", "minutes": 35, "intensity_1_5": 3 }], "calories_in": 2550, "water_liters": 2.0, "mood_1_5": 3, "notes": "desk day" },
            { "date": "2025-09-09", "sleep_hours": 7.1, "steps": 8100, "workouts": [], "calories_in": 2450, "water_liters": 2.3, "mood_1_5": 4, "notes": "light walk" }
        ]
    }
    print(json.dumps(run_pipeline(example_input), indent=2))
