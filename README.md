# Fire Risk Predictor — Setup & Run Guide

## Prerequisites
- Python 3.10+ and Node.js 18+
- Model artifacts from Kushagra (co-author):
  - `xgb_model.pkl`
  - `scaler.pkl`
  - `label_encoder.pkl`

---

## Step 1: Save model artifacts (Kushagra runs this once)

```python
import joblib
# Run this in the training notebook after training is complete:
joblib.dump(india_xgb, 'xgb_model.pkl')
joblib.dump(india_scaler, 'scaler.pkl')
joblib.dump(le_veg, 'label_encoder.pkl')
```

Place the 3 `.pkl` files into `backend/artifacts/`.

---

## Step 2: Run the Flask backend

```bash
cd backend
pip install -r requirements.txt
python app.py
```

Server starts at http://localhost:5001
Test it: http://localhost:5001/api/health

---

## Step 3: Run the React frontend

```bash
cd frontend
npm install
npm start
```

App opens at http://localhost:3000

---

## Step 4: Test a prediction (optional, from terminal)

```bash
curl -X POST http://localhost:5001/api/predict \
  -H "Content-Type: application/json" \
  -d '{"lat": 30.34, "lon": 76.37}'
```

---

## Deployment (for viva demo)

**Backend → Render.com (free)**
1. Push `backend/` to GitHub
2. New Web Service on render.com → Python → start command: `gunicorn app:app`
3. Add env var PORT=5001
4. Copy the Render URL (e.g. https://fire-risk-api.onrender.com)

**Frontend → Vercel.com (free)**
1. In `frontend/src/config.js`, set `API_BASE` to your Render URL
2. Push `frontend/` to GitHub
3. Import project on vercel.com → deploy
4. Your live URL is ready

---

## Feature order (CRITICAL — must match training)

```
temperature_c, relative_humidity, wind_speed_kmh, rainfall_mm, days_since_rain,
FFMC, DMC, DC, ISI, BUI, FWI,
brightness_K, FRP_MW, LST_day_c,
latitude, longitude, month, day_of_year,
NDVI, EVI, vegetation_encoded
```

Any deviation from this order will produce wrong predictions silently.

---

## Data sources used
| Feature group | Source |
|---|---|
| Weather (temp, rh, wind, rain, days_since_rain) | Open-Meteo API (free, no key) |
| FWI components (FFMC, DMC, DC, ISI, BUI, FWI) | Computed — Van Wagner (1987) formulas |
| Satellite (brightness_K, LST_day_c) | Approximated from air temperature + seasonal offset |
| FRP_MW | 0.0 (conservative — no active fire assumed) |
| NDVI, EVI | Monthly lookup table (MODIS MOD13A3 averages for India) |
| vegetation_type | Lat/lon biome lookup (India regional rules) |
