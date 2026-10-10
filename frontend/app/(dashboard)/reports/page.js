"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { useAPI } from "@/lib/api";
import { formatRupees } from "@/lib/utils";
import LanguageToggle from "@/components/ui/LanguageToggle";
import WhoSawCard from "@/components/reports/WhoSawCard";
import ScoreCard from "@/components/reports/ScoreCard";

/**
 * Reports — the whole page answers ONE question in money language:
 *   "₹X खर्च → Y ग्राहक" (₹X spent → Y customers)
 * Plus a simple per-campaign हिसाब. No charts, no jargon.
 */
export default function ReportsPage() {
  const { t } = useLanguage();
  const api = useAPI();

  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.reports
      .summary()
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const campaigns = summary?.campaigns ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("reports.title")}</h1>
        <LanguageToggle />
      </div>

      {loading ? (
        <p className="py-8 text-center text-gray-400">{t("loading")}</p>
      ) : !summary || campaigns.length === 0 ? (
        <div className="card py-10 text-center">
          <div className="text-4xl">📊</div>
          <p className="mt-3 text-gray-500">{t("reports.empty")}</p>
        </div>
      ) : (
        <>
          {/* 📊 असली Score Card — Meta से सीधे (10-10: पुराना DB hero ₹0
              दिखाता था, असली खर्च Meta पर होता है — गलत numbers मना है) */}
          <ScoreCard />

          {/* 👀 किसने ad देखी — उम्र/इलाका/FB-Instagram बंटवारा (08-10) */}
          <WhoSawCard />

          {/* Per-campaign हिसाब */}
          <div className="space-y-3">
            <h2 className="font-bold text-gray-700">
              {t("reports.campaigns")}
            </h2>
            {campaigns.map((c) => (
              <div key={c.id} className="card">
                <div className="flex items-center justify-between">
                  <p className="font-semibold">{c.name}</p>
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${
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
                <div className="mt-2 flex justify-between text-sm text-gray-500">
                  <span>
                    {t("reports.budget")}: {formatRupees(c.budget_total)}
                  </span>
                  <span>
                    {t("reports.spent")}: {formatRupees(c.budget_spent)}
                  </span>
                </div>
                {/* बजट की पट्टी — कितना खर्च हुआ */}
                <div className="mt-2 h-2 w-full rounded-full bg-gray-100">
                  <div
                    className="h-2 rounded-full bg-brand-500"
                    style={{
                      width: `${Math.min(
                        100,
                        c.budget_total > 0
                          ? (c.budget_spent / c.budget_total) * 100
                          : 0
                      )}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
