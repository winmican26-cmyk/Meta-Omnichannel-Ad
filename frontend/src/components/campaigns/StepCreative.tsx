import { useState } from "react";
import {
  FileText,
  Globe,
  MessageSquare,
  Smartphone,
  Monitor,
  Hash,
  Layout,
  ChevronDown,
} from "lucide-react";

const CTA_OPTIONS = [
  { value: "SHOP_NOW", label: "Shop Now" },
  { value: "LEARN_MORE", label: "Learn More" },
  { value: "SIGN_UP", label: "Sign Up" },
  { value: "CONTACT_US", label: "Contact Us" },
  { value: "DOWNLOAD", label: "Download" },
  { value: "GET_OFFER", label: "Get Offer" },
  { value: "SUBSCRIBE", label: "Subscribe" },
  { value: "APPLY_NOW", label: "Apply Now" },
];

interface StepCreativeProps {
  data: Record<string, unknown>;
  onChange: (data: Record<string, unknown>) => void;
}

export function StepCreative({ data, onChange }: StepCreativeProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const campaignName = (data?.campaign_name as string) || "";
  const webUrl = (data?.web_url as string) || "";
  const message = (data?.message as string) || "";
  const pageId = (data?.page_id as string) || "";
  const applicationId = (data?.application_id as string) || "";
  const pixelId = (data?.pixel_id as string) || "";
  const androidDeeplink = (data?.android_deeplink as string) || "";
  const iosDeeplink = (data?.ios_deeplink as string) || "";
  const cta = (data?.call_to_action as string) || "LEARN_MORE";

  const updateField = (field: string, value: unknown) => {
    onChange({
      ...data,
      [field]: value,
    });
  };

  return (
    <div className="space-y-5">
      <div className="mb-2">
        <h3 className="text-lg font-semibold text-text-primary">Create your ad</h3>
        <p className="text-sm text-text-muted mt-1">
          Set up the creative elements for your campaign.
        </p>
      </div>

      {/* Campaign Name */}
      <div className="space-y-1.5">
        <label className="flex items-center gap-2 text-sm font-medium text-text-primary">
          <FileText size={14} className="text-brand-blue" />
          Campaign Name
        </label>
        <input
          type="text"
          value={campaignName}
          onChange={(e) => updateField("campaign_name", e.target.value)}
          placeholder="e.g., Spring Sale 2026"
          maxLength={120}
          className="w-full px-4 py-2.5 rounded-xl bg-surface-card border border-surface-border text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue/50 text-sm"
        />
      </div>

      {/* Website URL */}
      <div className="space-y-1.5">
        <label className="flex items-center gap-2 text-sm font-medium text-text-primary">
          <Globe size={14} className="text-brand-blue" />
          Website URL
        </label>
        <input
          type="url"
          value={webUrl}
          onChange={(e) => updateField("web_url", e.target.value)}
          placeholder="https://example.com/landing"
          className="w-full px-4 py-2.5 rounded-xl bg-surface-card border border-surface-border text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue/50 text-sm font-mono"
        />
      </div>

      {/* Ad Message */}
      <div className="space-y-1.5">
        <label className="flex items-center gap-2 text-sm font-medium text-text-primary">
          <MessageSquare size={14} className="text-brand-blue" />
          Ad Message
        </label>
        <textarea
          value={message}
          onChange={(e) => updateField("message", e.target.value)}
          placeholder="Enter your ad message..."
          maxLength={500}
          rows={3}
          className="w-full px-4 py-2.5 rounded-xl bg-surface-card border border-surface-border text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue/50 text-sm resize-none"
        />
        <p className="text-xs text-text-muted text-right">{message.length}/500</p>
      </div>

      {/* Call to Action */}
      <div className="space-y-1.5">
        <label className="flex items-center gap-2 text-sm font-medium text-text-primary">
          <Layout size={14} className="text-brand-blue" />
          Call to Action
        </label>
        <div className="flex flex-wrap gap-2">
          {CTA_OPTIONS.map((option) => (
            <button
              key={option.value}
              onClick={() => updateField("call_to_action", option.value)}
              className={`px-3 py-1.5 rounded-lg border text-sm font-medium transition-all ${
                cta === option.value
                  ? "border-brand-blue bg-brand-blue/10 text-brand-blue"
                  : "border-surface-border text-text-secondary hover:border-surface-elevated hover:text-text-primary"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Advanced Section Toggle */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary transition-colors"
      >
        <ChevronDown
          size={16}
          className={`transition-transform ${showAdvanced ? "rotate-180" : ""}`}
        />
        Advanced Settings
      </button>

      {/* Advanced Fields */}
      {showAdvanced && (
        <div className="space-y-4 p-4 rounded-xl bg-surface-hover border border-surface-border">
          <p className="text-xs font-medium text-text-muted uppercase tracking-wider">
            Connection Settings
          </p>

          {/* Page ID */}
          <div className="space-y-1.5">
            <label className="flex items-center gap-2 text-xs font-medium text-text-muted">
              <Monitor size={12} />
              Page ID
            </label>
            <input
              type="text"
              value={pageId}
              onChange={(e) => updateField("page_id", e.target.value)}
              placeholder="Your Facebook/Instagram Page ID"
              className="w-full px-3 py-2 rounded-lg bg-surface-card border border-surface-border text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 text-xs font-mono"
            />
          </div>

          {/* Pixel ID */}
          <div className="space-y-1.5">
            <label className="flex items-center gap-2 text-xs font-medium text-text-muted">
              <Hash size={12} />
              Pixel ID
            </label>
            <input
              type="text"
              value={pixelId}
              onChange={(e) => updateField("pixel_id", e.target.value)}
              placeholder="Your Meta Pixel ID"
              className="w-full px-3 py-2 rounded-lg bg-surface-card border border-surface-border text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 text-xs font-mono"
            />
          </div>

          {/* Application ID */}
          <div className="space-y-1.5">
            <label className="flex items-center gap-2 text-xs font-medium text-text-muted">
              <Smartphone size={12} />
              App ID
            </label>
            <input
              type="text"
              value={applicationId}
              onChange={(e) => updateField("application_id", e.target.value)}
              placeholder="Your mobile app ID (optional)"
              className="w-full px-3 py-2 rounded-lg bg-surface-card border border-surface-border text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 text-xs font-mono"
            />
          </div>

          {/* Deep Links */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="flex items-center gap-2 text-xs font-medium text-text-muted">
                Android Deep Link
              </label>
              <input
                type="text"
                value={androidDeeplink}
                onChange={(e) => updateField("android_deeplink", e.target.value || null)}
                placeholder="myapp://product/123"
                className="w-full px-3 py-2 rounded-lg bg-surface-card border border-surface-border text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 text-xs font-mono"
              />
            </div>
            <div className="space-y-1.5">
              <label className="flex items-center gap-2 text-xs font-medium text-text-muted">
                iOS Deep Link
              </label>
              <input
                type="text"
                value={iosDeeplink}
                onChange={(e) => updateField("ios_deeplink", e.target.value || null)}
                placeholder="myapp://product/123"
                className="w-full px-3 py-2 rounded-lg bg-surface-card border border-surface-border text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 text-xs font-mono"
              />
            </div>
          </div>

          <p className="text-xs text-text-muted">
            These settings connect your ad to your Meta assets. You can find these IDs in your Meta Business account.
          </p>
        </div>
      )}
    </div>
  );
}
