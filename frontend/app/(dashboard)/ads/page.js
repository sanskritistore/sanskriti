"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { useAPI } from "@/lib/api";
import { formatRupees } from "@/lib/utils";
import LanguageToggle from "@/components/ui/LanguageToggle";
import StepDots from "@/components/ui/StepDots";
import AdPreviewCard from "@/components/ads/AdPreviewCard";

/** Preset daily budgets — simple choices, no free-form numbers */
const BUDGET_OPTIONS = [100, 250, 500, 1000];
const DAYS = 5; // हर campaign 5 दिन चलता है (total = daily × 5)

/**
 * Ads — असली Meta campaign 3 steps में (architecture rule):
 *   Step 1: प्रोडक्ट चुनें
 *   Step 2: रोज़ का बजट चुनें
 *   Step 3: पक्का करें → AI creative → campaign → LAUNCH (सब PAUSED Meta पर)
 */
export default function AdsPage() {
  const { t } = useLanguage();
  const api = useAPI();

  const [campaigns, setCampaigns] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  const [creating, setCreating] = useState(false);
  const [step, setStep] = useState(1);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [budget, setBudget] = useState(null);
  const [creative, setCreative] = useState(null); // AI से बना ad text (preview में दिखता है)
  const [previewError, setPreviewError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState(""); // कौन सा काम चल रहा है
  const [toast, setToast] = useState("");

  async function loadAll() {
    try {
      const [campsData, productsData] = await Promise.all([
        api.campaigns.list(),
        api.products.list(),
      ]);
      setCampaigns(
        Array.isArray(campsData) ? campsData : campsData?.items ?? []
      );
      setProducts(
        Array.isArray(productsData)
          ? productsData
          : productsData?.items ?? []
      );
    } catch {
      /* backend not ready */
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Step 2 → 3: AI से ad text बनवाकर PREVIEW दिखाएँ (पहले दिखेगी, फिर पैसा लगेगा) */
  async function goToPreview() {
    setStep(3);
    setCreative(null);
    setPreviewError(false);
    try {
      const c = await api.adStudio.generate({
        product_id: selectedProduct.id,
        language: "hi",
      });
      setCreative(c);
    } catch {
      setPreviewError(true);
    }
  }

  async function handlePublish() {
    if (!creative) return; // preview के बिना launch नहीं
    setBusy(true);
    try {
      // 1. Campaign बनाएँ (creative preview step में बन चुका है)
      setPhase(t("ads.launching"));
      const campaign = await api.campaigns.create({
        name: `${selectedProduct.name} - विज्ञापन`,
        objective: "awareness",
        ad_creative_id: creative.id,
        budget_total: budget * DAYS,
        budget_daily: budget,
      });

      // 3. LAUNCH — Meta पर पूरी chain खड़ी होगी
      await api.campaigns.launch(campaign.id);

      setToast(t("ads.published"));
      setCreating(false);
      resetForm();
      loadAll();
      setTimeout(() => setToast(""), 4000);
    } catch (err) {
      setToast(err?.message || t("login.error.generic"));
      setTimeout(() => setToast(""), 5000);
    } finally {
      setBusy(false);
      setPhase("");
    }
  }

  async function handlePause(id) {
    setBusy(true);
    try {
      await api.campaigns.pause(id);
      await loadAll();
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  function resetForm() {
    setStep(1);
    setSelectedProduct(null);
    setBudget(null);
    setCreative(null);
    setPreviewError(false);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("ads.title")}</h1>
        <LanguageToggle />
      </div>

      {toast && (
        <p className="rounded-xl bg-green-50 p-3 text-center font-semibold text-hindi-success">
          {toast}
        </p>
      )}

      {creating ? (
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold">{t("ads.title")}</h2>
            <button
              className="text-sm text-gray-500 underline"
              onClick={() => {
                setCreating(false);
                resetForm();
              }}
            >
              {t("cancel")}
            </button>
          </div>

          <StepDots step={step} total={3} />
          <p className="text-center text-sm font-medium text-brand-600">
            {step === 1 && t("ads.step1")}
            {step === 2 && t("ads.step2")}
            {step === 3 && t("ads.step3")}
          </p>

          {/* STEP 1: choose product */}
          {step === 1 && (
            <div className="space-y-3">
              <p className="font-semibold text-gray-700">
                {t("ads.selectProduct")}
              </p>
              {products.length === 0 ? (
                <p className="rounded-xl bg-amber-50 p-4 text-center text-amber-700">
                  {t("products.empty")}
                </p>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {products.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => {
                        setSelectedProduct(p);
                        setStep(2);
                      }}
                      className={`card text-left transition-colors ${
                        selectedProduct?.id === p.id
                          ? "ring-2 ring-brand-500"
                          : ""
                      }`}
                    >
                      <div className="text-3xl">📦</div>
                      <p className="mt-2 font-semibold">{p.name}</p>
                      <p className="text-brand-600">{formatRupees(p.price)}</p>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* STEP 2: choose daily budget */}
          {step === 2 && (
            <div className="space-y-4">
              <p className="font-semibold text-gray-700">{t("ads.budget")}</p>
              <div className="grid grid-cols-2 gap-3">
                {BUDGET_OPTIONS.map((amount) => (
                  <button
                    key={amount}
                    onClick={() => setBudget(amount)}
                    className={`card py-6 text-center transition-colors ${
                      budget === amount
                        ? "bg-brand-500 text-white ring-brand-500"
                        : ""
                    }`}
                  >
                    <span className="text-xl font-bold">
                      {formatRupees(amount)}
                    </span>
                    <span className="block text-xs opacity-80">
                      {t("ads.daily")}
                    </span>
                  </button>
                ))}
              </div>
              <p className="text-center text-sm text-gray-500">
                {t("ads.budgetHint")} · {t("ads.days5")}
              </p>
              <div className="flex gap-2">
                <button
                  className="btn-secondary flex-1"
                  onClick={() => setStep(1)}
                >
                  {t("back")}
                </button>
                <button
                  className="btn-primary flex-1"
                  onClick={goToPreview}
                  disabled={!budget}
                >
                  {t("next")}
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: PREVIEW — ad पहले देखो, फिर launch */}
          {step === 3 && (
            <div className="space-y-4">
              <p className="text-center font-semibold text-gray-700">
                {t("ads.previewTitle")}
              </p>

              {/* AI ad बन रही है */}
              {!creative && !previewError && (
                <p className="py-10 text-center text-gray-500">
                  ✨ {t("ads.working")}
                </p>
              )}

              {/* बन नहीं पाई — retry */}
              {previewError && (
                <div className="space-y-3 py-6 text-center">
                  <p className="text-red-600">{t("ads.previewError")}</p>
                  <button className="btn-secondary" onClick={goToPreview}>
                    🔄 {t("retry")}
                  </button>
                </div>
              )}

              {/* असली PREVIEW — Facebook जैसी ad */}
              {creative && (
                <>
                  <AdPreviewCard
                    product={selectedProduct}
                    creative={creative}
                  />
                  <div className="rounded-xl bg-brand-50 p-3 text-center">
                    <p className="font-bold text-brand-600">
                      {formatRupees(budget)} {t("ads.daily")} ·{" "}
                      {t("ads.days5")}
                    </p>
                    <p className="text-sm text-gray-500">
                      {t("ads.totalLabel")}: {formatRupees(budget * DAYS)}
                    </p>
                  </div>
                </>
              )}

              <div className="flex gap-2">
                <button
                  className="btn-secondary flex-1"
                  onClick={() => setStep(2)}
                  disabled={busy}
                >
                  {t("back")}
                </button>
                <button
                  className="btn-primary flex-1"
                  onClick={handlePublish}
                  disabled={busy || !creative}
                >
                  {busy ? phase || t("loading") : t("ads.publish")}
                </button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <>
          <button
            className="btn-primary w-full"
            onClick={() => setCreating(true)}
          >
            📣 {t("ads.title")}
          </button>

          {/* Campaigns */}
          {loading ? (
            <p className="py-8 text-center text-gray-400">{t("loading")}</p>
          ) : (
            <div className="space-y-3">
              <h2 className="font-bold text-gray-700">{t("ads.active")}</h2>
              {campaigns.length === 0 ? (
                <div className="card py-10 text-center">
                  <div className="text-4xl">📣</div>
                  <p className="mt-3 text-gray-500">{t("ads.none")}</p>
                </div>
              ) : (
                campaigns.map((c) => (
                  <div
                    key={c.id}
                    className="card flex items-center justify-between"
                  >
                    <div>
                      <p className="font-semibold">{c.name}</p>
                      <p className="text-sm text-gray-500">
                        {formatRupees(c.budget_daily)} {t("ads.daily")} ·{" "}
                        {c.status === "active"
                          ? t("ads.statusActive")
                          : t("ads.paused")}
                      </p>
                    </div>
                    {c.status === "active" ? (
                      <button
                        className="rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-700"
                        onClick={() => handlePause(c.id)}
                        disabled={busy}
                      >
                        ⏸ {t("ads.pause")}
                      </button>
                    ) : (
                      <span className="rounded-full bg-gray-100 px-3 py-1 text-sm font-semibold text-gray-500">
                        ⏸
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
