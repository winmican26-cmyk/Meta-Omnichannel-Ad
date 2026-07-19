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

// ---------------------------------------------------------------------------
// Campaign Builder Types
// ---------------------------------------------------------------------------

export type WizardStep = "objective" | "audience" | "budget" | "creative" | "review";

export const WIZARD_STEPS: WizardStep[] = [
  "objective",
  "audience",
  "budget",
  "creative",
  "review",
];

export const WIZARD_STEP_LABELS: Record<WizardStep, string> = {
  objective: "Objective",
  audience: "Audience",
  budget: "Budget",
  creative: "Creative",
  review: "Review & Launch",
};

export interface CampaignObjective {
  objective: string;
  label: string;
  event: string;
  description: string;
  icon: string;
  color: string;
  meta?: Record<string, string>;
}

export interface AudienceData {
  countries: string[];
  country_names: string[];
}

export interface BudgetData {
  daily_budget_cents: number;
  bid_amount_cents: number | null;
  has_bid_cap: boolean;
}

export interface CreativeData {
  campaign_name: string;
  web_url: string;
  message: string;
  page_id: string;
  application_id: string;
  pixel_id: string;
  android_deeplink: string | null;
  ios_deeplink: string | null;
  call_to_action: string;
  call_to_action_label?: string;
}

export interface StepData {
  objective?: CampaignObjective;
  audience?: AudienceData;
  budget?: BudgetData;
  creative?: CreativeData;
}

export interface CampaignDraft {
  id: number;
  current_step: number;
  is_complete: boolean;
  step_data: StepData;
  created_at: string;
  updated_at: string;
  objective_label?: string;
  campaign_name?: string;
}

export interface DraftCreateResponse {
  draft_id: number;
  current_step: number;
  step_data: StepData;
}

export interface DraftUpdateResponse {
  draft_id: number;
  current_step: number;
  step_data: StepData;
}

export interface ValidateStepResponse {
  valid: boolean;
  missing_fields: string[];
  step: string;
}

export interface DraftLaunchResponse {
  success: boolean;
  adset_id: string | null;
  creative_id: string | null;
  ad_id: string | null;
  message: string;
}
