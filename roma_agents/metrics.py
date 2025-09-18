from typing import Any, Dict

def _avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs)/len(xs), 2) if xs else None

class MetricsAgent:
    name = "metrics"

    def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        prof = payload["normalized_profile"]
        logs = payload["normalized_logs"]
        targets = payload["normalized_targets"]

        sleep_avg = _avg([d.get("sleep_hours") for d in logs])
        steps_avg = _avg([d.get("steps") for d in logs])
        water_avg = _avg([d.get("water_liters") for d in logs])
        workouts_count = sum(len(d.get("workouts",[])) for d in logs)
        minutes_total = sum(sum(w["minutes"] for w in d.get("workouts",[])) for d in logs)
        cals_avg = _avg([d.get("calories_in") for d in logs])

        bmi = None
        try:
            h = (prof["height_cm"] or 0)/100
            if h and prof["weight_kg"]:
                bmi = round(prof["weight_kg"]/(h*h), 2)
        except:
            pass

        def tdee():
            age = prof.get("age"); sex = prof.get("sex")
            w = prof.get("weight_kg"); hcm = prof.get("height_cm")
            if None in (age, sex, w, hcm) or steps_avg is None:
                return None
            bmr = 10*w + 6.25*hcm - 5*age + (5 if str(sex).upper().startswith("M") else -161)
            if steps_avg < 5000: af = 1.2
            elif steps_avg < 8000: af = 1.35
            elif steps_avg < 12000: af = 1.5
            else: af = 1.7
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
            "status": "ok",
            "metrics": {
                "bmi": bmi,
                "sleep_avg_h": sleep_avg,
                "steps_avg": steps_avg,
                "water_avg_l": water_avg,
                "workouts_count": workouts_count,
                "minutes_total": minutes_total,
                "calorie_balance_est": cal_bal,
                "adherence": adherence
            }
        }
