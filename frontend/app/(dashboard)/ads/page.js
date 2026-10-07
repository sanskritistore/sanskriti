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
 * उम्र के preset विकल्प — tenant को उम्र का गणित नहीं सिखाना
 */
const AGE_OPTIONS = [
  { key: "all", min: 18, max: 65, labelKey: "ads.ageAll" },
  { key: "young", min: 18, max: 25, labelKey: "ads.ageYoung" },
  { key: "mid", min: 26, max: 40, labelKey: "ads.ageMid" },
  { key: "senior", min: 41, max: 65, labelKey: "ads.ageSenior" },
];
const RADIUS_OPTIONS = [1, 2, 5]; // km — Meta का न्यूनतम घेरा 1 km

/**
 * Ads — असली Meta campaign 4 steps में:
 *   Step 1: प्रोडक्ट चुनें
 *   Step 2: रोज़ का बजट चुनें
 *   Step 3: दर्शक चुनें (कहाँ + किस उम्र को) — user की माँग 07-10
 *   Step 4: PREVIEW देखें → पक्का करें → LAUNCH
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
  const [geoType, setGeoType] = useState("city"); // city | place
  const [placeName, setPlaceName] = useState("");
  const [radiusKm, setRadiusKm] = useState(1);
  const [ageKey, setAgeKey] = useState("all");
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

  /** Step 3 → 4: जगह का नाम ज़रूरी है (खास जगह चुनी हो तो) */
  function handleTargetingNext() {
    if (geoType === "place" && !placeName.trim()) {
      setToast(t("ads.placeNeeded"));
      setTimeout(() => setToast(""), 3000);
      return;
    }
    goToPreview();
  }

  /** Step 3 → 4: AI से ad text बनवाकर PREVIEW दिखाएँ (पहले दिखेगी, फिर पैसा लगेगा) */
  async function goToPreview() {
    setStep(4);
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
      // Tenant के चुने दर्शक (जगह + घेरा + उम्र)
      const age = AGE_OPTIONS.find((a) => a.key === ageKey) || AGE_OPTIONS[0];
      const targeting = {
        geo_type: geoType,
        place_name: geoType === "place" ? placeName.trim() : null,
        radius_km: geoType === "place" ? radiusKm : null,
        age_min: age.min,
        age_max: age.max,
      };
      // 1. Campaign बनाएँ (creative preview step में बन चुका है)
      setPhase(t("ads.launching"));
      const campaign = await api.campaigns.create({
        name: `${selectedProduct.name} - विज्ञापन`,
        objective: "awareness",
        ad_creative_id: creative.id,
        budget_total: budget * DAYS,
        budget_daily: budget,
        targeting: JSON.stringify(targeting),
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
    setGeoType("city");
    setPlaceName("");
    setRadiusKm(1);
    setAgeKey("all");
    setCreative(null);
    setPreviewError(false);
  }

  /** Preview में दिखने वाला दर्शक-सारांश (जैसे: "आकाश इंस्टिट्यूट · 1 km · 👥 18-25") */
  function targetingSummary() {
    const age = AGE_OPTIONS.find((a) => a.key === ageKey) || AGE_OPTIONS[0];
    const place =
      geoType === "place"
        ? `${placeName.trim()} · ${radiusKm} km`
        : t("ads.yourCity");
    return `📍 ${place} · 👥 ${t(age.labelKey)}`;
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

          <StepDots step={step} total={4} />
          <p className="text-center text-sm font-medium text-brand-600">
            {step === 1 && t("ads.step1")}
            {step === 2 && t("ads.step2")}
            {step === 3 && t("ads.step3")}
            {step === 4 && t("ads.step4")}
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
                  onClick={() => setStep(3)}
                  disabled={!budget}
                >
                  {t("next")}
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: दर्शक चुनें — कहाँ + किस उम्र को (user की माँग) */}
          {step === 3 && (
            <div className="space-y-4">
              <p className="font-semibold text-gray-700">{t("ads.whereQ")}</p>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setGeoType("city")}
                  className={`card text-left transition-colors ${
                    geoType === "city" ? "ring-2 ring-brand-500" : ""
                  }`}
                >
                  <div className="text-2xl">🏙️</div>
                  <p className="mt-1 font-semibold">{t("ads.locCity")}</p>
                  <p className="text-xs text-gray-500">{t("ads.locCitySub")}</p>
                </button>
                <button
                  onClick={() => setGeoType("place")}
                  className={`card text-left transition-colors ${
                    geoType === "place" ? "ring-2 ring-brand-500" : ""
                  }`}
                >
                  <div className="text-2xl">📍</div>
                  <p className="mt-1 font-semibold">{t("ads.locPlace")}</p>
                  <p className="text-xs text-gray-500">
                    {t("ads.locPlaceSub")}
                  </p>
                </button>
              </div>

              {/* खास जगह चुनी तो: नाम + घेरा */}
              {geoType === "place" && (
                <div className="space-y-3 rounded-xl bg-gray-50 p-3">
                  <input
                    value={placeName}
                    onChange={(e) => setPlaceName(e.target.value)}
                    placeholder={t("ads.placePlaceholder")}
                    className="w-full rounded-xl border border-gray-300 p-3"
                  />
                  <p className="text-sm font-semibold text-gray-700">
                    {t("ads.radiusQ")}
                  </p>
                  <div className="flex gap-2">
                    {RADIUS_OPTIONS.map((km) => (
                      <button
                        key={km}
                        onClick={() => setRadiusKm(km)}
                        className={`flex-1 rounded-xl border py-2 font-semibold transition-colors ${
                          radiusKm === km
                            ? "border-brand-500 bg-brand-500 text-white"
                            : "border-gray-300"
                        }`}
                      >
                        {km} {t("ads.kmAway")}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <p className="font-semibold text-gray-700">{t("ads.ageQ")}</p>
              <div className="grid grid-cols-2 gap-2">
                {AGE_OPTIONS.map((a) => (
                  <button
                    key={a.key}
                    onClick={() => setAgeKey(a.key)}
                    className={`rounded-xl border py-3 font-semibold transition-colors ${
                      ageKey === a.key
                        ? "border-brand-500 bg-brand-500 text-white"
                        : "border-gray-300"
                    }`}
                  >
                    {t(a.labelKey)}
                  </button>
                ))}
              </div>

              <div className="flex gap-2">
                <button
                  className="btn-secondary flex-1"
                  onClick={() => setStep(2)}
                >
                  {t("back")}
                </button>
                <button
                  className="btn-primary flex-1"
                  onClick={handleTargetingNext}
                >
                  {t("next")}
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: PREVIEW — ad पहले देखो, फिर launch */}
          {step === 4 && (
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
                  {/* चुने हुए दर्शक — launch से पहले verify */}
                  <p className="text-center text-sm font-medium text-gray-600">
                    {t("ads.showsIn")}: {targetingSummary()}
                  </p>
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
                  onClick={() => setStep(3)}
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
