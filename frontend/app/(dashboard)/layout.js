"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import BottomNav from "@/components/layout/BottomNav";
import { useAPI } from "@/lib/api";

/**
 * Dashboard layout — guards auth and wraps pages with the
 * mobile-first bottom navigation (thumb-friendly).
 */
export default function DashboardLayout({ children }) {
  const api = useAPI();
  const router = useRouter();
  const pathname = usePathname();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const token =
      typeof window !== "undefined" && localStorage.getItem("sanskriti_token");
    if (!token) {
      router.replace("/login");
    } else {
      setChecked(true);
    }
  }, [router, pathname]);

  if (!checked) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <p className="text-gray-400">…</p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-lg flex-col">
      <main className="flex-1 px-4 pb-24 pt-6">{children}</main>
      <BottomNav />
    </div>
  );
}
