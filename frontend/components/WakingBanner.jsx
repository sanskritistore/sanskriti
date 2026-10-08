"use client";

import { useAPI } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

/**
 * ऊपर चिपकने वाली पट्टी — Render free server सोकर जागते समय (30-60 सेकंड)
 * ग्राहक को बताती है कि सब ठीक है, बस थोड़ा रुको। Error की जगह समझदारी!
 */
export default function WakingBanner() {
  const { waking } = useAPI();
  const { t } = useLanguage();

  if (!waking) return null;

  return (
    <div className="fixed inset-x-0 top-0 z-[9999] bg-orange-500 px-4 py-2.5 text-center text-white shadow-lg">
      <p className="text-sm font-semibold">{t("waking.title")}</p>
      <p className="text-xs opacity-90">{t("waking.sub")}</p>
    </div>
  );
}
