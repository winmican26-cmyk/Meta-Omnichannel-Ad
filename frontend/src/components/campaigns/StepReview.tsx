import { formatCurrency } from "@/lib/utils";
import type { CampaignDraft } from "@/types";

interface StepReviewProps {
  draft: CampaignDraft | null;
}

export function StepReview({ draft }: StepReviewProps) {
  if (!draft) {
    return (
      <div className="text-center py-12 text-text-muted">
        <p>No draft data to review.</p>
      </div>
    );
  }

  const stepData = (draft.step_data as Record<string, any>) || {};
  const objective = stepData.objective || {};
  const audience = stepData.audience || {};
  const budget = stepData.budget || {};
  const creative = stepData.creative || {};

  const sections = [
    {
      title: "Objective",
      items: [
        { label: "Goal", value: (objective as any).label || (objective as any).objective || "Not set" },
        { label: "Event", value: (objective as any).event || "—" },
      ],
    },
    {
      title: "Audience",
      items: [
        {
          label: "Target Countries",
          value: Array.isArray(audience.country_names)
            ? (audience.country_names as string[]).join(", ")
            : Array.isArray(audience.countries)
              ? (audience.countries as string[]).join(", ")
              : "Not set",
        },
        {
          label: "Countries Selected",
          value: String(Array.isArray(audience.countries) ? audience.countries.length : 0),
        },
      ],
    },
    {
      title: "Budget",
      items: [
        {
          label: "Daily Budget",
          value: formatCurrency(((budget as any).daily_budget_cents || 0) / 100),
        },
        {
          label: "Bid Cap",
          value: (budget as any).has_bid_cap
            ? formatCurrency(((budget as any).bid_amount_cents || 0) / 100)
            : "None (automatic)",
        },
        {
          label: "Est. Monthly Spend",
          value: formatCurrency((((budget as any).daily_budget_cents || 0) / 100) * 30),
        },
      ],
    },
    {
      title: "Creative",
      items: [
        { label: "Campaign Name", value: (creative as any).campaign_name || "Not set" },
        { label: "Website URL", value: (creative as any).web_url || "Not set" },
        { label: "Message", value: (creative as any).message || "Not set" },
        {
          label: "Call to Action",
          value: (creative as any).call_to_action_label || (creative as any).call_to_action || "Not set",
        },
        (creative as any).page_id ? { label: "Page ID", value: (creative as any).page_id } : null,
        (creative as any).pixel_id ? { label: "Pixel ID", value: (creative as any).pixel_id } : null,
        (creative as any).application_id ? { label: "App ID", value: (creative as any).application_id } : null,
      ].filter(Boolean) as { label: string; value: string }[],
    },
  ];

  return (
    <div className="space-y-6">
      <div className="mb-2">
        <h3 className="text-lg font-semibold text-text-primary">Review & Launch</h3>
        <p className="text-sm text-text-muted mt-1">
          Review your campaign settings before launching. Click "Launch Campaign" to go live.
        </p>
      </div>

      <div className="space-y-4">
        {sections.map((section) => (
          <div
            key={section.title}
            className="rounded-xl border border-surface-border bg-surface-card overflow-hidden"
          >
            <div className="px-4 py-2.5 bg-surface-hover border-b border-surface-border">
              <h4 className="text-sm font-semibold text-text-primary">{section.title}</h4>
            </div>
            <div className="p-4 space-y-2">
              {section.items.map((item) => (
                <div key={item.label} className="flex items-start justify-between gap-4">
                  <span className="text-sm text-text-muted shrink-0">{item.label}</span>
                  <span className="text-sm text-text-primary text-right font-medium break-all">
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="p-4 rounded-xl bg-brand-blue/5 border border-brand-blue/20">
        <p className="text-sm text-brand-blue">
          By clicking "Launch Campaign", your ad set will be created and paused by default.
          You can activate it from the Campaigns page after reviewing the settings.
        </p>
      </div>
    </div>
  );
}
