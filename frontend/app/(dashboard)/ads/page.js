"use client";

import { useEffect, useRef, useState } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { useAPI } from "@/lib/api";
import { formatRupees } from "@/lib/utils";
import LanguageToggle from "@/components/ui/LanguageToggle";
import StepDots from "@/components/ui/StepDots";
import AdPreviewCard from "@/components/ads/AdPreviewCard";
import MapPinPicker from "@/components/ads/MapPinPicker";
import { STATES } from "@/lib/data/india-states";

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
  // 🎠 Carousel (10-10 user माँग): मुख्य product के अलावा extra posters (अधिकतम 4)
  // 🎠 A (10-10): चुने product की album photos की गिनती — hint दिखाने के लिए
  const [albumPhotoCount, setAlbumPhotoCount] = useState(0);
  const [budget, setBudget] = useState(null);
  const [geoType, setGeoType] = useState("city"); // city | place | list
  // 📞 ग्राहक-सूची targeting (09-10 user idea): सेव किए phone numbers वालों को ad
  const [audiences, setAudiences] = useState([]);
  const [audienceId, setAudienceId] = useState(null);
  const [audienceName, setAudienceName] = useState("");
  const [audiencesLoading, setAudiencesLoading] = useState(false);
  // 📞 Ad flow के अंदर ही नए numbers जोड़ने का खाना (user की माँग 09-10 शाम)
  const [newPhones, setNewPhones] = useState("");
  const [addingPhones, setAddingPhones] = useState(false);
  const [state, setState] = useState("Delhi"); // पहले राज्य, फिर जगह (user की माँग 08-10)
  const [places, setPlaces] = useState([]); // चुनी जगहें: {name, area, lat, lon} — lat/lon null = सिर्फ़ नाम से
  const [placeInput, setPlaceInput] = useState("");
  const [suggestions, setSuggestions] = useState([]); // खोज से आए सुझाव (पते सहित)
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false); // कम से कम एक खोज पूरी हुई
  const searchTimer = useRef(null);
  const [showMap, setShowMap] = useState(false); // "नक्शे से सुई" modal (08-10)
  const [radiusKm, setRadiusKm] = useState(1);
  const [ageKey, setAgeKey] = useState("all");
  const [creative, setCreative] = useState(null); // AI से बना ad text (preview में दिखता है)
  const [previewError, setPreviewError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState(""); // कौन सा काम चल रहा है
  const [toast, setToast] = useState("");
  const [records, setRecords] = useState(null); // हटाई गई ads का रिकॉर्ड
  const [showRecords, setShowRecords] = useState(false);

  /** हटाई गई ads का रिकॉर्ड खोलें/लाएँ */
  async function toggleRecords() {
    const next = !showRecords;
    setShowRecords(next);
    if (next) {
      try {
        setRecords(await api.campaigns.records());
      } catch {
        setRecords(null);
      }
    }
  }

  /** रुकी/draft ad हटाएँ — record सुरक्षित रहता है (08-10 user माँग) */
  async function handleDelete(c) {
    if (!window.confirm(t("ads.deleteConfirm"))) return;
    setBusy(true);
    try {
      await api.campaigns.delete(c.id);
      setCampaigns(campaigns.filter((x) => x.id !== c.id));
      setRecords(null); // अगली बार खोलने पर ताज़ा रिकॉर्ड आए
    } catch (err) {
      setToast(err?.message || t("login.error.generic"));
      setTimeout(() => setToast(""), 3000);
    } finally {
      setBusy(false);
    }
  }

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

  /** नाम लिखते ही सुझाव — 400ms रुककर state के अंदर खोज (08-10 UX) */
  function onPlaceInput(value) {
    setPlaceInput(value);
    setSearched(false);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    const q = value.trim();
    if (q.length < 2) {
      setSuggestions([]);
      setSearching(false);
      return;
    }
    searchTimer.current = setTimeout(async () => {
      setSearching(true);
      try {
        const found = await api.targeting.searchPlaces(q, state);
        setSuggestions(found);
      } catch {
        setSuggestions([]);
      }
      setSearching(false);
      setSearched(true);
    }, 400);
  }

  /** सुझाव से जगह चुनी — सुई LOCK (पक्का पता, अंदाज़ा नहीं!) */
  function selectSuggestion(s) {
    if (places.some((p) => p.name === s.name) || places.length >= 10) return;
    setPlaces([...places, { name: s.name, area: s.area, lat: s.lat, lon: s.lon }]);
    setPlaceInput("");
    setSuggestions([]);
    setSearched(false);
  }

  /** हाथ से लिखी जगह जोड़ें (सुई बिना — launch पर खोजी जाएगी) */
  function addPlace() {
    const name = placeInput.trim();
    if (name && !places.some((p) => p.name === name) && places.length < 10) {
      setPlaces([...places, { name, area: "", lat: null, lon: null }]);
    }
    setPlaceInput("");
    setSuggestions([]);
    setSearched(false);
  }

  function removePlace(name) {
    setPlaces(places.filter((p) => p.name !== name));
  }

  /** Step 3 → 4: कम से कम एक जगह ज़रूरी (खास जगह चुनी हो तो)
   *  लिखी हुई जगह "+ जोड़ें" दबाए बिना भी अपने आप जुड़ जाती है —
   *  user ने लिखा पर add नहीं दबाया तो भी काम चले (07-10 UX सीख) */
  function handleTargetingNext() {
    let finalPlaces = places;
    const typed = placeInput.trim();
    if (geoType === "place" && typed && !places.some((p) => p.name === typed)) {
      finalPlaces = [...places, { name: typed, area: "", lat: null, lon: null }];
      setPlaces(finalPlaces);
      setPlaceInput("");
    }
    if (geoType === "place" && finalPlaces.length === 0) {
      setToast(t("ads.placeNeeded"));
      setTimeout(() => setToast(""), 3000);
      return;
    }
    if (geoType === "list" && !audienceId) {
      setToast(t("ads.listNeeded"));
      setTimeout(() => setToast(""), 3000);
      return;
    }
    goToPreview();
  }

  /** 📞 ग्राहक-सूची mode चुनते ही Meta की lists लाएँ (एक बार) */
  async function pickListMode() {
    setGeoType("list");
    if (audiences.length > 0 || audiencesLoading) return;
    setAudiencesLoading(true);
    try {
      const data = await api.audiences.list();
      setAudiences(data.audiences || []);
    } catch (err) {
      // Silent-fail नियम: error साफ़ दिखे
      setToast(err?.message || t("login.error.generic"));
      setTimeout(() => setToast(""), 5000);
    } finally {
      setAudiencesLoading(false);
    }
  }

  /** 📞 चुनी सूची में नए numbers जोड़ो — flow छोड़े बिना (user की माँग) */
  async function addPhonesToList() {
    if (!audienceId) {
      setToast(t("ads.listNeeded"));
      setTimeout(() => setToast(""), 3000);
      return;
    }
    const phones = newPhones
      .split(/[\n,;]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (phones.length === 0) return;
    setAddingPhones(true);
    try {
      const res = await api.audiences.upload(audienceId, phones);
      setToast(`✅ ${res.received} ${t("ads.phonesAdded")}`);
      setNewPhones("");
      setTimeout(() => setToast(""), 4000);
    } catch (err) {
      // Silent-fail नियम: error साफ़ दिखे
      setToast(err?.message || t("login.error.generic"));
      setTimeout(() => setToast(""), 5000);
    } finally {
      setAddingPhones(false);
    }
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
        // 📞 ग्राहक-सूची चुनी हो तो वही दर्शक — geo नहीं जाता
        audience_id: geoType === "list" ? audienceId : null,
        // locked जगहों की सुई साथ जाती है — backend को अंदाज़ा नहीं लगाना पड़ता
        places:
          geoType === "place"
            ? places.map((p) => ({
                name: p.name,
                latitude: p.lat,
                longitude: p.lon,
              }))
            : null,
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

  async function handleResume(id) {
    setBusy(true);
    try {
      await api.campaigns.resume(id);
      await loadAll();
    } catch {
      /* ignore */
    } finally {
      setBusy(false);
    }
  }

  // 👀📸 असली LIVE ad देखो — Facebook + Instagram (10-10 user माँग:
  // "facebook/instagram पर जैसे कोई और देख रहा हो वैसी असली ad") —
  // Meta से असली live post links, नई टैब में। देखना FREE — पैसा नहीं कटता।
  const [liveLinks, setLiveLinks] = useState({});

  async function handleView(id, platform) {
    setBusy(true);
    try {
      let links = liveLinks[id];
      if (!links) {
        links = await api.campaigns.preview(id);
        setLiveLinks((m) => ({ ...m, [id]: links }));
      }
      const url =
        platform === "ig"
          ? links?.instagram_url || links?.preview_url
          : links?.live_url || links?.preview_url;
      if (!url) throw new Error("no url");
      window.open(url, "_blank", "noopener");
    } catch {
      setToast(t("ads.previewError"));
      setTimeout(() => setToast(""), 4000);
    } finally {
      setBusy(false);
    }
  }

  function resetForm() {
    setStep(1);
    setSelectedProduct(null);
    setAlbumPhotoCount(0);
    setBudget(null);
    setGeoType("city");
    setAudienceId(null);
    setAudienceName("");
    setNewPhones("");
    setPlaces([]);
    setPlaceInput("");
    setRadiusKm(1);
    setAgeKey("all");
    setCreative(null);
    setPreviewError(false);
  }

  /** Preview में दिखने वाला दर्शक-सारांश (जैसे: "आकाश इंस्टिट्यूट +2 और · 1 km · 👥 18-25") */
  function targetingSummary() {
    const age = AGE_OPTIONS.find((a) => a.key === ageKey) || AGE_OPTIONS[0];
    if (geoType === "list") {
      return `📞 ${audienceName} · 👥 ${t(age.labelKey)}`;
    }
    let place = t("ads.yourCity");
    if (geoType === "place" && places.length > 0) {
      place = places[0].name;
      if (places.length > 1) place += ` +${places.length - 1} ${t("ads.morePlaces")}`;
      place += ` · ${radiusKm} km`;
    }
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
                <>
                  <div className="grid grid-cols-2 gap-3">
                    {products.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => {
                          setSelectedProduct(p);
                          // 🎠 album photos गिनो — hint: "सारी photos ad में दिखेंगी"
                          setAlbumPhotoCount(0);
                          api.products
                            .get(p.id)
                            .then((d) =>
                              setAlbumPhotoCount(d?.photos?.length || 0)
                            )
                            .catch(() => {});
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

                  {/* 🎠 A: product की अपनी album photos अपने-आप carousel में */}
                  {albumPhotoCount > 1 && (
                    <p className="rounded-xl bg-green-50 p-3 text-sm font-semibold text-green-700">
                      {t("ads.albumNote").replace(
                        "{n}",
                        String(albumPhotoCount)
                      )}
                    </p>
                  )}

                  {/* आगे बढ़ें — मुख्य product चुनने पर */}
                  {selectedProduct && (
                    <button
                      onClick={() => setStep(2)}
                      className="btn-primary w-full py-4 text-lg"
                    >
                      {t("ads.next")}
                    </button>
                  )}
                </>
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
              {/* पहले राज्य चुनें — फिर उसी राज्य की जगहें खोजी जाएँगी (user की माँग 08-10) */}
              {geoType !== "list" && (
                <>
                  <p className="font-semibold text-gray-700">{t("ads.stateQ")}</p>
                  <select
                    value={state}
                    onChange={(e) => {
                      setState(e.target.value);
                      setSuggestions([]); // राज्य बदला तो पुराने सुझाव हटाएँ
                    }}
                    className="w-full rounded-xl border border-gray-300 bg-white p-3 font-semibold text-gray-800"
                  >
                    {STATES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </>
              )}

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

              {/* 📞 ग्राहक-सूची card — सेव किए phone numbers वालों को ad (09-10 user idea) */}
              <button
                onClick={pickListMode}
                className={`card w-full text-left transition-colors ${
                  geoType === "list" ? "ring-2 ring-brand-500" : ""
                }`}
              >
                <div className="text-2xl">📞</div>
                <p className="mt-1 font-semibold">{t("ads.locList")}</p>
                <p className="text-xs text-gray-500">{t("ads.locListSub")}</p>
              </button>

              {/* ग्राहक-सूची चुनी तो: Meta lists में से एक चुनें */}
              {geoType === "list" && (
                <div className="space-y-3 rounded-xl bg-gray-50 p-3">
                  {audiencesLoading && (
                    <p className="p-2 text-sm text-gray-500">
                      {t("ads.searching")}
                    </p>
                  )}
                  {!audiencesLoading && audiences.length === 0 && (
                    <p className="rounded-xl bg-orange-50 p-3 text-sm font-semibold text-orange-700">
                      {t("ads.noLists")}
                    </p>
                  )}
                  {!audiencesLoading && audiences.length > 0 && (
                    <>
                      <p className="font-semibold text-gray-700">
                        {t("ads.pickList")}
                      </p>
                      <select
                        value={audienceId || ""}
                        onChange={(e) => {
                          const a = audiences.find(
                            (x) => x.id === e.target.value
                          );
                          setAudienceId(e.target.value || null);
                          setAudienceName(a ? a.name : "");
                        }}
                        className="w-full rounded-xl border border-gray-300 bg-white p-3 font-semibold text-gray-800"
                      >
                        <option value="">—</option>
                        {audiences.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name}
                          </option>
                        ))}
                      </select>
                      <p className="text-xs text-gray-500">
                        {t("ads.listHint")}
                      </p>
                      {/* 📞 इसी सूची में नए numbers जोड़ो — flow छोड़े बिना (user की माँग) */}
                      <div className="space-y-2 rounded-xl border border-dashed border-gray-300 bg-white p-3">
                        <p className="text-sm font-semibold text-gray-700">
                          {t("ads.addPhonesQ")}
                        </p>
                        <textarea
                          rows={3}
                          value={newPhones}
                          onChange={(e) => setNewPhones(e.target.value)}
                          placeholder={t("ads.phonesPlaceholder")}
                          className="w-full rounded-xl border border-gray-300 p-3 text-sm"
                        />
                        <button
                          onClick={addPhonesToList}
                          disabled={addingPhones || !newPhones.trim()}
                          className="w-full rounded-xl bg-brand-500 p-3 font-bold text-white disabled:opacity-50"
                        >
                          {addingPhones
                            ? t("customers.adding")
                            : t("ads.addPhonesBtn")}
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* खास जगह चुनी तो: कई जगहें जोड़ें + घेरा */}
              {geoType === "place" && (
                <div className="space-y-3 rounded-xl bg-gray-50 p-3">
                  {/* 🔍 खोज पेटी — नाम लिखते ही पते-सहित सुझाव, एक टैप में LOCK */}
                  <div className="relative">
                    <div className="flex gap-2">
                      <input
                        value={placeInput}
                        onChange={(e) => onPlaceInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            addPlace();
                          }
                        }}
                        placeholder={t("ads.placePlaceholder")}
                        className="flex-1 rounded-xl border border-gray-300 p-3"
                      />
                      <button
                        onClick={addPlace}
                        className="rounded-xl bg-brand-500 px-4 font-bold text-white"
                      >
                        + {t("ads.addPlace")}
                      </button>
                    </div>
                    {/* सुझाव सूची — नाम बड़ा, पता छोटा */}
                    {(searching || suggestions.length > 0) && (
                      <div className="absolute z-10 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-gray-200 bg-white shadow-lg">
                        {searching && (
                          <p className="p-3 text-sm text-gray-500">
                            {t("ads.searching")}
                          </p>
                        )}
                        {!searching &&
                          suggestions.map((s, i) => (
                            <button
                              key={`${s.name}-${i}`}
                              onClick={() => selectSuggestion(s)}
                              className="block w-full border-b border-gray-100 p-3 text-left last:border-0 hover:bg-green-50"
                            >
                              <p className="font-semibold text-gray-800">
                                📌 {s.name}
                              </p>
                              {s.area && (
                                <p className="text-xs text-gray-500">{s.area}</p>
                              )}
                            </button>
                          ))}
                      </div>
                    )}
                  </div>
                  {/* खाली नतीजे — spelling बदलने को कहो */}
                  {!searching &&
                    searched &&
                    suggestions.length === 0 &&
                    placeInput.trim().length >= 2 && (
                      <p className="text-sm text-orange-600">
                        {t("ads.noResults")}
                      </p>
                    )}
                  {/* नक्शे से सुई — मुफ़्त map में न मिले तो खुद टैप करो (08-10) */}
                  <button
                    type="button"
                    onClick={() => setShowMap(true)}
                    className="self-start text-left text-sm font-semibold text-brand-600 underline"
                  >
                    {t("ads.mapPick")}
                  </button>
                  {/* जुड़ी हुई जगहें — 🟢 हरा = पक्का पता LOCK, नीला = नाम से */}
                  {places.length > 0 && (
                    <>
                      <div className="flex flex-wrap gap-2">
                        {places.map((p) => (
                          <span
                            key={p.name}
                            className={`flex items-center gap-1 rounded-full px-3 py-1 text-sm font-medium ${
                              p.lat != null
                                ? "bg-green-100 text-green-800"
                                : "bg-brand-50 text-brand-600"
                            }`}
                          >
                            {p.lat != null ? "📌" : "📍"} {p.name}
                            {p.area ? (
                              <span className="max-w-32 truncate text-xs opacity-70">
                                · {p.area}
                              </span>
                            ) : null}
                            <button
                              onClick={() => removePlace(p.name)}
                              className="ml-1 font-bold text-gray-400"
                            >
                              ✕
                            </button>
                          </span>
                        ))}
                      </div>
                      <p className="text-xs text-gray-500">
                        {t("ads.lockedHint")}
                      </p>
                    </>
                  )}
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
                    {/* 👀📸 असली LIVE ad — Facebook + Instagram (10-10) */}
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <button
                        className="rounded-full bg-blue-100 px-3 py-1 text-sm font-semibold text-blue-700"
                        onClick={() => handleView(c.id, "fb")}
                        disabled={busy}
                      >
                        👀 {t("ads.liveViewFb")}
                      </button>
                      <button
                        className="rounded-full bg-pink-100 px-3 py-1 text-sm font-semibold text-pink-700"
                        onClick={() => handleView(c.id, "ig")}
                        disabled={busy}
                      >
                        📸 {t("ads.liveViewIg")}
                      </button>
                      {c.status === "active" ? (
                        <button
                          className="rounded-full bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-700"
                          onClick={() => handlePause(c.id)}
                          disabled={busy}
                        >
                          ⏸ {t("ads.pause")}
                        </button>
                      ) : (
                        <>
                          {/* ▶️ रुकी ad फिर चालू करो (10-10 launch day toggle) */}
                          <button
                            className="rounded-full bg-green-100 px-3 py-1 text-sm font-semibold text-green-700"
                            onClick={() => handleResume(c.id)}
                            disabled={busy}
                          >
                            ▶️ {t("ads.resume")}
                          </button>
                          {/* रुकी/draft ad हटाएँ — record सुरक्षित रहता है */}
                          <button
                            className="rounded-full bg-red-100 px-3 py-1 text-sm font-semibold text-red-600"
                            onClick={() => handleDelete(c)}
                            disabled={busy}
                            title={t("ads.delete")}
                          >
                            🗑 {t("ads.delete")}
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))
              )}

              {/* 📜 रिकॉर्ड — हटाई गई ads का इतिहास (08-10 user माँग:
                  "kitni ads chalai he, kis kis ki" हमेशा दिखे) */}
              <button
                className="mt-2 w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-2 text-sm font-semibold text-gray-600"
                onClick={toggleRecords}
              >
                📜 {t("ads.records")} {showRecords ? "▲" : "▼"}
              </button>
              {showRecords && (
                <div className="card space-y-3">
                  {!records ? (
                    <p className="py-4 text-center text-gray-400">{t("loading")}</p>
                  ) : (
                    <>
                      <p className="text-sm font-semibold text-gray-600">
                        {t("ads.totalAds")}: {records.total_ads} · 🗑{" "}
                        {records.deleted_count}
                      </p>
                      {records.records.length === 0 ? (
                        <p className="py-3 text-center text-sm text-gray-400">
                          {t("ads.noRecords")}
                        </p>
                      ) : (
                        records.records.map((r) => (
                          <div
                            key={r.id}
                            className="rounded-xl bg-gray-50 p-3 text-sm"
                          >
                            <p className="font-semibold text-gray-700">
                              🗑 {r.name}
                            </p>
                            <p className="text-gray-500">
                              {formatRupees(r.budget_daily)} {t("ads.daily")} ·{" "}
                              {t("ads.deletedBadge")}
                            </p>
                          </div>
                        ))
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
      {/* नक्शे से सुई modal — खोज में न मिली जगह खुद टैप करके LOCK (08-10) */}
      {showMap && (
        <MapPinPicker
          stateName={state}
          initialName={placeInput}
          onClose={() => setShowMap(false)}
          onPick={({ name, lat, lon }) => {
            if (!places.some((p) => p.name === name) && places.length < 10) {
              setPlaces([
                ...places,
                { name, area: t("ads.mapFromMap"), lat, lon },
              ]);
            }
            setPlaceInput("");
            setSuggestions([]);
            setSearched(false);
            setShowMap(false);
          }}
        />
      )}
    </div>
  );
}
