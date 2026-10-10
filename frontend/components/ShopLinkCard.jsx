"use client";

import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { useAPI } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

/**
 * 🏪 मेरी online दुकान card — products page के ऊपर।
 * दुकान का public link copy करो या QR code दिखाओ/download करो —
 * QR छापकर counter पर लगाओ, ग्राहक scan करके पूरी दुकान देखेंगे!
 * (10-10 user idea: QR counter/pamphlet पर)
 */
export default function ShopLinkCard() {
  const { t } = useLanguage();
  const api = useAPI();
  const [shopUrl, setShopUrl] = useState(null);
  const [qrData, setQrData] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.business
      .get()
      .then((b) => {
        if (b?.id) setShopUrl(`${window.location.origin}/shop/?t=${b.id}`);
      })
      .catch(() => {});
  }, []);

  if (!shopUrl) return null;

  async function openQr() {
    const data = await QRCode.toDataURL(shopUrl, {
      width: 640,
      margin: 2,
      color: { dark: "#0f172a", light: "#ffffff" },
    });
    setQrData(data);
  }

  function copy() {
    navigator.clipboard.writeText(shopUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="card border-2 border-brand-200 bg-brand-50">
      <p className="font-bold text-brand-800">{t("shop.cardTitle")}</p>
      <p className="mt-1 text-sm text-brand-600">{t("shop.cardHint")}</p>
      <p className="mt-2 break-all rounded-lg bg-white px-3 py-2 text-xs text-gray-500">
        {shopUrl}
      </p>
      <div className="mt-3 flex gap-2">
        <button
          onClick={copy}
          className="flex-1 rounded-xl bg-brand-600 py-3 font-semibold text-white"
        >
          {copied ? t("shop.copied") : t("shop.copy")}
        </button>
        <button
          onClick={openQr}
          className="flex-1 rounded-xl border-2 border-brand-300 bg-white py-3 font-semibold text-brand-700"
        >
          {t("shop.showQr")}
        </button>
      </div>

      {/* QR modal */}
      {qrData && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"
          onClick={() => setQrData(null)}
        >
          <div
            className="w-full max-w-sm rounded-2xl bg-white p-6 text-center"
            onClick={(e) => e.stopPropagation()}
          >
            <p className="font-bold text-gray-800">{t("shop.qrTitle")}</p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={qrData}
              alt="दुकान का QR code"
              className="mx-auto mt-4 w-full rounded-xl border-4 border-gray-100"
            />
            <a
              href={qrData}
              download="meri-dukkan-qr.png"
              className="mt-4 block rounded-xl bg-brand-600 py-3 font-semibold text-white"
            >
              {t("shop.download")}
            </a>
            <button
              onClick={() => setQrData(null)}
              className="mt-3 text-sm text-gray-400 underline"
            >
              {t("close")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
