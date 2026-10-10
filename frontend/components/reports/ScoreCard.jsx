"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { useAPI } from "@/lib/api";
import { formatRupees } from "@/lib/utils";

/**
 * 📊 ScoreCard — "आज मेरी ad ने क्या कमाया?" (10-10 user माँग)
 *
 * User का सवाल था: "सारा score card अपने software पर आए — किसने देखी,
 * कहाँ तक गई, कितना खर्च — वरना ads चलाने का क्या फ़ायदा?"
 *
 * असली numbers सीधे Meta से (DB के ₹0 वाले अंदाज़े नहीं):
 *   👀 कितने लोगों तक पहुँची (reach)   🔁 कुल कितनी बार दिखी (impressions)
 *   👆 कितनों ने छुआ (clicks)          💬 कितनों ने WhatsApp किया (messages)
 *   💰 कितना खर्च हुआ (spend)
 *
 * ईमानदार note हमेशा साथ: नाम/फ़ोन क़ानूनन नहीं मिलते (privacy)।
 * 📍 5 km वाली बात: ad targeting से सिर्फ़ उसी घेरे में दिखती है।
 */

function Num({ emoji, label, value, sub }) {
  return (
    <div className="rounded-xl bg-white/70 p-3 text-center shadow-sm">
      <div className="text-xl">{emoji}</div>
      <p className="mt-1 text-lg font-bold leading-tight text-gray-900">
        {value}
      </p>
      <p className="text-[11px] font-medium text-gray-500">{label}</p>
      {sub ? (
        <p className="mt-0.5 text-[10px] text-gray-400">{sub}</p>
      ) : null}
    </div>
  );
}

export default function ScoreCard() {
  const { t } = useLanguage();
  const api = useAPI();
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.reports
      .scoreCard()
      .then(setData)
      .catch(() => setFailed(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (failed || !data) return null;

  const d = data.today || {};
  const w = data.week || {};
  const camps = data.campaigns || [];
  const nothing = !d.impressions && !w.impressions;

  return (
    <div className="card border-2 border-brand-100 bg-gradient-to-b from-brand-50 to-white">
      <h2 className="flex items-center gap-2 font-bold text-gray-800">
        <span className="text-xl">📊</span> {t("reports.scoreTitle")}
      </h2>

      {nothing ? (
        <p className="mt-3 text-center text-sm text-gray-500">
          {t("reports.scoreEmpty")}
        </p>
      ) : (
        <>
          {/* आज की 5 असली गिनतियाँ */}
          <div className="mt-3 grid grid-cols-3 gap-2">
            <Num
              emoji="👀"
              label={t("reports.scReached")}
              value={(d.reach ?? 0).toLocaleString("en-IN")}
              sub={t("reports.scPeople")}
            />
            <Num
              emoji="🔁"
              label={t("reports.scShown")}
              value={(d.impressions ?? 0).toLocaleString("en-IN")}
              sub={t("reports.scTimes")}
            />
            <Num
              emoji="👆"
              label={t("reports.scClicks")}
              value={(d.clicks ?? 0).toLocaleString("en-IN")}
            />
            <Num
              emoji="💬"
              label={t("reports.scWhatsapp")}
              value={(d.messages ?? 0).toLocaleString("en-IN")}
            />
            <Num
              emoji="💰"
              label={t("reports.scSpent")}
              value={formatRupees(d.spend ?? 0)}
            />
            <Num
              emoji="🎯"
              label={t("reports.scCostPerClick")}
              value={
                d.clicks > 0
                  ? formatRupees((d.spend ?? 0) / d.clicks)
                  : "—"
              }
            />
          </div>

          {/* 7 दिन का हिसाब — एक लाइन में */}
          <p className="mt-3 rounded-lg bg-brand-100/60 px-3 py-2 text-center text-xs font-semibold text-brand-800">
            {t("reports.scWeekLine", {
              reach: (w.reach ?? 0).toLocaleString("en-IN"),
              clicks: (w.clicks ?? 0).toLocaleString("en-IN"),
              spend: formatRupees(w.spend ?? 0),
            })}
          </p>

          {/* हर चलती ad का अपना हिसाब */}
          {camps.length > 0 && (
            <div className="mt-3 space-y-2">
              {camps.map((c) => (
                <div
                  key={c.id}
                  className="rounded-lg bg-white/80 p-2.5 shadow-sm"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-xs font-semibold text-gray-700">
                      {c.name}
                    </p>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                        c.status === "active"
                          ? "bg-green-100 text-hindi-success"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {c.status === "active"
                        ? t("reports.active")
                        : t("reports.paused")}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] text-gray-500">
                    {t("reports.scCampLine", {
                      reach: (c.today.reach ?? 0).toLocaleString("en-IN"),
                      clicks: (c.today.clicks ?? 0).toLocaleString("en-IN"),
                      spend: formatRupees(c.today.spend ?? 0),
                    })}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* 📍 + ईमानदारी — दो छोटी सच्ची बातें */}
          <p className="mt-3 text-center text-[11px] text-gray-400">
            {t("reports.scRadiusNote")}
          </p>
          <p className="mt-1 text-center text-[11px] text-gray-400">
            {t("reports.scHonestNote")}
          </p>
        </>
      )}
    </div>
  );
}
