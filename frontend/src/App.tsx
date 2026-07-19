import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Shell } from "@/components/layout/Shell";
import { HomePage } from "@/pages/Home";
import { CampaignsPage } from "@/pages/Campaigns";
import { AIStudioPage } from "@/pages/AIStudio";
import { CreativeLabPage } from "@/pages/CreativeLab";
import { AnalyticsPage } from "@/pages/Analytics";
import { IntegrationsPage } from "@/pages/Integrations";
import { SettingsPage } from "@/pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/campaigns" element={<CampaignsPage />} />
          <Route path="/ai-studio" element={<AIStudioPage />} />
          <Route path="/creative-lab" element={<CreativeLabPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/integrations" element={<IntegrationsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
