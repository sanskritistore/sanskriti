/** @type {import('next').NextConfig} */
// STATIC_EXPORT=1 → pure static site (Render static hosting, free!)
// बिना इसके → Next server mode (local dev में rewrites काम करते हैं)
const isExport = process.env.STATIC_EXPORT === "1";

const nextConfig = {
  reactStrictMode: true,

  ...(isExport
    ? {
        output: "export",
        images: { unoptimized: true },
        trailingSlash: true, // static host पर /products/ → index.html पक्का मिले
      }
    : {
        // PWA headers
        async headers() {
          return [
            {
              source: "/sw.js",
              headers: [
                { key: "Cache-Control", value: "public, max-age=0, must-revalidate" },
                { key: "Service-Worker-Allowed", value: "/" },
              ],
            },
            {
              source: "/manifest.json",
              headers: [{ key: "Cache-Control", value: "public, max-age=86400" }],
            },
          ];
        },

        // Allow backend API calls in dev
        async rewrites() {
          return [
            {
              source: "/api/v1/:path*",
              destination: `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/v1/:path*`,
            },
          ];
        },
      }),
};

export default nextConfig;
