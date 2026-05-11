const GRADIENTS = [
  ["#ff5722", "#ff8a65"],
  ["#ff8c00", "#ffb74d"],
  ["#ffb800", "#ffe082"],
  ["#00bcd4", "#4dd0e1"],
  ["#7c4dff", "#b388ff"],
];

const FEATURE_LABELS = {
  temperature_c:     "Temperature",
  relative_humidity: "Humidity",
  wind_speed_kmh:    "Wind Speed",
  rainfall_mm:       "Rainfall",
  days_since_rain:   "Days Since Rain",
  FFMC: "FFMC", DMC: "DMC", DC: "DC",
  ISI: "ISI",  BUI: "BUI", FWI: "FWI",
  brightness_K: "Brightness (K)",
  FRP_MW:       "Fire Radiative Power",
  LST_day_c:    "Land Surface Temp",
  latitude: "Latitude", longitude: "Longitude",
  month: "Month", day_of_year: "Day of Year",
  NDVI: "NDVI", EVI: "EVI",
  vegetation_encoded: "Vegetation Type",
};

export default function FeatureChart({ contributors }) {
  const maxImp = Math.max(...contributors.map(c => c.importance));

  return (
    <div>
      {contributors.map((c, i) => {
        const pct = maxImp > 0 ? (c.importance / maxImp) * 100 : 0;
        const [c1, c2] = GRADIENTS[i % GRADIENTS.length];
        const label = FEATURE_LABELS[c.feature] || c.feature;

        return (
          <div key={c.feature} style={{ marginBottom: 14 }}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
              marginBottom: 5,
            }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#d0d4e0" }}>
                {label}
              </span>
              <span style={{ fontSize: 11, color: "#6b7280", fontVariantNumeric: "tabular-nums" }}>
                {c.value} &nbsp;<span style={{ opacity: 0.5 }}>·</span>&nbsp; {(c.importance * 100).toFixed(1)}%
              </span>
            </div>

            {/* Track */}
            <div style={{
              background: "rgba(255,255,255,0.06)",
              borderRadius: 6,
              height: 8,
              overflow: "hidden",
            }}>
              {/* Fill */}
              <div style={{
                width: `${pct}%`,
                height: "100%",
                background: `linear-gradient(90deg, ${c1}, ${c2})`,
                borderRadius: 6,
                boxShadow: `0 0 8px ${c1}66`,
                transition: "width 0.9s cubic-bezier(0.22,1,0.36,1)",
              }} />
            </div>
          </div>
        );
      })}

      <p style={{
        fontSize: 10,
        color: "#555a6e",
        marginTop: 12,
        lineHeight: 1.5,
      }}>
        Importance = XGBoost gain-based score. Higher bars = greater influence on this prediction.
      </p>
    </div>
  );
}
