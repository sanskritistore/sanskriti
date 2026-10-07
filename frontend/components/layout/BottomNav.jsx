"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLanguage } from "@/lib/LanguageContext";

/**
 * BottomNav — mobile-first, thumb-reachable navigation.
 * 4 items max, large touch targets (min 48px), icon + Hindi label.
 */
const ITEMS = [
  { href: "/products", icon: "📦", key: "nav.products" },
  { href: "/ads", icon: "📣", key: "nav.ads" },
  { href: "/reports", icon: "📊", key: "nav.reports" },
  { href: "/settings", icon: "⚙️", key: "nav.settings" },
];

export default function BottomNav() {
  const { t } = useLanguage();
  const pathname = usePathname();

  return (
    <nav className="fixed inset-x-0 bottom-0 z-50 mx-auto w-full max-w-lg border-t-2 border-gray-200 bg-white/95 backdrop-blur">
      <ul className="flex">
        {ITEMS.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <li key={item.href} className="flex-1">
              <Link
                href={item.href}
                className={`flex min-h-[64px] flex-col items-center justify-center gap-1 text-xs font-semibold transition-colors ${
                  active ? "text-brand-600" : "text-gray-500"
                }`}
              >
                <span className="text-2xl leading-none">{item.icon}</span>
                {t(item.key)}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
