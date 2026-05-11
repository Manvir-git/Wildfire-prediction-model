"""
Data Acquisition Module
Fetches all 21 features required by the XGBoost model from a lat/lon pair.

Weather (5):  Open-Meteo API — free, no API key, global real-time data
FWI (6):      Computed via fwi_calculator.py from the fetched weather
Satellite (3): LST_day_c ≈ derived from air temp; brightness_K ≈ LST+273.15; FRP_MW = 0
Vegetation (3): NDVI/EVI from monthly lookup; vegetation_type from biome lookup
Spatial (4):  lat, lon, month, day_of_year from the request itself

NOTE: For a production system, NDVI/EVI/LST should be fetched from NASA FIRMS/AppEEARS.
For demonstration, seasonal approximations are used, which match the training data
distribution well enough for showcase purposes.
"""

import math
import datetime
import urllib.request
import urllib.error
import json
import ssl

from fwi_calculator import compute_fwi_components

# ── Vegetation type lookup (GlobCover simplified) ────────────────────────────
# Maps rough lat/lon bounding boxes to vegetation_type label used in training.
# The label encoder values must match those from the training run (Kushagra provides le_veg).
# We use the string labels; le_veg.transform() is called in app.py at inference time.

_VEGETATION_RULES = [
    # (lat_min, lat_max, lon_min, lon_max, vegetation_type)
    (8,  18,  72,  88,  "Tropical Moist Forest"),   # Western Ghats / coastal
    (18, 28,  68,  90,  "Dry Deciduous Forest"),     # Central India belt
    (28, 36,  76,  98,  "Mixed Forest"),              # Himachal/Uttarakhand
    (20, 28,  80,  98,  "Dry Deciduous Forest"),     # Odisha/Jharkhand/MP
    (22, 32,  88,  97,  "Mixed Forest"),              # Northeast India
    (25, 32,  68,  78,  "Scrubland"),                 # Rajasthan/Gujarat
    (8,  25,  68,  88,  "Tropical Moist Forest"),    # General peninsular
]
_DEFAULT_VEG = "Mixed Forest"


def _get_vegetation_type(lat, lon):
    for lat_min, lat_max, lon_min, lon_max, veg in _VEGETATION_RULES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return veg
    return _DEFAULT_VEG


# ── NDVI/EVI monthly lookup by India fire zone ──────────────────────────────
# Mean values estimated from MODIS MOD13A3 product for Indian forest zones.
# Higher NDVI in post-monsoon (Oct-Dec), lower in peak-fire season (Mar-May).
_NDVI_MONTHLY = {
    1: 0.42, 2: 0.36, 3: 0.30, 4: 0.25, 5: 0.28,
    6: 0.45, 7: 0.58, 8: 0.62, 9: 0.60, 10: 0.55,
    11: 0.50, 12: 0.46
}
_EVI_MONTHLY = {
    1: 0.28, 2: 0.24, 3: 0.20, 4: 0.17, 5: 0.19,
    6: 0.30, 7: 0.38, 8: 0.41, 9: 0.40, 10: 0.37,
    11: 0.34, 12: 0.31
}

# Latitude modifier: northern India (lat > 25) has lower NDVI in winter
def _get_ndvi_evi(month, lat):
    ndvi_base = _NDVI_MONTHLY[month]
    evi_base  = _EVI_MONTHLY[month]
    if lat > 25 and month in [11, 12, 1, 2]:
        ndvi_base *= 0.85
        evi_base  *= 0.85
    return round(ndvi_base, 3), round(evi_base, 3)


# ── Open-Meteo API call ──────────────────────────────────────────────────────
_OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"

def _fetch_open_meteo(lat, lon):
    """
    Fetch current + last 7 days of daily weather from Open-Meteo.
    Returns dict with today's values and precipitation history.
    """
    today = datetime.date.today()
    seven_days_ago = today - datetime.timedelta(days=7)

    params = (
        f"latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,relative_humidity_2m_max,"
        f"windspeed_10m_max,precipitation_sum"
        f"&timezone=Asia%2FKolkata"
        f"&start_date={seven_days_ago.isoformat()}"
        f"&end_date={today.isoformat()}"
    )
    url = f"{_OPEN_METEO_BASE}?{params}"

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        raise RuntimeError(f"Open-Meteo API error: {e}")

    daily = data.get("daily", {})
    dates          = daily.get("time", [])
    temps          = daily.get("temperature_2m_max", [])
    humidities     = daily.get("relative_humidity_2m_max", [])
    winds          = daily.get("windspeed_10m_max", [])
    precipitations = daily.get("precipitation_sum", [])

    if not dates:
        raise RuntimeError("Open-Meteo returned empty data for this location.")

    # Today is the last entry
    idx = -1
    temp_c       = float(temps[idx]) if temps[idx] is not None else 30.0
    humidity     = float(humidities[idx]) if humidities[idx] is not None else 40.0
    wind_kmh     = float(winds[idx]) if winds[idx] is not None else 15.0
    rain_today   = float(precipitations[idx]) if precipitations[idx] is not None else 0.0

    # days_since_rain: how many days ago did it last rain (>= 1mm)?
    days_since_rain = 0
    for i in range(len(precipitations) - 2, -1, -1):  # look back, skip today
        p = precipitations[i]
        if p is not None and float(p) >= 1.0:
            break
        days_since_rain += 1

    return {
        "temperature_c":     round(temp_c, 1),
        "relative_humidity": round(max(0, min(humidity, 100)), 1),
        "wind_speed_kmh":    round(wind_kmh, 1),
        "rainfall_mm":       round(rain_today, 1),
        "days_since_rain":   days_since_rain,
        "_rain_yesterday":   float(precipitations[-2]) if len(precipitations) >= 2 and precipitations[-2] else 0.0,
    }


