import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { Shell } from "@/components/layout/Shell";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PageSkeleton } from "@/components/ui/skeleton";

// ── Lazy-loaded route pages for code splitting ────────────────────────

const HomePage = lazy(() =>
  import("@/pages/Home").then((m) => ({ default: m.HomePage }))
);
const CampaignsPage = lazy(() =>
  import("@/pages/Campaigns").then((m) => ({ default: m.CampaignsPage }))
);
const AIStudioPage = lazy(() =>
  import("@/pages/AIStudio").then((m) => ({ default: m.AIStudioPage }))
);
const CreativeLabPage = lazy(() =>
  import("@/pages/CreativeLab").then((m) => ({ default: m.CreativeLabPage }))
);
const AnalyticsPage = lazy(() =>
  import("@/pages/Analytics").then((m) => ({ default: m.AnalyticsPage }))
);
const IntegrationsPage = lazy(() =>
  import("@/pages/Integrations").then((m) => ({ default: m.IntegrationsPage }))
);
const SettingsPage = lazy(() =>
  import("@/pages/Settings").then((m) => ({ default: m.SettingsPage }))
);

function SuspendedPage({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageSkeleton />}>{children}</Suspense>
    </ErrorBoundary>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route
              path="/"
              element={
                <SuspendedPage>
                  <HomePage />
                </SuspendedPage>
              }
            />
            <Route
              path="/campaigns"
              element={
                <SuspendedPage>
                  <CampaignsPage />
                </SuspendedPage>
              }
            />
            <Route
              path="/ai-studio"
              element={
                <SuspendedPage>
                  <AIStudioPage />
                </SuspendedPage>
              }
            />
            <Route
              path="/creative-lab"
              element={
                <SuspendedPage>
                  <CreativeLabPage />
                </SuspendedPage>
              }
            />
            <Route
              path="/analytics"
              element={
                <SuspendedPage>
                  <AnalyticsPage />
                </SuspendedPage>
              }
            />
            <Route
              path="/integrations"
              element={
                <SuspendedPage>
                  <IntegrationsPage />
                </SuspendedPage>
              }
            />
            <Route
              path="/settings"
              element={
                <SuspendedPage>
                  <SettingsPage />
                </SuspendedPage>
              }
            />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
