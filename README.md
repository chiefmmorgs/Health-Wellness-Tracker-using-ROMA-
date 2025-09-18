ROMA Health Tracker

Run CLI
source .venv/bin/activate
python app.py

Run API
uvicorn api:app --reload --port 8000

Test API
curl -X POST http://127.0.0.1:8000/weekly-report \
  -H "Content-Type: application/json" \
  -d '{"user_profile":{"age":28,"sex":"M","height_cm":177,"weight_kg":79,"goal":"fat loss"},"targets":{"sleep_h":7.5,"steps":9000,"workouts_per_week":3,"calories_in":2400,"water_liters":2.5},"daily_logs":[{"date":"2025-09-08","sleep_hours":6.8,"steps":7200,"workouts":[{"type":"push","minutes":35,"intensity_1_5":3}],"calories_in":2550,"water_liters":2.0},{"date":"2025-09-09","sleep_hours":7.1,"steps":8100,"workouts":[],"calories_in":2450,"water_liters":2.3}]}'
