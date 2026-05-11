import FeatureChart from "./FeatureChart";

const RISK = {
  "Low":       { color: "#00c875", bg: "low",       emoji: "🟢", blurb: "Conditions are not conducive to fire spread." },
  "Moderate":  { color: "#ffb800", bg: "moderate",  emoji: "🟡", blurb: "Some fire-weather factors are elevated." },
  "High":      { color: "#ff8c00", bg: "high",      emoji: "🟠", blurb: "Dangerous conditions. Heightened caution advised." },
  "Very High": { color: "#e74c3c", bg: "very-high", emoji: "🔴", blurb: "Extreme fire risk. Immediate vigilance required." },
};

/* ── SVG semi-circle gauge with coloured zone track ── */
function RiskGauge({ probability, riskLevel }) {
  const theme = RISK[riskLevel] || RISK["Moderate"];
  const pct = Math.round(probability * 100);

  const R = 72, cx = 110, cy = 95;
  const toRad = d => (d * Math.PI) / 180;
  const ptAt  = deg => [cx + R * Math.cos(toRad(deg)), cy + R * Math.sin(toRad(deg))];

  const arcPath = (fromDeg, toDeg) => {
    const [x1, y1] = ptAt(fromDeg);
    const [x2, y2] = ptAt(toDeg);
    const large = Math.abs(toDeg - fromDeg) > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2}`;
  };

  // Zone segments: 0→40% green, 40→60% yellow, 60→75% orange, 75→100% red
  // Arc spans -180° (left) to 0° (right), so prob maps → -180 + prob*180
  const zoneSegments = [
    { from: -180, to: -180 + 0.40 * 180, color: "#00c875" },
    { from: -180 + 0.40 * 180, to: -180 + 0.60 * 180, color: "#ffb800" },
    { from: -180 + 0.60 * 180, to: -180 + 0.75 * 180, color: "#ff8c00" },
    { from: -180 + 0.75 * 180, to: 0,                  color: "#e74c3c" },
  ];

  const fillAngle = -180 + probability * 180;
  const [fx, fy] = ptAt(fillAngle);
  const fillPath = `M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${fx} ${fy}`;

  return (
    <div className="gauge-card">
      <svg viewBox="0 0 220 112" style={{ width: "100%", maxWidth: 240, display: "block", margin: "0 auto" }}>
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Coloured zone track (background) */}
        {zoneSegments.map((z, i) => (
          <path key={i} d={arcPath(z.from, z.to)}
            fill="none" stroke={z.color} strokeWidth="10"
            strokeLinecap="butt" opacity="0.22" />
        ))}

        {/* Filled arc */}
        <path d={fillPath} fill="none" stroke={theme.color}
          strokeWidth="10" strokeLinecap="round" />

        {/* Needle dot */}
        <circle cx={fx} cy={fy} r={7} fill={theme.color} filter="url(#glow)" />

        {/* Text */}
        <text x={cx} y={cy - 8} textAnchor="middle"
          fontSize="30" fontWeight="800" fill={theme.color}
          fontFamily="-apple-system, BlinkMacSystemFont, sans-serif">
          {pct}%
        </text>
        <text x={cx} y={cy + 10} textAnchor="middle"
          fontSize="10" fill="#6b7280"
          fontFamily="-apple-system, BlinkMacSystemFont, sans-serif">
          fire probability
        </text>

        {/* Zone labels */}
        <text x={cx - R - 4} y={cy + 4} textAnchor="end"  fontSize="8" fill="#00c875" opacity="0.7">Low</text>
        <text x={cx + R + 4} y={cy + 4} textAnchor="start" fontSize="8" fill="#e74c3c" opacity="0.7">V.High</text>
      </svg>

      <div className={`risk-badge risk-badge--${theme.bg}`}>
        {theme.emoji} {riskLevel} Risk
      </div>
    </div>
  );
}


export default function RiskResult({ result, locationLabel }) {
  const f = result.features_used || {};
  const risk = RISK[result.risk_level] || RISK["Moderate"];

  return (
    <div className="result-panel">

      {/* ── Risk banner ── */}
      <div className={`risk-banner risk-banner--${risk.bg}`}>
        <div className="risk-banner-left">
          <h2 style={{ color: risk.color }}>{result.risk_level} Fire Risk</h2>
          <p>{locationLabel && <><strong>{locationLabel}</strong> · </>}{risk.blurb}</p>
        </div>
        <div className="risk-banner-right" style={{ color: risk.color }}>
          {result.fire_probability_pct}%
        </div>
      </div>

      {/* ── Key weather stat cards ── */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">🌡️</div>
          <div className="stat-value">{f.temperature_c}°C</div>
          <div className="stat-label">Temperature</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💧</div>
          <div className="stat-value">{f.relative_humidity}%</div>
          <div className="stat-label">Humidity</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">💨</div>
          <div className="stat-value">{f.wind_speed_kmh} <span style={{fontSize:12}}>km/h</span></div>
          <div className="stat-label">Wind Speed</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🌧️</div>
          <div className="stat-value">{f.rainfall_mm} <span style={{fontSize:12}}>mm</span></div>
          <div className="stat-label">Rainfall</div>
        </div>
      </div>

      {/* ── Gauge + feature bars ── */}
      <div className="analysis-row">
        <RiskGauge probability={result.fire_probability} riskLevel={result.risk_level} />

        {result.top_contributors?.length > 0 && (
          <div className="chart-card">
            <h3>Top Contributing Features</h3>
            <FeatureChart contributors={result.top_contributors} />
          </div>
        )}
      </div>

      {/* ── Details accordion ── */}
      <details className="details-accordion">
        <summary>📊 All 21 features used in this prediction ▾</summary>
        <div className="details-grid">
          <div>
            <p className="details-section-label">Weather</p>
            <FeatureRow label="Temperature"    value={`${f.temperature_c} °C`} />
            <FeatureRow label="Humidity"        value={`${f.relative_humidity}%`} />
            <FeatureRow label="Wind Speed"      value={`${f.wind_speed_kmh} km/h`} />
            <FeatureRow label="Rainfall"        value={`${f.rainfall_mm} mm`} />
            <FeatureRow label="Days Since Rain" value={`${f.days_since_rain} days`} />

            <p className="details-section-label">FWI System</p>
            <FeatureRow label="FFMC" value={f.FFMC} />
            <FeatureRow label="DMC"  value={f.DMC} />
            <FeatureRow label="DC"   value={f.DC} />
            <FeatureRow label="ISI"  value={f.ISI} />
            <FeatureRow label="BUI"  value={f.BUI} />
            <FeatureRow label="FWI"  value={f.FWI} />
          </div>
          <div>
            <p className="details-section-label">Satellite</p>
            <FeatureRow label="Brightness"  value={`${f.brightness_K} K`} />
            <FeatureRow label="FRP"          value={`${f.FRP_MW} MW`} />
            <FeatureRow label="LST (day)"    value={`${f.LST_day_c} °C`} />

            <p className="details-section-label">Vegetation</p>
            <FeatureRow label="NDVI"       value={f.NDVI} />
            <FeatureRow label="EVI"        value={f.EVI} />
            <FeatureRow label="Type"       value={result.vegetation_type || "—"} />

            <p className="details-section-label">Spatiotemporal</p>
            <FeatureRow label="Latitude"    value={`${f.latitude}°N`} />
            <FeatureRow label="Longitude"   value={`${f.longitude}°E`} />
            <FeatureRow label="Month"       value={f.month} />
            <FeatureRow label="Day of Year" value={f.day_of_year} />
          </div>
        </div>
        <div className="details-footnote">
          Weather: {result.metadata?.data_sources?.weather} &nbsp;·&nbsp;
          FWI: {result.metadata?.data_sources?.fwi} &nbsp;·&nbsp;
          Satellite: {result.metadata?.data_sources?.satellite} &nbsp;·&nbsp;
          Date: {result.metadata?.fetch_date}
        </div>
      </details>

    </div>
  );
}

function FeatureRow({ label, value }) {
  return (
    <div className="feature-row">
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}
