import { BarChart3, TrendingUp, Users, Image, LineChart } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const tabs = [
  { id: "performance", label: "Performance", icon: <TrendingUp size={16} /> },
  { id: "audience", label: "Audience", icon: <Users size={16} /> },
  { id: "creative", label: "Creative", icon: <Image size={16} /> },
  { id: "forecast", label: "Forecast", icon: <LineChart size={16} /> },
];

export function AnalyticsPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Analytics</h1>
        <p className="text-sm text-text-muted mt-1">Performance, audience, creative analysis, and AI-powered forecasts</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-xl bg-surface-card border border-surface-border/50 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-all"
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Forecast preview */}
      <Card className="bg-gradient-to-br from-brand-blue/5 to-brand-purple/5 border-brand-blue/20">
        <CardContent className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <LineChart size={18} className="text-brand-blue" />
            <h3 className="text-sm font-semibold text-text-primary">Claude Forecast — Tomorrow</h3>
          </div>
          <div className="grid grid-cols-3 gap-6">
            {[
              { label: "Expected Spend", value: "$132", confidence: "92%" },
              { label: "Expected CPA", value: "$4.61", confidence: "89%" },
              { label: "Expected Conversions", value: "28", confidence: "87%" },
            ].map((item) => (
              <div key={item.label}>
                <div className="text-xs text-text-muted mb-1">{item.label}</div>
                <div className="text-2xl font-bold text-text-primary">{item.value}</div>
                <div className="text-[11px] text-brand-green mt-1">{item.confidence} confidence</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
