"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/lib/LanguageContext";

/**
 * Root page — redirects to dashboard if logged in, else to login.
 * (Keeps entry simple: one tap decision, mobile-first.)
 */
export default function Home() {
  const router = useRouter();
  const { t } = useLanguage();

  useEffect(() => {
    const token =
      typeof window !== "undefined" && localStorage.getItem("sanskriti_token");
    router.replace(token ? "/products" : "/login");
  }, [router]);

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 p-6 text-center">
      <div className="text-5xl">🪔</div>
      <h1 className="text-2xl font-bold">{t("app.name")} · Sanskriti</h1>
      <p className="text-gray-500">{t("loading")}</p>
    </div>
  );
}
