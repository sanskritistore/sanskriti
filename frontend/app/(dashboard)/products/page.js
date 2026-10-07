"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { useAPI } from "@/lib/api";
import { formatRupees } from "@/lib/utils";
import LanguageToggle from "@/components/ui/LanguageToggle";
import StepDots from "@/components/ui/StepDots";
import ProductCard from "@/components/ui/ProductCard";
import PhotoPicker from "@/components/forms/PhotoPicker";

/**
 * Products — add/manage products in 3 steps:
 *   Step 1: take/pick photo
 *   Step 2: enter name & price
 *   Step 3: save
 */
export default function ProductsPage() {
  const { t } = useLanguage();
  const api = useAPI();

  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  // Add-product 3-step state
  const [adding, setAdding] = useState(false);
  const [step, setStep] = useState(1);
  const [photo, setPhoto] = useState(null);
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");

  async function loadProducts() {
    try {
      const data = await api.products.list();
      setProducts(Array.isArray(data) ? data : data?.items ?? []);
    } catch {
      // Offline or backend not ready — keep empty list
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProducts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSave(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.products.create({
        name,
        price: Number(price),
        photo, // placeholder: base64/URL — backend contract TBD
      });
      setToast(t("products.added"));
      setAdding(false);
      resetForm();
      loadProducts();
      setTimeout(() => setToast(""), 2500);
    } catch {
      setToast(t("login.error.generic"));
    } finally {
      setBusy(false);
    }
  }

  function resetForm() {
    setStep(1);
    setPhoto(null);
    setName("");
    setPrice("");
  }

  async function handleDelete(id) {
    try {
      await api.products.delete(id);
      loadProducts();
    } catch {
      /* non-blocking */
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("products.title")}</h1>
        <LanguageToggle />
      </div>

      {toast && (
        <p className="rounded-xl bg-green-50 p-3 text-center font-semibold text-hindi-success">
          {toast}
        </p>
      )}

      {/* Add product — 3 steps */}
      {adding ? (
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold">{t("products.add")}</h2>
            <button
              className="text-sm text-gray-500 underline"
              onClick={() => {
                setAdding(false);
                resetForm();
              }}
            >
              {t("cancel")}
            </button>
          </div>

          <StepDots step={step} total={3} />
          <p className="text-center text-sm font-medium text-brand-600">
            {step === 1 && t("products.step1")}
            {step === 2 && t("products.step2")}
            {step === 3 && t("products.step3")}
          </p>

          {/* STEP 1: photo */}
          {step === 1 && (
            <div className="space-y-4">
              <PhotoPicker value={photo} onChange={setPhoto} hint={t("products.photoHint")} />
              <button className="btn-primary w-full" onClick={() => setStep(2)}>
                {t("next")}
              </button>
            </div>
          )}

          {/* STEP 2: name & price */}
          {step === 2 && (
            <div className="space-y-4">
              <div>
                <label className="label">{t("products.name")}</label>
                <input
                  className="input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoFocus
                />
              </div>
              <div>
                <label className="label">{t("products.price")}</label>
                <input
                  className="input"
                  type="tel"
                  inputMode="numeric"
                  value={price}
                  onChange={(e) =>
                    setPrice(e.target.value.replace(/\D/g, ""))
                  }
                />
              </div>
              <div className="flex gap-2">
                <button className="btn-secondary flex-1" onClick={() => setStep(1)}>
                  {t("back")}
                </button>
                <button
                  className="btn-primary flex-1"
                  onClick={() => setStep(3)}
                  disabled={!name || !price}
                >
                  {t("next")}
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: confirm & save */}
          {step === 3 && (
            <div className="space-y-4">
              <div className="rounded-xl bg-brand-50 p-4 text-center">
                {photo ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={photo}
                    alt={name}
                    className="mx-auto h-32 w-32 rounded-xl object-cover"
                  />
                ) : (
                  <div className="mx-auto flex h-32 w-32 items-center justify-center rounded-xl bg-brand-100 text-4xl">
                    📦
                  </div>
                )}
                <p className="mt-3 text-lg font-bold">{name}</p>
                <p className="text-xl font-bold text-brand-600">
                  {formatRupees(price)}
                </p>
              </div>
              <div className="flex gap-2">
                <button className="btn-secondary flex-1" onClick={() => setStep(2)}>
                  {t("back")}
                </button>
                <button
                  className="btn-primary flex-1"
                  onClick={handleSave}
                  disabled={busy}
                >
                  {busy ? t("loading") : t("save")}
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <button className="btn-primary w-full" onClick={() => setAdding(true)}>
          ➕ {t("products.add")}
        </button>
      )}

      {/* Product list */}
      {loading ? (
        <p className="py-8 text-center text-gray-400">{t("loading")}</p>
      ) : products.length === 0 ? (
        <div className="card py-10 text-center">
          <div className="text-4xl">📦</div>
          <p className="mt-3 text-gray-500">{t("products.empty")}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {products.map((p) => (
            <ProductCard
              key={p.id}
              product={p}
              onDelete={() => handleDelete(p.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
