"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { useAPI } from "@/lib/api";

/**
 * WhoSawCard — "किसने ad देखी?" (08-10 user माँग: सटीक जानकारी)
 *
 * ईमानदारी पहले: Meta किसी का नाम/फ़ोन नहीं बताता (privacy क़ानून —
 * यह हमारी नहीं, दुनिया भर की सीमा है)। पर यह 3 सच्ची बातें ज़रूर देता है:
 *   1. किस उम्र के, लड़के या लड़कियों ने देखा
 *   2. कौन-से इलाके/राज्य से देखा
 *   3. Facebook पर दिखी या Instagram पर
 * हर साफ़ी = पिछले 7 दिन की असली गिनती, Meta से सीधे।
 */

function Bar({ label, pct, count }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-24 shrink-0 text-xs font-semibold text-gray-600">
        {label}
      </span>
      <div className="h-3 flex-1 overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-full rounded-full bg-brand-500"
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
      <span className="w-16 shrink-0 text-right text-xs text-gray-500">
        {count.toLocaleString("en-IN")} ({pct}%)
      </span>
    </div>
  );
}

export default function WhoSawCard() {
  const { t } = useLanguage();
  const api = useAPI();
  const [data, setData] = useState(null);

  useEffect(() => {
    api.reports
      .whoSaw()
      .then(setData)
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!data) return null;
  const empty =
    !data.age_gender.length && !data.regions.length && !data.platforms.length;

  return (
    <div className="card space-y-4">
      <p className="text-lg font-bold">👀 {t("reports.whoSaw")}</p>
      <p className="rounded-xl bg-amber-50 p-3 text-xs text-amber-800">
        {t("reports.privacyNote")}
      </p>

      {empty ? (
        <p className="text-sm text-gray-500">{t("reports.whoSawEmpty")}</p>
      ) : (
        <>
          {/* उम्र × लड़का/लड़की */}
          {data.age_gender.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-sm font-bold text-gray-700">
                {t("reports.byAge")}
              </p>
              {data.age_gender.slice(0, 8).map((r, i) => (
                <Bar
                  key={i}
                  label={`${r.age} • ${t(`gender.${r.gender}`)}`}
                  pct={r.pct}
                  count={r.impressions}
                />
              ))}
            </div>
          )}

          {/* इलाका */}
          {data.regions.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-sm font-bold text-gray-700">
                {t("reports.byRegion")}
              </p>
              {data.regions.slice(0, 6).map((r, i) => (
                <Bar
                  key={i}
                  label={r.region || r.country || "?"}
                  pct={r.pct}
                  count={r.impressions}
                />
              ))}
            </div>
          )}

          {/* FB vs Instagram */}
          {data.platforms.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-sm font-bold text-gray-700">
                {t("reports.byPlatform")}
              </p>
              {data.platforms.map((r, i) => (
                <Bar
                  key={i}
                  label={t(`platform.${r.platform}`)}
                  pct={r.pct}
                  count={r.impressions}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
