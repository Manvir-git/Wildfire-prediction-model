import { useState, useCallback, useEffect } from "react";
import MapView from "./components/MapView";
import RiskResult from "./components/RiskResult";
import API_BASE from "./config";
import "./App.css";

const NOMINATIM = "https://nominatim.openstreetmap.org/search";

const STEPS = [
  "Fetching real-time weather from Open-Meteo…",
  "Computing Fire Weather Index components…",
  "Estimating vegetation & satellite features…",
  "Running XGBoost inference…",
];

export default function App() {
  const [query, setQuery]           = useState("");
  const [coords, setCoords]         = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading]       = useState(false);
  const [stepIdx, setStepIdx]       = useState(0);
  const [result, setResult]         = useState(null);
  const [error, setError]           = useState(null);

  const searchPlace = useCallback(async (q) => {
    if (q.trim().length < 3) { setSuggestions([]); return; }
    try {
      const url = `${NOMINATIM}?q=${encodeURIComponent(q)}&format=json&limit=5&countrycodes=in`;
      const res = await fetch(url);
      const data = await res.json();
      setSuggestions(data.map(p => ({
        label: p.display_name,
        lat: parseFloat(p.lat),
        lon: parseFloat(p.lon),
      })));
    } catch { setSuggestions([]); }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => searchPlace(query), 400);
    return () => clearTimeout(t);
  }, [query, searchPlace]);

  const pickSuggestion = (s) => {
    setCoords({ lat: s.lat, lon: s.lon, label: s.label.split(",")[0] });
    setQuery(s.label.split(",")[0]);
    setSuggestions([]);
    setResult(null);
    setError(null);
  };

  // Called by MapView on moveend (drag/zoom) and on geolocation
  const handlePinMove = (lat, lon) => {
    setCoords(prev => {
      // Keep the place label if the move is tiny (search-triggered pan settling)
      const label = (prev && Math.abs(prev.lat - lat) < 0.001 && Math.abs(prev.lon - lon) < 0.001)
        ? prev.label
        : `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`;
      return { lat, lon, label };
    });
    setResult(null);
    setError(null);
  };

  const runPrediction = async () => {
    if (!coords) return;
    setLoading(true);
    setStepIdx(0);
    setResult(null);
    setError(null);

    let i = 0;
    const interval = setInterval(() => {
      i = Math.min(i + 1, STEPS.length - 1);
      setStepIdx(i);
    }, 950);

    try {
      const res = await fetch(`${API_BASE}/api/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat: coords.lat, lon: coords.lon }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Prediction failed.");
      setResult(data);
    } catch (e) {
      setError(e.message);
    } finally {
      clearInterval(interval);
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <span className="header-icon">🔥</span>
          <div>
            <h1>Fire Risk Predictor</h1>
            <p className="header-sub">India · Real-time Weather · XGBoost Ensemble</p>
          </div>
          <span className="header-badge">CSE439 · LPU 2026</span>
        </div>
      </header>

      <main className="main">
        {/* Search */}
        <section className="search-panel">
          <div className="search-box">
            <input
              type="text"
              placeholder="Search any Indian location — e.g. Uttarakhand, Simlipal, Bandipur…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && suggestions[0] && pickSuggestion(suggestions[0])}
            />
            <button
              className="btn-predict"
              onClick={runPrediction}
              disabled={!coords || loading}
            >
              {loading ? "Analysing…" : "Analyse Risk"}
            </button>
          </div>

          {suggestions.length > 0 && (
            <ul className="suggestions">
              {suggestions.map((s, i) => (
                <li key={i} onClick={() => pickSuggestion(s)}>
                  <span className="sug-icon">📍</span>
                  {s.label}
                </li>
              ))}
            </ul>
          )}

          {coords && (
            <div className="coords-badge">
              📌 {coords.label}
            </div>
          )}
        </section>

        <div className="content-grid">
          {/* Left: map */}
          <div>
            <section className="map-section">
              <MapView coords={coords} onPinMove={handlePinMove} />
            </section>
            <p className="map-hint">Drag the map to position the pin · Zoom in for precision</p>
          </div>

          {/* Right: result / loading / placeholder */}
          <div>
            {loading && (
              <div className="glass loading-panel">
                <div className="spinner" />
                <div className="loading-steps">
                  {STEPS.map((s, i) => (
                    <div
                      key={i}
                      className={`loading-step ${i < stepIdx ? "done" : i === stepIdx ? "active" : ""}`}
                    >
                      <span className="step-dot" />
                      {i < stepIdx ? "✓ " : ""}{s}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {error && !loading && (
              <div className="error-panel">⚠️ {error}</div>
            )}

            {result && !loading && (
              <RiskResult result={result} locationLabel={coords?.label} />
            )}

            {!result && !loading && !error && (
              <div className="placeholder-panel">
                <div className="big-icon">🗺️</div>
                <p>Search or click on the map to select a location, then click <strong>Analyse Risk</strong>.</p>
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="footer">
        CSE439 Dissertation-I · Manvir Singh &amp; Kushagra Mangalam · LPU 2026
        &nbsp;·&nbsp; Weather: Open-Meteo · Model: XGBoost · FWI: Van Wagner 1987
      </footer>
    </div>
  );
}
