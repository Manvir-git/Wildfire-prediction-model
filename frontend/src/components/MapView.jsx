import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const INDIA_CENTER = [22.5, 82.0];
const INDIA_ZOOM   = 5;

export default function MapView({ coords, onPinMove }) {
  const wrapRef     = useRef(null);   // outer div (position:relative)
  const mapDivRef   = useRef(null);   // inner div (Leaflet target)
  const leafletRef  = useRef(null);
  const skipRef     = useRef(false);  // suppress moveend after programmatic pan
  const cbRef       = useRef(onPinMove);
  const [dragging, setDragging] = useState(false);

  useEffect(() => { cbRef.current = onPinMove; }, [onPinMove]);

  // ── Init map once ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (leafletRef.current) return;

    const map = L.map(mapDivRef.current, {
      center: INDIA_CENTER,
      zoom: INDIA_ZOOM,
      zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap contributors",
      maxZoom: 18,
    }).addTo(map);

    map.on("dragstart", () => setDragging(true));
    map.on("zoomstart", () => setDragging(true));

    map.on("moveend", () => {
      setDragging(false);
      if (skipRef.current) { skipRef.current = false; return; }
      const { lat, lng } = map.getCenter();
      cbRef.current(parseFloat(lat.toFixed(6)), parseFloat(lng.toFixed(6)));
    });

    leafletRef.current = map;

    // ── Geolocation on load ─────────────────────────────────────────────────
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        ({ coords: { latitude: lat, longitude: lon } }) => {
          // Use leafletRef (not closed-over map) — StrictMode destroys+recreates
          const m = leafletRef.current;
          if (!m || !m._container) return;
          skipRef.current = true;
          m.setView([lat, lon], 11, { animate: false });
          cbRef.current(parseFloat(lat.toFixed(6)), parseFloat(lon.toFixed(6)));
        },
        () => {}
      );
    }

    return () => { map.remove(); leafletRef.current = null; };
  }, []);

  // ── Pan map when parent sets coords (search selection) ──────────────────────
  useEffect(() => {
    const map = leafletRef.current;
    if (!map || !map._container || !coords) return;
    const c = map.getCenter();
    if (Math.abs(c.lat - coords.lat) < 0.0001 && Math.abs(c.lng - coords.lon) < 0.0001) return;
    skipRef.current = true;
    map.setView([coords.lat, coords.lon], Math.max(map.getZoom(), 10), { animate: true });
  }, [coords]);

  return (
    <div ref={wrapRef} style={{ position: "relative", width: "100%", height: "420px" }}>

      {/* Leaflet map */}
      <div ref={mapDivRef} style={{ width: "100%", height: "100%" }} />

      {/* Shadow on map surface */}
      <div className={`pin-shadow ${dragging ? "pin-shadow--lifted" : ""}`} />

      {/* Fixed center teardrop pin */}
      <div className={`pin-overlay ${dragging ? "pin-overlay--lifted" : ""}`}>
        <svg width="36" height="52" viewBox="0 0 36 52" fill="none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <filter id="pin-drop" x="-30%" y="-20%" width="160%" height="160%">
              <feDropShadow dx="0" dy="3" stdDeviation="3" floodColor="#00000055" />
            </filter>
          </defs>
          {/* Teardrop body */}
          <path
            d="M18 0C8.059 0 0 8.059 0 18C0 31.5 18 52 18 52C18 52 36 31.5 36 18C36 8.059 27.941 0 18 0Z"
            fill="#e8380c"
            filter="url(#pin-drop)"
          />
          {/* Inner highlight ring */}
          <circle cx="18" cy="18" r="9" fill="white" opacity="0.95" />
          <circle cx="18" cy="18" r="5" fill="#e8380c" />
        </svg>
      </div>

      {/* Coordinates readout while dragging */}
      {coords && (
        <div className={`pin-coords ${dragging ? "pin-coords--visible" : ""}`}>
          {coords.lat.toFixed(4)}°N &nbsp; {coords.lon.toFixed(4)}°E
        </div>
      )}
    </div>
  );
}
