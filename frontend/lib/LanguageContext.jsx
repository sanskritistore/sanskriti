"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { translations } from "./translations";

const LanguageContext = createContext(null);

const STORAGE_KEY = "sanskriti_lang";

/**
 * Language context — Hindi is the DEFAULT language.
 * English is available as a toggle for users who prefer it.
 */
export function LanguageProvider({ children, defaultLanguage = "hi" }) {
  const [lang, setLang] = useState(defaultLanguage);

  // Restore saved preference on mount
  useEffect(() => {
    try {
      const saved =
        typeof window !== "undefined" && localStorage.getItem(STORAGE_KEY);
      if (saved === "hi" || saved === "en") setLang(saved);
    } catch {
      /* storage unavailable — keep default */
    }
  }, []);

  const switchLanguage = useCallback((next) => {
    const value = next === "en" ? "en" : "hi";
    setLang(value);
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      /* ignore */
    }
    if (typeof document !== "undefined") {
      document.documentElement.lang = value;
    }
  }, []);

  // t(key) returns the string for the current language; falls back to
  // Hindi, then the key itself, so missing translations never crash the UI.
  const t = useCallback(
    (key, vars) => {
      let str =
        translations[lang]?.[key] ??
        translations.hi[key] ??
        key;
      if (vars) {
        Object.entries(vars).forEach(([k, v]) => {
          str = str.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
        });
      }
      return str;
    },
    [lang]
  );

  const value = useMemo(
    () => ({ lang, setLang: switchLanguage, t, isHindi: lang === "hi" }),
    [lang, switchLanguage, t]
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    throw new Error("useLanguage must be used within <LanguageProvider>");
  }
  return ctx;
}
