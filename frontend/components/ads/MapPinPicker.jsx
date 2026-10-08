"use client";

import { useEffect, useRef, useState } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { INDIA_CENTER, STATE_ZOOM, CITY_ZOOM } from "@/lib/data/india-states";

/**
 * MapPinPicker — "नक्शे से सुई लगाओ" (08-10)
 *
 * जब खोज में जगह न मिले (मुफ़्त map database में छोटी जगहें कम हैं),
 * user खुद नक्शे पर टैप करके सुई लगाए — Google जैसा अनुभव, मुफ़्त में।
 * Leaflet + OpenStreetMap (CDN से, कोई key नहीं)।
 *
 * बिंदु 18 (No Hardcoding): केंद्र hardcode नहीं — state का नाम live
 * geocode करके नक्शा उस राज्य पर खोलते हैं; असफल हो तो भारत-केंद्र सहारा।
 */
export default function MapPinPicker({ stateName, initialName, onPick, onClose }) {
  const { t } = useLanguage();
  const mapDivRef = useRef(null);
  const mapRef = useRef(null); // {map, marker}
  const [pin, setPin] = useState(null); // {lat, lon}
  const [name, setName] = useState(initialName || "");
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function boot() {
      // Leaflet CSS/JS CDN से (एक बार ही जोड़ें)
      if (!document.getElementById("leaflet-css")) {
        const link = document.createElement("link");
        link.id = "leaflet-css";
        link.rel = "stylesheet";
        link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
        document.head.appendChild(link);
      }
      if (!window.L) {
        await new Promise((resolve, reject) => {
          const s = document.createElement("script");
          s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
          s.onload = resolve;
          s.onerror = reject;
          document.body.appendChild(s);
        });
      }
      if (cancelled || !mapDivRef.current) return;

      // केंद्र: state नाम से live geocode (hardcode नहीं — बिंदु 18)
      let center = INDIA_CENTER;
      let zoom = STATE_ZOOM;
      try {
        const resp = await fetch(
          `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(
            `${stateName}, India`
          )}&format=json&limit=1&countrycodes=in`,
          { headers: { "Accept-Language": "en" } }
        );
        const rows = await resp.json();
        if (rows.length > 0) {
          center = [parseFloat(rows[0].lat), parseFloat(rows[0].lon)];
          zoom = CITY_ZOOM;
        }
      } catch {
        /* सहारा: भारत-केंद्र */
      }
      if (cancelled) return;

      const map = window.L.map(mapDivRef.current).setView(center, zoom);
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap",
        maxZoom: 19,
      }).addTo(map);

      let marker = null;
      map.on("click", (e) => {
        const { lat, lng } = e.latlng;
        if (marker) {
          marker.setLatLng([lat, lng]);
        } else {
          marker = window.L.circleMarker([lat, lng], {
            radius: 11,
            color: "#ffffff",
            weight: 3,
            fillColor: "#16a34a",
            fillOpacity: 0.95,
          }).addTo(map);
        }
        setPin({ lat, lon: lng });
      });
      mapRef.current = { map };
    }

    boot().catch(() => setLoadError(true));
    return () => {
      cancelled = true;
      try {
        mapRef.current?.map?.remove();
      } catch {
        /* ignore */
      }
      mapRef.current = null;
    };
  }, [stateName]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-3">
      <div className="w-full max-w-md space-y-3 rounded-2xl bg-white p-4">
        <p className="font-bold text-gray-800">{t("ads.mapHint")}</p>
        {loadError ? (
          <p className="rounded-xl bg-red-50 p-3 text-sm text-red-600">
            {t("ads.mapError")}
          </p>
        ) : (
          <div ref={mapDivRef} className="h-72 w-full rounded-xl bg-gray-100" />
        )}
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("ads.mapNameLabel")}
          className="w-full rounded-xl border border-gray-300 p-3"
        />
        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 rounded-xl border border-gray-300 py-3 font-semibold"
          >
            {t("cancel")}
          </button>
          <button
            disabled={!pin || !name.trim()}
            onClick={() => onPick({ name: name.trim(), lat: pin.lat, lon: pin.lon })}
            className="flex-1 rounded-xl bg-green-600 py-3 font-bold text-white disabled:opacity-40"
          >
            {t("ads.mapConfirm")}
          </button>
        </div>
      </div>
    </div>
  );
}
