import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BarChart3,
  TrendingUp,
  Users,
  Image,
  LineChart,
  DollarSign,
  Target,
  Smartphone,
  Globe,
  RefreshCw,
  Sparkles,
  ChevronDown,
  Calendar,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { MetricCard } from "@/components/ai/MetricCard";
import { formatCurrency, formatNumber, cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api";
import { useSessionId } from "@/contexts/AuthContext";
import type { MetricCardData } from "@/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CampaignRecord {
  adset_id: string;
  name: string;
  event: string;
  status: string;
  created_at: string;
}

interface DashboardSummary {
  total_campaigns: number;
  active_campaigns: number;
  total_spend_last_30d: number;
  avg_ccco_lift: number;
  recent_campaigns: CampaignRecord[];
  credits_balance: number;
  last_synced: string | null;
}

interface InsightRecord {
  adset_id: string;
  date: string;
  conversions_web: number;
  conversions_app: number;
  spend: number;
  cpa: number;
  channel_split_web: number;
  channel_split_app: number;
}

interface DashboardResponse {
  adset_id: string;
  total_conversions: number;
  total_spend: number;
  avg_cpa: number;
  ccco_lift_percent: number;
  channel_breakdown: { web: number; app: number };
  daily_insights: InsightRecord[];
}

type TabId = "performance" | "audience" | "creative" | "forecast";

const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: "performance", label: "Performance", icon: <TrendingUp size={16} /> },
  { id: "audience", label: "Audience", icon: <Users size={16} /> },
  { id: "creative", label: "Creative", icon: <Image size={16} /> },
  { id: "forecast", label: "Forecast", icon: <LineChart size={16} /> },
];

// ---------------------------------------------------------------------------
// Sparkline mini bar chart
// ---------------------------------------------------------------------------

