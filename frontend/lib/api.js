"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const APIContext = createContext(null);

const TOKEN_KEY = "sanskriti_token";

/**
 * Minimal API client for the Sanskriti backend.
 * Same-origin by default: /api/v1 requests go through Next.js rewrites
 * (next.config.mjs) to the backend — काम करता है हर domain पर, बिना CORS.
 */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "/api/v1";

/**
 * "सर्वर जाग रहा है" signal — Render का free plan 15 मिनट बाद सो जाता है
 * और जागने में 30-60 सेकंड लगता है। कोई request 4 सेकंड से ज़्यादा लटके
 * तो banner दिखाने के लिए listeners को खबर जाती है।
 */
const wakingListeners = new Set();
let slowRequests = 0;

export function onServerWaking(fn) {
  wakingListeners.add(fn);
  return () => wakingListeners.delete(fn);
}

function bumpSlow(delta) {
  slowRequests = Math.max(0, slowRequests + delta);
  wakingListeners.forEach((fn) => fn(slowRequests > 0));
}

async function request(path, { method = "GET", body, token, ...rest } = {}) {
  const headers = { "Content-Type": "application/json", ...rest.headers };
  if (token) headers.Authorization = `Bearer ${token}`;

  // Cold-start दोस्त: लंबा timeout + 3 कोशिशें (Render जागने में ~30-60s)
  const MAX_ATTEMPTS = 3;
  const TIMEOUT_MS = 75000;
  let lastError;
  let markedSlow = false;
  const slowTimer = setTimeout(() => {
    markedSlow = true;
    bumpSlow(1);
  }, 4000);

  try {
    for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
      try {
        const res = await fetch(`${API_BASE}${path}`, {
          method,
          headers,
          body: body !== undefined ? JSON.stringify(body) : undefined,
          signal: controller.signal,
        });

        if (!res.ok) {
          // 401 = login session खत्म — साफ़ करके login page भेजें,
          // वरना user को खाली list + "गड़बड़" समझ नहीं आती (08-10 शाम user फँसा था)
          if (res.status === 401) {
            try {
              localStorage.removeItem(TOKEN_KEY);
            } catch {
              /* storage बंद हो तो भी आगे बढ़ें */
            }
            if (
              typeof window !== "undefined" &&
              !window.location.pathname.startsWith("/login")
            ) {
              window.location.href = "/login";
            }
          }
          // 5xx = server की तबीयत खराब — दोबारा कोशिश
          // 4xx = असली जवाब (जैसे गलत OTP) — वैसे ही आगे बढ़ाओ
          if (res.status >= 500 && attempt < MAX_ATTEMPTS) {
            await new Promise((r) => setTimeout(r, 2000));
            continue;
          }
          let message = `API error ${res.status}`;
          try {
            const data = await res.json();
            message = data?.detail || data?.message || message;
          } catch {
            /* non-JSON error body */
          }
          const error = new Error(message);
          error.status = res.status;
          throw error;
        }

        // 204 / empty body
        if (res.status === 204) return null;
        const text = await res.text();
        return text ? JSON.parse(text) : null;
      } catch (err) {
        lastError = err;
        const retriable =
          err.name === "AbortError" || // हमारा अपना timeout
          err instanceof TypeError || // network टूटा / proxy ने काटा
          (typeof err.status === "number" && err.status >= 500);
        if (attempt < MAX_ATTEMPTS && retriable) {
          await new Promise((r) => setTimeout(r, 2000));
          continue;
        }
        throw err;
      } finally {
        clearTimeout(timeout);
      }
    }
    throw lastError;
  } finally {
    clearTimeout(slowTimer);
    if (markedSlow) bumpSlow(-1);
  }
}

/**
 * APIProvider — holds the auth token and exposes typed helpers.
 * Every backend call the MVP needs is one function call.
 */
