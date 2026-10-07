"use client";

import { useLanguage } from "@/lib/LanguageContext";
import { formatRupees } from "@/lib/utils";

/**
 * AdPreviewCard — Facebook/Instagram feed जैसी ad की झलक।
 *
 * Launch से पहले tenant देखे कि उसकी ad असल में कैसी दिखेगी।
 * (User की माँग: "jab tak live na dekhlu kuch samjh nahi aata" —
 *  पहले दिखाओ, फिर पैसा लगाओ!)
 */
export default function AdPreviewCard({ product, creative }) {
  const { t } = useLanguage();
  const imageSrc = product?.photo || null;

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      {/* Header: दुकान + sponsored tag */}
      <div className="flex items-center gap-2 p-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-500 text-lg text-white">
          🏪
        </div>
        <div className="leading-tight">
          <p className="text-sm font-semibold">{t("ads.shopName")}</p>
          <p className="text-xs text-gray-500">{t("ads.sponsored")} · 🌐</p>
        </div>
      </div>

      {/* Ad का मुख्य text */}
      <p className="whitespace-pre-line px-3 pb-2 text-sm text-gray-800">
        {creative?.primary_text}
      </p>

      {/* Product की photo — पूरी दिखाएँ (काटें नहीं) */}
      {imageSrc ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={imageSrc} alt={product?.name || "ad"} className="w-full" />
      ) : (
        <div className="flex h-48 w-full items-center justify-center bg-gray-100 text-5xl">
          📦
        </div>
      )}

      {/* नीचे की पट्टी: headline + कीमत + WhatsApp button */}
      <div className="flex items-center justify-between gap-2 bg-gray-100 px-3 py-2">
        <div className="min-w-0 leading-tight">
          <p className="truncate text-sm font-bold text-gray-900">
            {creative?.headline}
          </p>
          <p className="text-xs text-gray-500">
            {product ? formatRupees(product.price) : ""}
          </p>
        </div>
        <span className="shrink-0 rounded-lg bg-green-500 px-3 py-2 text-xs font-bold text-white">
          💬 {t("ads.whatsappCta")}
        </span>
      </div>
    </div>
  );
}
