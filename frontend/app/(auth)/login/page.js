"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/lib/LanguageContext";
import { useAPI } from "@/lib/api";
import { isValidOtp, isValidPhone } from "@/lib/utils";
import StepDots from "@/components/ui/StepDots";
import LanguageToggle from "@/components/ui/LanguageToggle";

/**
 * Login — phone + OTP, strictly 3 steps (architecture rule):
 *   Step 1: enter mobile number
 *   Step 2: enter OTP
 *   Step 3: done → redirect into the app
 */
export default function LoginPage() {
  const { t } = useLanguage();
  const api = useAPI();
  const router = useRouter();

  const [step, setStep] = useState(1);
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [devOtp, setDevOtp] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSendOtp(e) {
    e.preventDefault();
    setError("");
    if (!isValidPhone(phone)) {
      setError(t("login.error.phone"));
      return;
    }
    setBusy(true);
    try {
      const res = await api.auth.sendOtp(phone);
      if (res?.dev_otp) setDevOtp(res.dev_otp);
      setStep(2);
    } catch (err) {
      setError(err.message || t("login.error.generic"));
    } finally {
      setBusy(false);
    }
  }

  async function handleVerifyOtp(e) {
    e.preventDefault();
    setError("");
    if (!isValidOtp(otp)) {
      setError(t("login.error.otp"));
      return;
    }
    setBusy(true);
    try {
      const res = await api.auth.verifyOtp(phone, otp);
      if (res?.token) api.setAuthToken(res.token);
      setStep(3);
      // Brief success moment, then into the app
      setTimeout(() => router.replace("/products"), 800);
    } catch (err) {
      setError(err.message || t("login.error.generic"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="mb-2 flex justify-end">
        <LanguageToggle />
      </div>

      <div className="mb-6 text-center">
        <div className="text-5xl">🪔</div>
        <h1 className="mt-2 text-2xl font-bold">{t("login.title")}</h1>
        <p className="mt-1 text-gray-500">{t("login.subtitle")}</p>
      </div>

      {/* 3-step progress indicator */}
      <div className="mb-6">
        <StepDots step={step} total={3} />
        <p className="mt-2 text-center text-sm font-medium text-brand-600">
          {step === 1 && t("login.step1")}
          {step === 2 && t("login.step2")}
          {step === 3 && t("login.step3")}
        </p>
      </div>

      {error && (
        <p className="mb-4 rounded-xl bg-red-50 p-3 text-center text-red-600">
          {error}
        </p>
      )}

      {/* STEP 1: phone number */}
      {step === 1 && (
        <form onSubmit={handleSendOtp} className="space-y-4">
          <div>
            <label className="label" htmlFor="phone">
              {t("login.phoneLabel")}
            </label>
            <div className="flex items-stretch gap-2">
              <span className="flex min-h-[48px] items-center rounded-xl border-2 border-gray-300 bg-gray-50 px-4 font-semibold text-gray-600">
                +91
              </span>
              <input
                id="phone"
                type="tel"
                inputMode="numeric"
                maxLength={10}
                className="input"
                placeholder={t("login.phonePlaceholder")}
                value={phone}
                onChange={(e) =>
                  setPhone(e.target.value.replace(/\D/g, "").slice(0, 10))
                }
                autoFocus
              />
            </div>
          </div>
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? t("loading") : t("login.sendOtp")}
          </button>
        </form>
      )}

      {/* STEP 2: OTP */}
      {step === 2 && (
        <form onSubmit={handleVerifyOtp} className="space-y-4">
          <div>
            <label className="label" htmlFor="otp">
              {t("login.otpLabel")} (+91 {phone})
            </label>
            <input
              id="otp"
              type="tel"
              inputMode="numeric"
              maxLength={6}
              className="input text-center text-2xl tracking-[0.5em]"
              placeholder="••••••"
              value={otp}
              onChange={(e) =>
                setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))
              }
              autoFocus
            />
            <p className="mt-2 text-sm text-gray-500">{t("login.otpHint")}</p>
            {devOtp && (
              <div className="mt-3 rounded-lg border-2 border-dashed border-amber-400 bg-amber-50 p-3 text-center">
                <p className="text-xs text-amber-700">🔑 Testing mode — SMS बाद में आएगा, अभी OTP यहाँ है:</p>
                <p className="mt-1 text-2xl font-bold tracking-[0.4em] text-amber-900">{devOtp}</p>
              </div>
            )}
          </div>
          <button type="submit" className="btn-primary w-full" disabled={busy}>
            {busy ? t("loading") : t("login.verifyOtp")}
          </button>
          <button
            type="button"
            className="btn-secondary w-full"
            onClick={handleSendOtp}
            disabled={busy}
          >
            {t("login.resendOtp")}
          </button>
          <button
            type="button"
            className="w-full text-sm text-gray-500 underline"
            onClick={() => {
              setStep(1);
              setOtp("");
            }}
          >
            {t("back")}
          </button>
        </form>
      )}

      {/* STEP 3: success */}
      {step === 3 && (
        <div className="py-8 text-center">
          <div className="text-6xl">✅</div>
          <p className="mt-4 text-xl font-bold text-hindi-success">
            {t("login.step3")}
          </p>
        </div>
      )}
    </div>
  );
}