# ── Satellite feature approximations ────────────────────────────────────────

def _approx_satellite(temp_c, month, lat):
    """
    LST_day_c: land surface temperature runs 2-8°C above air temp in India,
               higher in summer, lower in monsoon.
    brightness_K: satellite brightness temperature ≈ LST in Kelvin
    FRP_MW: 0 — no active fire detected (conservative/safe default)
    """
    lst_offset_monthly = {
        1: 3.0, 2: 4.0, 3: 6.0, 4: 8.0, 5: 7.0, 6: 4.0,
        7: 2.0, 8: 2.0, 9: 3.0, 10: 4.0, 11: 3.0, 12: 2.5
    }
    offset = lst_offset_monthly.get(month, 4.0)
    lst_day_c = temp_c + offset

    # Brightness temperature: LST in Kelvin (physical relationship)
    brightness_k = round(lst_day_c + 273.15, 1)

    return {
        "brightness_K": brightness_k,
        "FRP_MW":        0.0,        # no active fire
        "LST_day_c":     round(lst_day_c, 1),
    }


# ── Main feature assembly ────────────────────────────────────────────────────

def get_all_features(lat: float, lon: float) -> dict:
    """
    Fetch and compute all 21 features for a lat/lon point (today's date).

    Returns:
        dict with all 21 feature values + 'vegetation_type' string for encoding.
        Also returns 'metadata' for display purposes.
    """
    today = datetime.date.today()
    month      = today.month
    day_of_year = today.timetuple().tm_yday

    # 1. Fetch weather
    weather = _fetch_open_meteo(lat, lon)

    # 2. Compute FWI (previous-day codes: use seasonal defaults)
    fwi = compute_fwi_components(
        temp=weather["temperature_c"],
        rh=weather["relative_humidity"],
        wind=weather["wind_speed_kmh"],
        rain=weather["rainfall_mm"],
        month=month,
    )

    # 3. Satellite approximations
    satellite = _approx_satellite(weather["temperature_c"], month, lat)

    # 4. Vegetation
    ndvi, evi = _get_ndvi_evi(month, lat)
    veg_type  = _get_vegetation_type(lat, lon)

    # 5. Spatiotemporal
    spatial = {
        "latitude":    round(lat, 4),
        "longitude":   round(lon, 4),
        "month":       month,
        "day_of_year": day_of_year,
    }

    features = {
        # Weather (5)
        "temperature_c":     weather["temperature_c"],
        "relative_humidity": weather["relative_humidity"],
        "wind_speed_kmh":    weather["wind_speed_kmh"],
        "rainfall_mm":       weather["rainfall_mm"],
        "days_since_rain":   weather["days_since_rain"],

        # FWI (6)
        "FFMC": fwi["FFMC"],
        "DMC":  fwi["DMC"],
        "DC":   fwi["DC"],
        "ISI":  fwi["ISI"],
        "BUI":  fwi["BUI"],
        "FWI":  fwi["FWI"],

        # Satellite (3)
        "brightness_K": satellite["brightness_K"],
        "FRP_MW":        satellite["FRP_MW"],
        "LST_day_c":     satellite["LST_day_c"],

        # Vegetation (3) — vegetation_type encoded in app.py
        "NDVI":           ndvi,
        "EVI":            evi,
        "vegetation_type": veg_type,    # string — encoded to int in app.py

        # Spatiotemporal (4)
        "latitude":    spatial["latitude"],
        "longitude":   spatial["longitude"],
        "month":       spatial["month"],
        "day_of_year": spatial["day_of_year"],
    }

    metadata = {
        "data_sources": {
            "weather":   "Open-Meteo API (real-time)",
            "fwi":       "Computed (Van Wagner 1987 formulas)",
            "satellite": "Seasonal approximation (LST from air temp)",
            "vegetation": "Regional biome lookup",
        },
        "fetch_date": today.isoformat(),
    }

    return features, metadata
