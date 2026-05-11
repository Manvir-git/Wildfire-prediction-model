# 🔥 Wildfire Risk Predictor — India

Real-time forest fire risk prediction for any location in India using live weather data, Fire Weather Index computations, and a trained XGBoost ensemble model.

**CSE439 Dissertation-I · Manvir Singh & Kushagra Mangalam · LPU 2026**

---

## Live Demo

| Service | URL |
|---|---|
| Frontend | [frontend-theta-hazel-10.vercel.app](https://frontend-theta-hazel-10.vercel.app) |
| Backend API | Render (see deployment section) |

---

## Overview

The app takes a latitude/longitude pair, fetches real-time weather, computes the Canadian Forest Fire Weather Index (FWI) system, assembles 21 features, and runs them through an XGBoost classifier trained on India's 2022–23 fire season data to output a fire probability and risk level.

**Risk levels**

| Level | Probability | Colour |
|---|---|---|
| Low | < 40% | Green |
| Moderate | 40–60% | Yellow |
| High | 60–75% | Orange |
| Very High | > 75% | Red |

---

## Architecture

```
Browser
  └── React 18 frontend (Vercel)
        ├── Leaflet.js map — fixed-center pin UX
        ├── Nominatim geocoding — place search
        └── POST /api/predict → Flask backend (Render)
                                  ├── Open-Meteo API — live weather
                                  ├── fwi_calculator.py — Van Wagner 1987
                                  ├── Vegetation & satellite approximations
                                  └── XGBoost inference (21 features)
```

---

## Features

### Frontend
- Dark dashboard UI with glassmorphism cards
- Fixed-center teardrop pin — drag the map to reposition (ride-hailing style UX)
- Auto-centres on user's current location via browser Geolocation API
- Place search with autocomplete (restricted to India)
- Animated semi-circular risk gauge with colour-coded zone tracks
- Live weather stat cards (temperature, humidity, wind, rainfall)
- Top-5 feature importance bars with gradient fills
- Expandable accordion showing all 21 raw feature values
- Step-by-step loading animation

### Backend
- Single `POST /api/predict` endpoint — request body: `{"lat": float, "lon": float}`
- Real-time weather from [Open-Meteo](https://open-meteo.com/) (free, no API key)
- Full Canadian FWI system (FFMC, DMC, DC, ISI, BUI, FWI) via Van Wagner 1987
- Land Surface Temperature approximated from air temperature + monthly seasonal offset
- NDVI/EVI from MODIS MOD13A3 monthly lookup tables
- Vegetation type from GlobCover-simplified lat/lon bounding box rules
- Flask-CORS enabled for Vercel frontend

---

## 21 Model Features

| # | Feature | Source |
|---|---|---|
| 1 | temperature_c | Open-Meteo |
| 2 | relative_humidity | Open-Meteo |
| 3 | wind_speed_kmh | Open-Meteo |
| 4 | rainfall_mm | Open-Meteo |
| 5 | days_since_rain | Computed from 7-day history |
| 6 | FFMC | Van Wagner 1987 |
| 7 | DMC | Van Wagner 1987 |
| 8 | DC | Van Wagner 1987 |
| 9 | ISI | Van Wagner 1987 |
| 10 | BUI | Van Wagner 1987 |
| 11 | FWI | Van Wagner 1987 |
| 12 | brightness_K | LST + 273.15 |
| 13 | FRP_MW | 0 (no active fire default) |
| 14 | LST_day_c | Air temp + monthly offset |
| 15 | latitude | Request |
| 16 | longitude | Request |
| 17 | month | System date |
| 18 | day_of_year | System date |
| 19 | NDVI | MODIS monthly lookup |
| 20 | EVI | MODIS monthly lookup |
| 21 | vegetation_encoded | GlobCover biome rules + LabelEncoder |

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Leaflet.js, react-leaflet |
| Geocoding | Nominatim (OpenStreetMap) |
| Backend | Flask 3, Flask-CORS, Gunicorn |
| ML Model | XGBoost, scikit-learn, joblib |
| Weather API | Open-Meteo (free, no key required) |
| Frontend hosting | Vercel |
| Backend hosting | Render |

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Place model artifacts in backend/artifacts/
#   xgb_model.pkl
#   scaler.pkl
#   label_encoder.pkl

python3 app.py
# → http://localhost:5001
```

### Frontend

```bash
cd frontend
npm install
npm start
# → http://localhost:3000
```

The frontend reads `REACT_APP_API_URL` for the backend address — defaults to `http://localhost:5001` for local dev.

### Test the API

```bash
# Health check
curl http://localhost:5001/api/health

# Prediction (Bhopal, MP)
curl -X POST http://localhost:5001/api/predict \
  -H "Content-Type: application/json" \
  -d '{"lat": 23.2599, "lon": 77.4126}'
```

---

## Deployment

### Backend → Render

1. Connect the repo to a new Render Web Service, set root directory to `backend/`
2. **Build command:** `pip install -r requirements.txt`
3. **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
4. Go to **Environment → Secret Files** and upload the 3 `.pkl` files to `/opt/render/project/src/artifacts/`
5. Note the service URL (e.g. `https://fire-risk-api.onrender.com`)

### Frontend → Vercel

```bash
cd frontend

# Add your Render backend URL
npx vercel env add REACT_APP_API_URL production
# enter: https://your-app.onrender.com

# Deploy to production
npx vercel --prod
```

Or connect this GitHub repo in the Vercel dashboard, set the **Root Directory** to `frontend`, and add `REACT_APP_API_URL` under **Project → Settings → Environment Variables**.

---

## Project Structure

```
wildfire-prediction-model/
├── backend/
│   ├── app.py                  # Flask REST API
│   ├── data_fetcher.py         # Weather fetch + feature assembly
│   ├── fwi_calculator.py       # Van Wagner 1987 FWI implementation
│   ├── requirements.txt
│   ├── render.yaml             # Render deployment config
│   └── artifacts/              # .pkl files (gitignored)
│       ├── xgb_model.pkl
│       ├── scaler.pkl
│       └── label_encoder.pkl
└── frontend/
    ├── public/
    │   └── index.html
    ├── src/
    │   ├── App.jsx             # Root component, search, layout
    │   ├── App.css             # Dark theme design system
    │   ├── config.js           # API base URL
    │   └── components/
    │       ├── MapView.jsx     # Leaflet map + fixed-center pin
    │       ├── RiskResult.jsx  # Risk banner, gauge, stat cards
    │       └── FeatureChart.jsx # Feature importance bars
    ├── package.json
    └── vercel.json
```

---

## API Reference

### `GET /`
Returns service info and available endpoints.

### `GET /api/health`
```json
{
  "status": "ok",
  "artifacts_loaded": true,
  "feature_count": 21
}
```

### `POST /api/predict`

**Request**
```json
{ "lat": 23.2599, "lon": 77.4126 }
```

**Response**
```json
{
  "fire_probability": 0.2829,
  "fire_probability_pct": 28.3,
  "risk_level": "Low",
  "risk_color": "#2ecc71",
  "top_contributors": [
    { "feature": "rainfall_mm", "importance": 0.2875, "value": 0.0 }
  ],
  "features_used": { "temperature_c": 40.2, "..." : "..." },
  "vegetation_type": "Dry Deciduous Forest",
  "metadata": {
    "data_sources": { "weather": "Open-Meteo API (real-time)", "..." : "..." },
    "fetch_date": "2026-05-02"
  }
}
```

---

## Notes

- **Satellite features** (LST, brightness, FRP) are approximated for demonstration. A production system would pull real MODIS/VIIRS data from NASA FIRMS or AppEEARS.
- **FRP_MW** is set to 0 (no active fire detected) as a conservative default.
- Open-Meteo serves daily max forecasts updated in real time — predictions made minutes apart may differ slightly as forecasts are revised.
- The XGBoost model was trained on India 2022–23 fire event data with `rainfall_mm` as the highest-importance feature (~28.75% gain).
- The XGBoost version warning on startup (`serialized model from older version`) is harmless — re-export with `booster.save_model("xgb_model.json")` to eliminate it.

---

## References

- Van Wagner, C.E. (1987). *Development and Structure of the Canadian Forest Fire Weather Index System.* Canadian Forestry Service Technical Report 35.
- Chen, T. & Guestrin, C. (2016). *XGBoost: A Scalable Tree Boosting System.* KDD '16.
- Open-Meteo: [open-meteo.com](https://open-meteo.com/)
- NASA FIRMS: [firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov/)
