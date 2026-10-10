"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { API_BASE } from "@/lib/api";
import { formatRupees } from "@/lib/utils";

/**
 * 🏪 Public मिनी-दुकान — customer के लिए (बिना login)!
 *
 * 10-10 user माँग (option B): "customer सारी photos tap करके full-page
 * देखे" — Meta ads में photo बड़ी करके नहीं दिखती, इसलिए दुकान का अपना
 * public page। Link: /shop/?t=1
 *
 * Customer flow: products देखो → tap करो → सारी photos (tap पर FULLSCREEN)
 * → WhatsApp से order।
 */
export default function ShopPage() {
  return (
    <Suspense
      fallback={<p className="py-16 text-center text-gray-400">लोड हो रहा…</p>}
    >
      <ShopInner />
    </Suspense>
  );
}

/** WhatsApp deep link — 10 अंक हों तो 91 (India) जोड़ो */
function waLink(phone, text) {
  let num = String(phone || "").replace(/\D/g, "");
  if (num.length === 10) num = "91" + num;
  return `https://wa.me/${num}?text=${encodeURIComponent(text)}`;
}

function ShopInner() {
  const searchParams = useSearchParams();
  const tenantId = searchParams.get("t") || "1";

  const [shop, setShop] = useState(null);
  const [error, setError] = useState("");
  const [product, setProduct] = useState(null); // खुला हुआ product
  const [photoIdx, setPhotoIdx] = useState(0); // बड़ी photo कौन सी
  const [fullscreen, setFullscreen] = useState(false); // full-page photo

  useEffect(() => {
    fetch(`${API_BASE}/shop/${tenantId}`)
      .then((r) => {
        if (!r.ok) throw new Error("bad");
        return r.json();
      })
      .then(setShop)
      .catch(() => setError("दुकान नहीं मिली — link फिर से जाँचें 🙏"));
  }, [tenantId]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
        <p className="rounded-2xl bg-white p-6 text-center font-semibold text-red-600 shadow">
          {error}
        </p>
      </div>
    );
  }
  if (!shop) {
    return (
      <p className="py-16 text-center text-gray-400">लोड हो रहा…</p>
    );
  }

  const photos = product?.photos || [];
  const curPhoto = photos[photoIdx] || photos[0];

  function openProduct(p) {
    setProduct(p);
    setPhotoIdx(0);
    window.scrollTo(0, 0);
  }

  function orderText(p) {
    return `नमस्ते! 🙏 मुझे यह चाहिए:\n\n• ${p.name} — ${formatRupees(p.price)}\n\n(${shop.name} की online दुकान से)`;
  }

  return (
    <div className="mx-auto min-h-screen max-w-lg bg-gray-50 pb-20">
      {/* ── दुकान की पहचान ── */}
      <header className="sticky top-0 z-10 bg-gradient-to-r from-slate-900 to-blue-900 px-4 pb-4 pt-5 text-white shadow-lg">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="truncate text-xl font-extrabold tracking-tight">
              🖨️ {shop.name}
            </h1>
            <p className="mt-0.5 text-sm text-blue-200">
              {shop.google_rating
                ? `⭐ ${shop.google_rating.toFixed(1)} · ${shop.google_reviews_count || ""} Google reviews`
                : shop.city || ""}
            </p>
          </div>
          <a
            href={waLink(shop.phone, `नमस्ते! ${shop.name} से बात करनी है 🙏`)}
            target="_blank"
            rel="noopener noreferrer"
            className="flex flex-none items-center gap-1.5 rounded-full bg-green-500 px-4 py-2.5 text-sm font-bold text-white shadow active:scale-95"
          >
            💬 WhatsApp
          </a>
        </div>
      </header>

      {/* ── product detail खुला हो तो ── */}
      {product ? (
        <div className="space-y-4 p-4">
          <button
            onClick={() => setProduct(null)}
            className="flex items-center gap-2 font-bold text-brand-600"
          >
            ← सारे products
          </button>

          {/* बड़ी photo — tap करने पर FULL PAGE (user की मूल माँग!) */}
          {curPhoto ? (
            <button
              onClick={() => setFullscreen(true)}
              className="block w-full overflow-hidden rounded-2xl bg-white shadow"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={curPhoto.url}
                alt={product.name}
                className="aspect-square w-full object-cover"
              />
              <p className="py-2 text-center text-xs font-semibold text-gray-400">
                🔍 photo पर tap करें — full page में दिखेगी
              </p>
            </button>
          ) : (
            <div className="flex aspect-square items-center justify-center rounded-2xl bg-white text-6xl shadow">
              📷
            </div>
          )}

          {/* छोटी photos — tap पर बड़ी बदलो */}
          {photos.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-1">
              {photos.map((ph, i) => (
                <button
                  key={ph.id}
                  onClick={() => setPhotoIdx(i)}
                  className={`h-20 w-20 flex-none overflow-hidden rounded-xl ${
                    i === photoIdx
                      ? "ring-4 ring-brand-500"
                      : "ring-1 ring-gray-200"
                  }`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={ph.url}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}

          <div>
            <h2 className="text-xl font-extrabold text-gray-900">
              {product.name}
            </h2>
            <p className="mt-1 text-2xl font-extrabold text-brand-600">
              {formatRupees(product.price)}
            </p>
          </div>

          <a
            href={waLink(shop.phone, orderText(product))}
            target="_blank"
            rel="noopener noreferrer"
            className="block rounded-2xl bg-green-500 py-4 text-center text-lg font-extrabold text-white shadow-lg active:scale-95"
          >
            💬 WhatsApp पर order करें
          </a>
          <p className="text-center text-xs text-gray-400">
            button दबाते ही WhatsApp खुलेगा — message तैयार मिलेगा, बस भेजें!
          </p>
        </div>
      ) : (
        /* ── products की grid ── */
        <div className="p-4">
          <p className="mb-3 font-bold text-gray-700">
            🛍️ हमारे products — किसी पर भी tap करें
          </p>
          <div className="grid grid-cols-2 gap-3">
            {shop.products.map((p) => {
              const main = p.photos[0];
              return (
                <button
                  key={p.id}
                  onClick={() => openProduct(p)}
                  className="overflow-hidden rounded-2xl bg-white text-left shadow transition-transform active:scale-95"
                >
                  {main ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img
                      src={main.url}
                      alt={p.name}
                      className="aspect-square w-full object-cover"
                    />
                  ) : (
                    <div className="flex aspect-square items-center justify-center bg-gray-100 text-4xl">
                      📷
                    </div>
                  )}
                  <div className="p-2.5">
                    <p className="line-clamp-2 text-sm font-bold text-gray-900">
                      {p.name}
                    </p>
                    <div className="mt-1 flex items-center justify-between">
                      <span className="font-extrabold text-brand-600">
                        {formatRupees(p.price)}
                      </span>
                      {p.photos.length > 1 && (
                        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-500">
                          📸 {p.photos.length}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* पता + branding */}
          {(shop.address || shop.city) && (
            <p className="mt-6 rounded-2xl bg-white p-4 text-center text-sm text-gray-600 shadow">
              📍 {shop.address}
              {shop.address && shop.city ? ", " : ""}
              {shop.city}
            </p>
          )}
          <p className="mt-4 text-center text-xs text-gray-300">
            ⚡ Sanskriti से बनी online दुकान
          </p>
        </div>
      )}

      {/* ── FULL PAGE photo (lightbox) ── */}
      {fullscreen && curPhoto && (
        <div
          className="fixed inset-0 z-50 flex flex-col bg-black"
          onClick={() => setFullscreen(false)}
        >
          <div className="flex items-center justify-between p-3 text-white">
            <span className="text-sm font-semibold">
              {photoIdx + 1} / {photos.length}
            </span>
            <button className="rounded-full bg-white/20 px-3 py-1 text-lg font-bold">
              ✕
            </button>
          </div>
          <div className="flex flex-1 items-center justify-center overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={curPhoto.url}
              alt={product.name}
              className="max-h-full max-w-full object-contain"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
          {photos.length > 1 && (
            <div
              className="flex items-center justify-between p-4"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                onClick={() =>
                  setPhotoIdx((i) => (i - 1 + photos.length) % photos.length)
                }
                className="rounded-full bg-white/20 px-5 py-2 text-2xl font-bold text-white"
              >
                ‹
              </button>
              <a
                href={waLink(shop.phone, orderText(product))}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-full bg-green-500 px-5 py-2.5 font-bold text-white"
              >
                💬 Order
              </a>
              <button
                onClick={() => setPhotoIdx((i) => (i + 1) % photos.length)}
                className="rounded-full bg-white/20 px-5 py-2 text-2xl font-bold text-white"
              >
                ›
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
