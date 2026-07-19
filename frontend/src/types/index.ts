export type NavSection =
  | "overview"
  | "campaigns"
  | "ai-studio"
  | "creative-lab"
  | "analytics"
  | "integrations"
  | "settings";

export interface NavItem {
  id: NavSection;
  label: string;
  icon: string;
  path: string;
  badge?: number;
}

export interface MetricCardData {
  label: string;
  value: string;
  change?: number;
  trend?: "up" | "down" | "neutral";
  tooltip?: string;
}

export interface AIRecommendation {
  id: string;
  title: string;
  description: string;
  impact: number;
  impactLabel: string;
  confidence: number;
  expectedChange: string;
  action: string;
  source: "claude" | "rule-engine";
  timestamp: string;
}

export interface TimelineEvent {
  id: string;
  time: string;
  label: string;
  type: "optimization" | "creative" | "launch" | "alert" | "approval";
  description: string;
  impact?: string;
}

export interface CampaignSummary {
  id: string;
  name: string;
  status: "active" | "paused" | "draft" | "completed";
  spend: number;
  impressions: number;
  conversions: number;
  cpa: number;
  roas: number;
}

export interface AIMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}
