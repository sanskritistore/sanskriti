"use client";

import { useLanguage } from "@/lib/LanguageContext";

/**
 * LanguageToggle — Hindi is default; this button switches to English
 * (and back to Hindi). Label always shows the *other* language.
 */
export default function LanguageToggle() {
  const { lang, setLang, t } = useLanguage();
  return (
    <button
      onClick={() => setLang(lang === "hi" ? "en" : "hi")}
      className="rounded-full border-2 border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-gray-600 hover:border-brand-500 hover:text-brand-600"
      aria-label={t("lang.current")}
    >
      🌐 {t("lang.toggle")}
    </button>
  );
}
