"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { useAPI } from "@/lib/api";

/**
 * BillingCard — "गलत खाते में पैसा न जाए" सुरक्षा-डिब्बा (08-10 user माँग)
 *
 * दुकानदार को 3 भरोसे देता है:
 * 1. LIVE बैलेंस दिखे (कम हो तो लाल चेतावनी — ad रुकने से पहले पता चले)
 * 2. पैसा डालने से पहले खाते का नाम + आख़िरी अंक दिखे (पुष्टि करके ही आगे)
 * 3. Button सीधे उसी खाते का billing page खोले (asset_id lock) —
 *    menu ढूँढने की ज़रूरत ही नहीं, गलत खाता असंभव।
 */
export default function BillingCard() {
  const { t } = useLanguage();
  const api = useAPI();
  const [info, setInfo] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  useEffect(() => {
    api.billing
      .status()
      .then(setInfo)
      .catch(() => {}); // Meta बंद हो तो card चुपचाप छिप जाए
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!info) return null;

  return (
    <>
      <div
        className={`card space-y-2 border-2 ${
          info.low_balance ? "border-red-300 bg-red-50" : "border-green-200"
        }`}
      >
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-gray-500">
            {t("billing.title")}
          </p>
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-600">
            {info.account_name} •••{info.account_last4}
          </span>
        </div>
        <p
          className={`text-3xl font-bold ${
            info.low_balance ? "text-red-600" : "text-green-700"
          }`}
        >
          ₹{info.balance_rupees.toLocaleString("en-IN")}
        </p>
        {info.low_balance ? (
          <p className="text-sm font-semibold text-red-600">
            {t("billing.lowWarn")}
          </p>
        ) : (
          <p className="text-xs text-gray-400">
            {t("billing.spentSoFar")}: ₹
            {info.spent_rupees.toLocaleString("en-IN")}
          </p>
        )}
        {info.today_spend_rupees !== null && (
          <p className="text-xs text-gray-500">
            {t("billing.todaySpend")}: ₹
            {info.today_spend_rupees.toLocaleString("en-IN")}
          </p>
        )}
        <button
          className="btn-primary w-full"
          onClick={() => setConfirmOpen(true)}
        >
          {t("billing.addMoney")}
        </button>

        {/* 🔒 Prepaid सच्चाई — Meta खुद की सीमा prepaid खातों पर नहीं लगने
            देता (08-10 test: error 1487840), और ज़रूरत भी नहीं: घड़े में जितना
            पानी, उतना ही निकलेगा। यही user की माँगी हुई सुरक्षा पहले से है। */}
        <div className="rounded-xl bg-green-50 p-3">
          <p className="text-xs font-bold text-green-800">
            {t("billing.prepaidTitle")}
          </p>
          <p className="mt-0.5 text-xs text-green-700">
            {t("billing.prepaidHint")}
          </p>
        </div>
      </div>

      {/* पुष्टि डिब्बा — नाम दिखाए बिना आगे नहीं (गलत खाता असंभव) */}
      {confirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-sm space-y-4 rounded-2xl bg-white p-5 text-center">
            <p className="text-lg font-bold">{t("billing.confirmTitle")}</p>
            <div className="rounded-xl bg-green-50 p-4">
              <p className="text-2xl font-bold text-green-800">
                {info.account_name}
              </p>
              <p className="mt-1 text-sm text-gray-500">
                {t("billing.accountEnds")}: •••{info.account_last4}
              </p>
              <p className="mt-2 text-sm text-gray-600">
                {t("billing.confirmHint")}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                className="flex-1 rounded-xl border border-gray-300 py-3 font-semibold"
                onClick={() => setConfirmOpen(false)}
              >
                {t("cancel")}
              </button>
              <button
                className="flex-1 rounded-xl bg-green-600 py-3 font-bold text-white"
                onClick={() => {
                  window.open(info.add_money_url, "_blank", "noopener");
                  setConfirmOpen(false);
                }}
              >
                {t("billing.confirmGo")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
