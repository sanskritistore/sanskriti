"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/lib/LanguageContext";
import { useAPI } from "@/lib/api";
import LanguageToggle from "@/components/ui/LanguageToggle";
import StepDots from "@/components/ui/StepDots";

/** Shop categories — plain Hindi words, no jargon */
const CATEGORIES = [
  { value: "kirana", hi: "किराना दुकान", en: "Grocery" },
  { value: "clothing", hi: "कपड़े की दुकान", en: "Clothing" },
  { value: "food", hi: "खाने की दुकान", en: "Food" },
  { value: "electronics", hi: "इलेक्ट्रॉनिक्स", en: "Electronics" },
  { value: "salon", hi: "सैलून", en: "Salon" },
  { value: "other", hi: "अन्य", en: "Other" },
];

/**
 * Settings — business profile in 3 steps:
 *   Step 1: shop name & owner
 *   Step 2: shop type
 *   Step 3: address → save
 */
export default function SettingsPage() {
  const { t, lang } = useLanguage();
  const api = useAPI();
  const router = useRouter();

  const [form, setForm] = useState({
    shop_name: "",
    owner_name: "",
    category: "",
    address: "",
  });
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const [wallet, setWallet] = useState(null);

  useEffect(() => {
    api.business
      .get()
      .then((data) => {
        if (data) {
          setForm((f) => ({ ...f, ...data }));
          setWallet(data.wallet_balance ?? 0);
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSave() {
    setBusy(true);
    try {
      await api.business.update(form);
      setToast(t("settings.saved"));
      setTimeout(() => setToast(""), 2500);
    } catch {
      setToast(t("login.error.generic"));
    } finally {
      setBusy(false);
    }
  }

  function handleLogout() {
    api.logout();
    router.replace("/login");
  }

  const set = (key) => (e) =>
    setForm((f) => ({ ...f, [key]: e.target ? e.target.value : e }));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("settings.title")}</h1>
        <LanguageToggle />
      </div>

      {toast && (
        <p className="rounded-xl bg-green-50 p-3 text-center font-semibold text-hindi-success">
          {toast}
        </p>
      )}

      {/* 💰 Wallet — दुकानदार का पैसा सबसे ऊपर */}
      {wallet !== null && (
        <div className="card bg-gradient-to-r from-brand-50 to-white text-center">
          <p className="text-sm font-semibold text-gray-500">
            {t("settings.wallet")}
          </p>
          <p className="mt-1 text-3xl font-bold text-brand-600">
            ₹{Number(wallet).toLocaleString("en-IN")}
          </p>
          <p className="mt-1 text-xs text-gray-400">
            {t("settings.walletHint")}
          </p>
        </div>
      )}

      <div className="card space-y-4">
        <StepDots step={step} total={3} />

        {/* STEP 1: names */}
        {step === 1 && (
          <div className="space-y-4">
            <div>
              <label className="label">{t("settings.shopName")}</label>
              <input
                className="input"
                value={form.shop_name}
                onChange={set("shop_name")}
                autoFocus
              />
            </div>
            <div>
              <label className="label">{t("settings.ownerName")}</label>
              <input
                className="input"
                value={form.owner_name}
                onChange={set("owner_name")}
              />
            </div>
            <button
              className="btn-primary w-full"
              onClick={() => setStep(2)}
              disabled={!form.shop_name}
            >
              {t("next")}
            </button>
          </div>
        )}

        {/* STEP 2: category */}
        {step === 2 && (
          <div className="space-y-4">
            <label className="label">{t("settings.category")}</label>
            <div className="grid grid-cols-2 gap-3">
              {CATEGORIES.map((c) => (
                <button
                  key={c.value}
                  onClick={() => {
                    setForm((f) => ({ ...f, category: c.value }));
                    setStep(3);
                  }}
                  className={`card py-4 text-center font-semibold transition-colors ${
                    form.category === c.value
                      ? "bg-brand-500 text-white ring-brand-500"
                      : ""
                  }`}
                >
                  {lang === "hi" ? c.hi : c.en}
                </button>
              ))}
            </div>
            <button className="btn-secondary w-full" onClick={() => setStep(1)}>
              {t("back")}
            </button>
          </div>
        )}

        {/* STEP 3: address & save */}
        {step === 3 && (
          <div className="space-y-4">
            <div>
              <label className="label">
                {t("settings.address")} <span className="text-gray-400">({t("optional")})</span>
              </label>
              <textarea
                className="input min-h-[96px]"
                value={form.address}
                onChange={set("address")}
              />
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

      <button className="btn-danger w-full" onClick={handleLogout}>
        {t("settings.logout")}
      </button>
    </div>
  );
}
