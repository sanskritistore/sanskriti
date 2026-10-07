import "./globals.css";
import { LanguageProvider } from "@/lib/LanguageContext";
import { APIProvider } from "@/lib/api";
import AppShell from "@/components/layout/AppShell";

export const metadata = {
  title: "Sanskriti | संस्कृति",
  description:
    "अपने दुकान का डिजिटल विज्ञापन — आसान, सस्ता, अपनी भाषा में। (Digital advertising for your shop — easy, affordable, in your language.)",
  manifest: "/manifest.json",
  icons: {
    icon: "/icons/icon-192.png",
    apple: "/icons/icon-192.png",
  },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#f97316",
};

export default function RootLayout({ children }) {
  return (
    <html lang="hi">
      <head>
        {/* Register service worker for PWA/offline support */}
        <script
          dangerouslySetInnerHTML={{
            __html: `if ('serviceWorker' in navigator) { window.addEventListener('load', function() { navigator.serviceWorker.register('/sw.js').catch(function(e){ console.warn('SW registration failed', e); }); }); }`,
          }}
        />
      </head>
      <body className="min-h-dvh bg-gray-50 text-gray-900 antialiased">
        <LanguageProvider defaultLanguage="hi">
          <APIProvider>
            <AppShell>{children}</AppShell>
          </APIProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