function MiniBarChart({ data, height = 80 }: { data: number[]; height?: number }) {
  if (!data.length) return null;
  const max = Math.max(...data, 1);
  const width = 100;
  const barWidth = Math.max(4, Math.floor(width / data.length) - 2);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" preserveAspectRatio="none">
      {data.map((val, i) => {
        const barH = (val / max) * (height - 4);
        return (
          <rect
            key={i}
            x={i * (barWidth + 2) + 1}
            y={height - 2 - barH}
            width={barWidth}
            height={barH}
            rx={2}
            className="fill-brand-blue/60 hover:fill-brand-blue transition-colors"
          />
        );
      })}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Channel split donut (simple SVG)
// ---------------------------------------------------------------------------

function ChannelDonut({ web, app }: { web: number; app: number }) {
  const total = web + app || 1;
  const webPct = (web / total) * 100;
  const appPct = (app / total) * 100;
  const r = 28;
  const circ = 2 * Math.PI * r;

  return (
    <div className="flex items-center gap-4">
      <svg width="72" height="72" viewBox="0 0 72 72" className="flex-shrink-0">
        <circle cx="36" cy="36" r={r} fill="none" stroke="rgb(30 41 59)" strokeWidth="8" />
        <circle
          cx="36"
          cy="36"
          r={r}
          fill="none"
          stroke="rgb(59 130 246)"
          strokeWidth="8"
          strokeDasharray={`${(webPct / 100) * circ} ${circ}`}
          strokeDashoffset={0}
          transform="rotate(-90 36 36)"
          className="transition-all"
        />
        <circle
          cx="36"
          cy="36"
          r={r}
          fill="none"
          stroke="rgb(139 92 246)"
          strokeWidth="8"
          strokeDasharray={`${(appPct / 100) * circ} ${circ}`}
          strokeDashoffset={-(webPct / 100) * circ}
          transform="rotate(-90 36 36)"
          className="transition-all"
        />
      </svg>
      <div className="space-y-2 text-xs">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-sm bg-brand-blue" />
          <span className="text-text-secondary">Web</span>
          <span className="text-text-primary font-medium">{webPct.toFixed(0)}%</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-sm bg-brand-purple" />
          <span className="text-text-secondary">App</span>
          <span className="text-text-primary font-medium">{appPct.toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Daily insights table
// ---------------------------------------------------------------------------

function DailyInsightsTable({ insights }: { insights: InsightRecord[] }) {
  if (!insights.length) {
    return <p className="text-sm text-text-muted py-4 text-center">No daily insights available. Sync campaign data to see daily performance.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-text-muted uppercase tracking-wider border-b border-surface-border/50">
            <th className="text-left py-2 pr-4 font-medium">Date</th>
            <th className="text-right py-2 px-4 font-medium">Spend</th>
            <th className="text-right py-2 px-4 font-medium">CPA</th>
            <th className="text-right py-2 px-4 font-medium">Web Conv.</th>
            <th className="text-right py-2 px-4 font-medium">App Conv.</th>
            <th className="text-right py-2 pl-4 font-medium">Web Split</th>
          </tr>
        </thead>
        <tbody>
          {insights.map((row) => (
            <tr key={row.date} className="border-b border-surface-border/20 hover:bg-surface-hover/30 transition-colors">
              <td className="py-2.5 pr-4 text-text-primary font-medium">{row.date}</td>
              <td className="py-2.5 px-4 text-right text-text-primary">{formatCurrency(row.spend)}</td>
              <td className="py-2.5 px-4 text-right text-text-primary">{formatCurrency(row.cpa)}</td>
              <td className="py-2.5 px-4 text-right text-text-primary">{formatNumber(row.conversions_web)}</td>
              <td className="py-2.5 px-4 text-right text-text-primary">{formatNumber(row.conversions_app)}</td>
              <td className="py-2.5 pl-4 text-right text-text-primary">{row.channel_split_web.toFixed(0)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Forecast tab
// ---------------------------------------------------------------------------

function ForecastTab() {
  const [forecast, setForecast] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const generateForecast = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ai/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: "Based on typical e-commerce campaign data, provide a 7-day forecast for spend, CPA, and conversions. Format as bullet points with expected values and confidence ranges.",
          provider: "claude",
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setForecast(data.response);
      } else {
        setForecast("Unable to generate forecast. Configure Claude API key in Settings for AI-powered forecasts.");
      }
    } catch {
      setForecast("Forecast unavailable in offline mode. Connect to the backend and configure Claude for AI-powered predictions.");
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="space-y-4">
      <Card className="bg-gradient-to-br from-brand-blue/5 to-brand-purple/5 border-brand-blue/20">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <LineChart size={18} className="text-brand-blue" />
              <h3 className="text-sm font-semibold text-text-primary">Claude AI Forecast</h3>
            </div>
            <Button variant="outline" size="sm" onClick={generateForecast} disabled={loading}>
              <RefreshCw size={14} className={cn("mr-1.5", loading && "animate-spin")} />
              {loading ? "Generating..." : "Generate Forecast"}
            </Button>
          </div>

          <AnimatePresence mode="wait">
            {forecast ? (
              <motion.div
                key="forecast"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-sm text-text-secondary leading-relaxed whitespace-pre-line"
              >
                {forecast}
              </motion.div>
            ) : (
              <motion.div
                key="placeholder"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-sm text-text-muted text-center py-8"
              >
                <Sparkles size={32} className="mx-auto mb-3 text-text-muted/40" />
                <p>Click "Generate Forecast" to get an AI-powered 7-day outlook</p>
                <p className="text-xs mt-1">Powered by Claude — requires API key in Settings</p>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>

      {/* Sample forecast metrics */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: "Expected Spend (7d)", value: "$840 – $1,120" },
          { label: "Expected CPA Range", value: "$4.20 – $5.10" },
          { label: "Expected Conversions", value: "180 – 220" },
        ].map((item) => (
          <Card key={item.label}>
            <CardContent className="p-4 text-center">
              <div className="text-xs text-text-muted mb-1">{item.label}</div>
              <div className="text-lg font-bold text-text-primary">{item.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Audience tab
// ---------------------------------------------------------------------------

function AudienceTab({ campaign }: { campaign: CampaignRecord | null }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card>
        <CardContent className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <Globe size={16} className="text-brand-blue" />
            <h3 className="text-sm font-semibold text-text-primary">Geographic Distribution</h3>
          </div>
          <p className="text-sm text-text-muted">
            {campaign
              ? `Audience data for "${campaign.name}" will appear here after syncing insights.`
              : "Select a campaign to view audience demographics."}
          </p>
          <div className="mt-4 h-32 rounded-xl bg-surface-hover/50 flex items-center justify-center">
            <span className="text-xs text-text-muted">Map visualization (coming soon)</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <Smartphone size={16} className="text-brand-purple" />
            <h3 className="text-sm font-semibold text-text-primary">Device Breakdown</h3>
          </div>
          <p className="text-sm text-text-muted">
            Device-level performance data will be available after sufficient campaign data is collected.
          </p>
          <div className="mt-4 space-y-3">
            {[
              { device: "Mobile", pct: 72, color: "bg-brand-blue" },
              { device: "Desktop", pct: 20, color: "bg-brand-purple" },
              { device: "Tablet", pct: 8, color: "bg-brand-orange" },
            ].map((d) => (
              <div key={d.device}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-text-secondary">{d.device}</span>
                  <span className="text-text-primary font-medium">{d.pct}%</span>
                </div>
                <div className="w-full h-2 rounded-full bg-surface-hover overflow-hidden">
                  <div className={`h-full rounded-full ${d.color} transition-all`} style={{ width: `${d.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Creative tab
// ---------------------------------------------------------------------------

function CreativeTab() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {[
        { label: "CTR by Creative", value: "2.4%", change: "+0.3%", color: "text-brand-green" },
        { label: "Top Performing", value: "Spring Sale v2", change: "3.1% CTR", color: "text-brand-blue" },
        { label: "Creative Fatigue", value: "2 variants", change: "CTR declining", color: "text-brand-orange" },
      ].map((item) => (
        <Card key={item.label}>
          <CardContent className="p-4">
            <div className="text-xs text-text-muted mb-1">{item.label}</div>
            <div className="text-lg font-bold text-text-primary">{item.value}</div>
            <div className={`text-xs mt-1 ${item.color}`}>{item.change}</div>
          </CardContent>
        </Card>
      ))}

      <Card className="md:col-span-3">
        <CardContent className="p-5">
          <div className="flex items-center gap-2 mb-4">
            <Image size={16} className="text-brand-green" />
            <h3 className="text-sm font-semibold text-text-primary">Creative Performance</h3>
          </div>
          <p className="text-sm text-text-muted">
            Detailed creative performance metrics and A/B test results will appear here. Use the{" "}
            <span className="text-brand-blue font-medium">Creative Lab</span> to generate and test new variants.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Analytics Page
// ---------------------------------------------------------------------------

export function AnalyticsPage() {
  const sessionId = useSessionId();
  const [activeTab, setActiveTab] = useState<TabId>("performance");
  const [campaigns, setCampaigns] = useState<CampaignRecord[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<string | null>(null);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [campaignLoading, setCampaignLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch campaigns & summary on mount
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [campaignsRes, summaryRes] = await Promise.all([
          fetch(`${API_BASE}/campaigns/ccco?session_id=${sessionId}`),
          fetch(`${API_BASE}/dashboard/summary?session_id=${sessionId}`),
        ]);

        if (campaignsRes.ok) {
          const data = await campaignsRes.json();
          setCampaigns(data);
          if (data.length > 0 && !selectedCampaign) {
            setSelectedCampaign(data[0].adset_id);
          }
        }

        if (summaryRes.ok) {
          setSummary(await summaryRes.json());
        }
      } catch (err) {
        setError("Unable to connect to backend. Start the server to see live analytics.");
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch per-campaign dashboard when selection changes
  useEffect(() => {
    if (!selectedCampaign) return;
    setCampaignLoading(true);
    fetch(`${API_BASE}/dashboard/ccco/${selectedCampaign}?session_id=${sessionId}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setDashboard(data))
      .catch(() => setDashboard(null))
      .finally(() => setCampaignLoading(false));
  }, [selectedCampaign]);

  const selectedName = campaigns.find((c) => c.adset_id === selectedCampaign)?.name;

  // Build summary metrics
  const metricCards: MetricCardData[] = summary
    ? [
        {
          label: "Total Spend (30d)",
          value: formatCurrency(summary.total_spend_last_30d),
          trend: summary.total_spend_last_30d > 0 ? "up" : "neutral",
        },
        {
          label: "Active Campaigns",
          value: String(summary.active_campaigns),
          change: summary.active_campaigns > 0 ? 100 : 0,
          trend: summary.active_campaigns > 0 ? "up" : "neutral",
        },
        {
          label: "Avg CCCO Lift",
          value: `${summary.avg_ccco_lift.toFixed(1)}%`,
          trend: summary.avg_ccco_lift > 0 ? "up" : "down",
        },
        {
          label: "Credits Balance",
          value: String(summary.credits_balance),
          trend: "neutral",
        },
      ]
    : [];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-text-primary">Analytics</h1>
        <p className="text-sm text-text-muted mt-1">Performance, audience, creative analysis, and AI-powered forecasts</p>
      </motion.div>

      {/* Campaign selector + summary metrics */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Campaign dropdown */}
        <div className="relative">
          <select
            value={selectedCampaign ?? ""}
            onChange={(e) => setSelectedCampaign(e.target.value || null)}
            className="appearance-none w-64 px-4 py-2.5 rounded-xl bg-surface-card border border-surface-border/50 text-sm text-text-primary font-medium outline-none focus:border-brand-blue/50 transition-all cursor-pointer"
          >
            {campaigns.length === 0 && <option value="">No campaigns found</option>}
            {campaigns.map((c) => (
              <option key={c.adset_id} value={c.adset_id}>
                {c.name}
              </option>
            ))}
          </select>
          <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
        </div>

        {summary?.last_synced && (
          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <Calendar size={12} />
            Last synced: {summary.last_synced}
          </div>
        )}
      </div>

      {/* Error state */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-4 rounded-xl bg-brand-orange/5 border border-brand-orange/20 text-sm text-text-secondary"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Summary metric cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {metricCards.map((m, i) => (
            <MetricCard key={m.label} data={m} delay={i * 0.06} />
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-xl bg-surface-card border border-surface-border/50 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              activeTab === tab.id
                ? "bg-brand-blue/10 text-brand-blue shadow-sm"
                : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
          className="space-y-6"
        >
          {activeTab === "performance" && (
            <>
              {/* Campaign dashboard */}
              {selectedCampaign && dashboard && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <Card>
                      <CardContent className="p-4">
                        <div className="text-xs text-text-muted mb-1">Total Spend</div>
                        <div className="text-xl font-bold text-text-primary">{formatCurrency(dashboard.total_spend)}</div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4">
                        <div className="text-xs text-text-muted mb-1">Total Conversions</div>
                        <div className="text-xl font-bold text-text-primary">{formatNumber(dashboard.total_conversions)}</div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4">
                        <div className="text-xs text-text-muted mb-1">Avg CPA</div>
                        <div className="text-xl font-bold text-text-primary">{formatCurrency(dashboard.avg_cpa)}</div>
                      </CardContent>
                    </Card>
                    <Card className="bg-gradient-to-br from-brand-green/5 to-brand-blue/5 border-brand-green/20">
                      <CardContent className="p-4">
                        <div className="text-xs text-text-muted mb-1">CCCO Lift</div>
                        <div className="text-xl font-bold text-brand-green">+{dashboard.ccco_lift_percent.toFixed(1)}%</div>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Channel breakdown + daily spend chart */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <Card className="lg:col-span-2">
                      <CardContent className="p-5">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-sm font-semibold text-text-primary">Daily Spend Trend</h3>
                          <Badge variant="blue" className="text-[10px]">
                            Last {dashboard.daily_insights.length} days
                          </Badge>
                        </div>
                        {dashboard.daily_insights.length > 0 ? (
                          <MiniBarChart
                            data={dashboard.daily_insights.map((d) => d.spend).reverse()}
                            height={100}
                          />
                        ) : (
                          <div className="h-24 rounded-xl bg-surface-hover/50 flex items-center justify-center">
                            <span className="text-xs text-text-muted">No daily data — sync a campaign</span>
                          </div>
                        )}
                      </CardContent>
                    </Card>

                    <Card>
                      <CardContent className="p-5">
                        <div className="flex items-center gap-2 mb-4">
                          <BarChart3 size={16} className="text-brand-purple" />
                          <h3 className="text-sm font-semibold text-text-primary">Channel Split</h3>
                        </div>
                        <ChannelDonut web={dashboard.channel_breakdown.web} app={dashboard.channel_breakdown.app} />
                      </CardContent>
                    </Card>
                  </div>

                  {/* Daily insights table */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Daily Insights</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <DailyInsightsTable insights={dashboard.daily_insights} />
                    </CardContent>
                  </Card>
                </>
              )}

              {selectedCampaign && campaignLoading && (
                <div className="text-center py-12">
                  <RefreshCw size={24} className="animate-spin mx-auto mb-3 text-text-muted" />
                  <p className="text-sm text-text-muted">Loading campaign data...</p>
                </div>
              )}

              {selectedCampaign && !dashboard && !campaignLoading && (
                <Card>
                  <CardContent className="p-8 text-center">
                    <BarChart3 size={32} className="mx-auto mb-3 text-text-muted/40" />
                    <h3 className="text-sm font-semibold text-text-primary mb-1">No Data Yet</h3>
                    <p className="text-xs text-text-muted">
                      Sync campaign insights from Meta to see performance data. Go to Integrations to connect your ad account.
                    </p>
                  </CardContent>
                </Card>
              )}

              {!selectedCampaign && !loading && (
                <Card>
                  <CardContent className="p-8 text-center">
                    <Target size={32} className="mx-auto mb-3 text-text-muted/40" />
                    <h3 className="text-sm font-semibold text-text-primary mb-1">No Campaigns</h3>
                    <p className="text-xs text-text-muted">
                      Create a campaign using the Campaign Builder to start seeing analytics.
                    </p>
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {activeTab === "audience" && (
            <AudienceTab campaign={selectedCampaign ? campaigns.find((c) => c.adset_id === selectedCampaign) ?? null : null} />
          )}

          {activeTab === "creative" && <CreativeTab />}

          {activeTab === "forecast" && <ForecastTab />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