export function APIProvider({ children }) {
  const [token, setToken] = useState(null);
  const [waking, setWaking] = useState(false);

  // "सर्वर जाग रहा है" सूचना सुनो
  useEffect(() => onServerWaking(setWaking), []);

  // Hydrate token on first client render
  useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(TOKEN_KEY);
      if (saved) setToken(saved);
    }
  });

  const setAuthToken = useCallback((value) => {
    setToken(value);
    if (typeof window !== "undefined") {
      if (value) localStorage.setItem(TOKEN_KEY, value);
      else localStorage.removeItem(TOKEN_KEY);
    }
  }, []);

  const api = useMemo(() => {
    const call = (path, opts = {}) => request(path, { ...opts, token });

    return {
      // Auth — phone OTP (3 steps: send OTP → verify → in)
      auth: {
        sendOtp: (phone) =>
          request("/auth/send-otp", { method: "POST", body: { phone } }),
        verifyOtp: (phone, otp) =>
          request("/auth/verify-otp", { method: "POST", body: { phone, otp } }),
      },

      // Business profile
      business: {
        get: () => call("/business"),
        update: (data) => call("/business", { method: "PUT", body: data }),
      },

      // Products
      products: {
        list: () => call("/products"),
        get: (id) => call(`/products/${id}`),
        create: (data) => call("/products", { method: "POST", body: data }),
        update: (id, data) =>
          call(`/products/${id}`, { method: "PUT", body: data }),
        delete: (id) => call(`/products/${id}`, { method: "DELETE" }),
      },

      // Ads
      ads: {
        list: () => call("/ads"),
        get: (id) => call(`/ads/${id}`),
        create: (data) => call("/ads", { method: "POST", body: data }),
        update: (id, data) => call(`/ads/${id}`, { method: "PUT", body: data }),
        delete: (id) => call(`/ads/${id}`, { method: "DELETE" }),
        records: () => call("/ads/records"),
      },

      // Ad Studio — AI द्वारा विज्ञापन text बनाना
      adStudio: {
        generate: (data) =>
          call("/ad-studio/generate", { method: "POST", body: data }),
      },

      // जगह खोज — state के अंदर नाम लिखते ही पते-सहित सुझाव (08-10 UX)
      targeting: {
        searchPlaces: (q, state) =>
          call(
            `/targeting/search-places?q=${encodeURIComponent(q)}&state=${encodeURIComponent(state)}`
          ),
      },

      // Billing — Meta ad खाते की पैसा-स्थिति + सुरक्षित पैसा-डालो link (08-10)
      billing: {
        status: () => call("/billing/status"),
      },

      // Campaigns — असली Meta पर launch होने वाली campaigns (runner)
      campaigns: {
        list: () => call("/campaigns"),
        create: (data) => call("/campaigns", { method: "POST", body: data }),
        launch: (id) => call(`/campaigns/${id}/launch`, { method: "POST" }),
        pause: (id) => call(`/campaigns/${id}/pause`, { method: "POST" }),
        resume: (id) => call(`/campaigns/${id}/resume`, { method: "POST" }),
        delete: (id) => call(`/campaigns/${id}`, { method: "DELETE" }),
        records: () => call("/campaigns/records"),
      },

      // Reports — simple "₹X spent → Y customers"
      reports: {
        summary: () => call("/reports/summary"),
        whoSaw: () => call("/reports/who-saw"),
      },

      // Audiences — ग्राहक phone lists → Meta Custom Audience (09-10 user idea)
      audiences: {
        list: () => call("/audiences"),
        create: (data) => call("/audiences", { method: "POST", body: data }),
        upload: (id, phones) =>
          call(`/audiences/${id}/upload`, {
            method: "POST",
            body: { phones },
          }),
        remove: (id, phones) =>
          call(`/audiences/${id}/remove`, {
            method: "POST",
            body: { phones },
          }),
      },

      // Token management
      token,
      setAuthToken,
      logout: () => setAuthToken(null),
    };
  }, [token, setAuthToken]);

  const value = useMemo(() => ({ ...api, waking }), [api, waking]);

  return <APIContext.Provider value={value}>{children}</APIContext.Provider>;
}

export function useAPI() {
  const ctx = useContext(APIContext);
  if (!ctx) {
    throw new Error("useAPI must be used within <APIProvider>");
  }
  return ctx;
}
