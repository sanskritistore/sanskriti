/**
 * Auth layout — centered, minimal, mobile-first.
 * No bottom nav here; the user is not inside the app yet.
 */
export default function AuthLayout({ children }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-gradient-to-b from-brand-50 to-white p-4">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
