"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useLanguage } from "@/lib/LanguageContext";
import { useAPI } from "@/lib/api";
import { formatRupees } from "@/lib/utils";

const MAX_DIM = 1600; // PhotoPicker जैसी compressing — भारी फ़ोन photos हल्की हो जाएँ
const JPEG_QUALITY = 0.85;
const MAX_PHOTOS = 7;

/**
 * Product Album — एक product की सारी photos (10-10 user माँग)।
 *
 * ऊपर बड़ी photo (tap की हुई), नीचे छोटी thumbnails — Amazon/Flipkart जैसा।
 * ⭐ main photo ही ads में दिखती है।
 * URL: /products/album?id=24 (static export के लिए query-param, dynamic route नहीं)
 */
export default function ProductAlbumPage() {
  return (
    <Suspense fallback={<p className="py-10 text-center text-gray-400">…</p>}>
      <AlbumInner />
    </Suspense>
  );
}

function AlbumInner() {
  const { t } = useLanguage();
  const api = useAPI();
  const router = useRouter();
  const searchParams = useSearchParams();
  const productId = searchParams.get("id");

  const [product, setProduct] = useState(null);
  const [selectedId, setSelectedId] = useState(null); // बड़ी photo में कौन सी दिखे
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const load = useCallback(async () => {
    if (!productId) {
      setError(t("products.albumLoadFail"));
      return;
    }
    try {
      const p = await api.products.get(productId);
      setProduct(p);
      // चुनी photo अब न हो (हट गई) तो main पर लौटो
      const photos = p.photos || [];
      setSelectedId((cur) =>
        photos.some((ph) => ph.id === cur) ? cur : (photos[0]?.id ?? null)
      );
    } catch {
      setError(t("products.albumLoadFail"));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [api, productId]);

  useEffect(() => {
    load();
  }, [load]);

  function showToast(msg) {
    setToast(msg);
    setTimeout(() => setToast(""), 2500);
  }

  /** फ़ोन की भारी photo छोटी करें (PhotoPicker जैसा) */
  function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = async () => {
        let { width, height } = img;
        if (Math.max(width, height) > MAX_DIM) {
          const scale = MAX_DIM / Math.max(width, height);
          width = Math.round(width * scale);
          height = Math.round(height * scale);
        }
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        canvas.getContext("2d").drawImage(img, 0, 0, width, height);
        await addPhoto(canvas.toDataURL("image/jpeg", JPEG_QUALITY));
      };
      img.onerror = () => addPhoto(reader.result);
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
    e.target.value = ""; // वही file दोबारा चुन सके
  }

  async function addPhoto(dataUrl) {
    setBusy(true);
    try {
      const p = await api.products.addPhoto(productId, dataUrl);
      setProduct(p);
      setSelectedId(p.photos[p.photos.length - 1]?.id ?? null); // नई photo दिखाओ
      showToast(t("products.photoAdded"));
    } catch (err) {
      showToast(err?.message || t("products.photoFail"));
    } finally {
      setBusy(false);
    }
  }

  async function makeMain(photoId) {
    setBusy(true);
    try {
      const p = await api.products.setPrimaryPhoto(productId, photoId);
      setProduct(p);
      showToast(t("products.mainDone"));
    } catch {
      showToast(t("products.photoFail"));
    } finally {
      setBusy(false);
    }
  }

  async function removePhoto(photoId) {
    if (!window.confirm(t("products.deletePhotoConfirm"))) return;
    setBusy(true);
    try {
      const p = await api.products.deletePhoto(productId, photoId);
      setProduct(p);
      showToast(t("products.photoDeleted"));
    } catch {
      showToast(t("products.photoFail"));
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <div className="card mt-6 text-center text-hindi-danger">{error}</div>
    );
  }
  if (!product) {
    return <p className="py-10 text-center text-gray-400">{t("loading")}</p>;
  }

  const photos = product.photos || [];
  const selected = photos.find((ph) => ph.id === selectedId) || photos[0];

  return (
    <div className="space-y-4">
      {/* header: वापस + नाम */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push("/products")}
          className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-100 text-lg"
          aria-label="back"
        >
          ←
        </button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-bold">{product.name}</h1>
          <p className="font-semibold text-brand-600">
            {formatRupees(product.price)}
            <span className="ml-2 text-sm font-normal text-gray-400">
              {photos.length}/{MAX_PHOTOS} photos
            </span>
          </p>
        </div>
      </div>

      {toast && (
        <p className="rounded-xl bg-green-50 p-3 text-center font-semibold text-green-700">
          {toast}
        </p>
      )}

      {/* बड़ी photo */}
      <div className="relative overflow-hidden rounded-2xl bg-gray-100">
        {selected ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={selected.url}
            alt={product.name}
            className="aspect-square w-full object-cover"
          />
        ) : (
          <button
            onClick={() => inputRef.current?.click()}
            className="flex aspect-square w-full flex-col items-center justify-center gap-2 text-brand-500"
          >
            <span className="text-6xl">📷</span>
            <span className="font-semibold">{t("products.addFirstPhoto")}</span>
          </button>
        )}
        {selected?.is_primary && (
          <span className="absolute left-3 top-3 rounded-full bg-yellow-400 px-3 py-1 text-sm font-bold text-gray-900 shadow">
            ⭐ {t("products.mainPhoto")}
          </span>
        )}
      </div>

      {/* छोटी photos की कतार + add tile */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {photos.map((ph) => (
          <button
            key={ph.id}
            onClick={() => setSelectedId(ph.id)}
            className={`relative h-20 w-20 flex-none overflow-hidden rounded-xl transition-all ${
              ph.id === selected?.id
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
            {ph.is_primary && (
              <span className="absolute right-1 top-1 rounded-full bg-yellow-400 px-1.5 text-xs font-bold shadow">
                ⭐
              </span>
            )}
          </button>
        ))}
        {photos.length < MAX_PHOTOS && photos.length > 0 && (
          <button
            onClick={() => inputRef.current?.click()}
            disabled={busy}
            className="flex h-20 w-20 flex-none flex-col items-center justify-center rounded-xl border-2 border-dashed border-brand-300 bg-brand-50 text-brand-500"
          >
            <span className="text-2xl">＋</span>
            <span className="text-xs font-semibold">{t("products.addPhoto")}</span>
          </button>
        )}
      </div>

      {/* चुनी photo के काम */}
      {selected && (
        <div className="space-y-3">
          {selected.is_primary ? (
            <p className="rounded-xl bg-yellow-50 p-3 text-center text-sm font-semibold text-yellow-700">
              {t("products.isMainNote")}
            </p>
          ) : (
            <button
              onClick={() => makeMain(selected.id)}
              disabled={busy}
              className="btn-primary w-full"
            >
              ⭐ {t("products.makeMain")}
            </button>
          )}
          {photos.length > 1 && (
            <button
              onClick={() => removePhoto(selected.id)}
              disabled={busy}
              className="w-full rounded-xl border-2 border-red-200 py-3 font-semibold text-hindi-danger"
            >
              🗑 {t("products.deletePhoto")}
            </button>
          )}
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFile}
      />

      {busy && (
        <p className="text-center text-sm text-gray-400">{t("loading")}</p>
      )}
    </div>
  );
}
