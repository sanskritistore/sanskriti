/**
 * AppShell — outermost wrapper. Currently a passthrough;
 * reserved for global banners (e.g., offline notice) later.
 */
export default function AppShell({ children }) {
  return <>{children}</>;
}
