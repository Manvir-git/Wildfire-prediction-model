"""
Fire Risk Prediction API
Flask REST backend for the fire risk prediction web application.

Endpoints:
  POST /api/predict  { "lat": float, "lon": float }
  GET  /api/health

Requires model artifacts in ./artifacts/:
  xgb_model.pkl      — trained XGBoost classifier (from co-author)
  scaler.pkl         — fitted StandardScaler (from co-author)
  label_encoder.pkl  — fitted LabelEncoder for vegetation_type (from co-author)
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

# ── Load model artifacts at startup ─────────────────────────────────────────
try:
    import joblib
    ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
    model   = joblib.load(os.path.join(ARTIFACTS_DIR, "xgb_model.pkl"))
    scaler  = joblib.load(os.path.join(ARTIFACTS_DIR, "scaler.pkl"))
    le_veg  = joblib.load(os.path.join(ARTIFACTS_DIR, "label_encoder.pkl"))
    ARTIFACTS_LOADED = True
    print("[OK] Model artifacts loaded successfully.")
except Exception as e:
    ARTIFACTS_LOADED = False
    print(f"[WARN] Could not load model artifacts: {e}")
    print("[WARN] /api/predict will return 503 until artifacts are placed in ./artifacts/")

# ── Feature order MUST match training data exactly ───────────────────────────
# From training notebook: weather_features + fwi_features + satellite_features
#                         + spatial_temporal + ["vegetation_encoded"]
FEATURE_ORDER = [
    "temperature_c", "relative_humidity", "wind_speed_kmh", "rainfall_mm", "days_since_rain",
    "FFMC", "DMC", "DC", "ISI", "BUI", "FWI",
    "brightness_K", "FRP_MW", "LST_day_c",
    "latitude", "longitude", "month", "day_of_year",
    "NDVI", "EVI", "vegetation_encoded",
]

# Risk level thresholds
def _risk_label(prob):
    if prob < 0.40:   return "Low"
    elif prob < 0.60: return "Moderate"
    elif prob < 0.75: return "High"
    else:             return "Very High"

def _risk_color(label):
    return {"Low": "#2ecc71", "Moderate": "#f39c12",
            "High": "#e67e22", "Very High": "#e74c3c"}.get(label, "#aaa")

# ── Flask app ────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app, origins="*")   # allow Vercel frontend

from data_fetcher import get_all_features


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "Fire Risk Predictor API",
        "status": "ok",
        "artifacts_loaded": ARTIFACTS_LOADED,
        "endpoints": {
            "health":  "GET  /api/health",
            "predict": "POST /api/predict  — body: {lat, lon}",
        }
    })

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "artifacts_loaded": ARTIFACTS_LOADED,
        "feature_count": len(FEATURE_ORDER),
    })


@app.route("/api/predict", methods=["POST"])
def predict():
    if not ARTIFACTS_LOADED:
        return jsonify({
            "error": "Model artifacts not loaded. Place xgb_model.pkl, scaler.pkl, "
                     "and label_encoder.pkl in ./artifacts/ and restart the server."
        }), 503

    body = request.get_json(force=True)
    lat = body.get("lat")
    lon = body.get("lon")

    if lat is None or lon is None:
        return jsonify({"error": "Request must include 'lat' and 'lon' fields."}), 400

    try:
        lat, lon = float(lat), float(lon)
    except (ValueError, TypeError):
        return jsonify({"error": "'lat' and 'lon' must be numeric."}), 400

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return jsonify({"error": "Coordinates out of valid range."}), 400

    # 1. Fetch and compute all features
    try:
        raw_features, metadata = get_all_features(lat, lon)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502

    # 2. Encode vegetation_type → vegetation_encoded
    try:
        veg_str = raw_features.pop("vegetation_type")
        # Handle unseen labels gracefully
        if veg_str in le_veg.classes_:
            veg_encoded = int(le_veg.transform([veg_str])[0])
        else:
            veg_encoded = int(le_veg.transform([le_veg.classes_[0]])[0])
        raw_features["vegetation_encoded"] = veg_encoded
    except Exception as e:
        return jsonify({"error": f"Vegetation encoding failed: {e}"}), 500

    # 3. Assemble feature vector in EXACT training order
    try:
        feature_vector = [raw_features[f] for f in FEATURE_ORDER]
    except KeyError as e:
        return jsonify({"error": f"Missing feature: {e}"}), 500

    # 4. Scale
    try:
        X = np.array(feature_vector).reshape(1, -1)
        X_scaled = scaler.transform(X)
    except Exception as e:
        return jsonify({"error": f"Scaling failed: {e}"}), 500

    # 5. Predict
    try:
        prob = float(model.predict_proba(X_scaled)[0][1])
        prediction = int(model.predict(X_scaled)[0])
    except Exception as e:
        return jsonify({"error": f"Inference failed: {e}"}), 500

    # 6. Feature importance (model's gain-based importance, not SHAP)
    #    Top 5 features by model importance × scaled feature value magnitude
    try:
        importances = model.feature_importances_  # shape: (21,)
        feature_df = pd.DataFrame({
            "feature": FEATURE_ORDER,
            "importance": importances,
            "raw_value": feature_vector,
        })
        top5 = feature_df.nlargest(5, "importance")[["feature", "importance", "raw_value"]]
        top_contributors = [
            {
                "feature": row["feature"],
                "importance": round(float(row["importance"]), 4),
                "value": round(float(row["raw_value"]), 3),
            }
            for _, row in top5.iterrows()
        ]
    except Exception:
        top_contributors = []

    risk_label = _risk_label(prob)

    response = {
        "fire_probability": round(prob, 4),
        "fire_probability_pct": round(prob * 100, 1),
        "prediction": prediction,
        "risk_level": risk_label,
        "risk_color": _risk_color(risk_label),
        "top_contributors": top_contributors,
        "features_used": {k: v for k, v in raw_features.items() if k != "vegetation_encoded"},
        "vegetation_type": veg_str,
        "metadata": metadata,
    }

    return jsonify(response)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)
