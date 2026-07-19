import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Palette,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  Globe,
  Smartphone,
  Monitor,
  ChevronDown,
  ExternalLink,
  Zap,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { formatCurrency, cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api";
import { useSessionId } from "@/contexts/AuthContext";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CampaignRecord {
  adset_id: string;
  name: string;
  event: string;
  status: string;
}

interface CreativeVariant {
  name: string;
  creative_spec: Record<string, unknown>;
  omnichannel_link_spec: Record<string, unknown>;
  deep_link_routing: string;
  expected_ctr_lift: number;
}

interface GenerationHistoryItem {
  id: string;
  campaign_name: string;
  variants: CreativeVariant[];
  timestamp: string;
}

const EVENT_OPTIONS = [
  { value: "PURCHASE", label: "Purchase" },
  { value: "LEAD", label: "Lead" },
  { value: "COMPLETE_REGISTRATION", label: "Complete Registration" },
  { value: "ADD_TO_CART", label: "Add to Cart" },
  { value: "INITIATED_CHECKOUT", label: "Initiated Checkout" },
  { value: "CONTENT_VIEW", label: "Content View" },
  { value: "SEARCH", label: "Search" },
  { value: "SUBSCRIBE", label: "Subscribe" },
  { value: "START_TRIAL", label: "Start Trial" },
  { value: "ADD_TO_WISHLIST", label: "Add to Wishlist" },
  { value: "ADD_PAYMENT_INFO", label: "Add Payment Info" },
];

const CTA_OPTIONS = [
  { value: "LEARN_MORE", label: "Learn More" },
  { value: "SHOP_NOW", label: "Shop Now" },
  { value: "SIGN_UP", label: "Sign Up" },
  { value: "GET_OFFER", label: "Get Offer" },
  { value: "GET_QUOTE", label: "Get Quote" },
  { value: "BOOK_NOW", label: "Book Now" },
  { value: "DOWNLOAD", label: "Download" },
  { value: "CONTACT_US", label: "Contact Us" },
  { value: "SUBSCRIBE", label: "Subscribe" },
  { value: "INSTALL", label: "Install" },
];

// ---------------------------------------------------------------------------
// Variant card
// ---------------------------------------------------------------------------

function VariantCard({ variant, index }: { variant: CreativeVariant; index: number }) {
  const routingLabels: Record<string, string> = {
    deeplink_with_web_fallback: "App + Web Fallback",
    app_only: "App Only",
    web_only: "Web Only",
  };

  const routingColors: Record<string, string> = {
    deeplink_with_web_fallback: "bg-brand-blue/10 text-brand-blue border-brand-blue/20",
    app_only: "bg-brand-purple/10 text-brand-purple border-brand-purple/20",
    web_only: "bg-brand-green/10 text-brand-green border-brand-green/20",
  };

  const cs = variant.creative_spec as Record<string, unknown>;
  const spec = cs?.object_story_spec as Record<string, unknown> | undefined;
  const linkData = spec?.link_data as Record<string, unknown> | undefined;
  const ols = variant.omnichannel_link_spec as Record<string, unknown>;
  const app = ols?.app as Record<string, unknown> | undefined;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
    >
      <Card className="hover:border-brand-blue/30 transition-all group">
        <CardContent className="p-5">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h4 className="text-sm font-semibold text-text-primary">{variant.name}</h4>
              <div className="flex items-center gap-2 mt-1">
                <Badge
                  variant="outline"
                  className={cn("text-[10px]", routingColors[variant.deep_link_routing] || "")}
                >
                  {routingLabels[variant.deep_link_routing] || variant.deep_link_routing}
                </Badge>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-text-muted">Expected CTR Lift</div>
              <div className="text-lg font-bold text-brand-green">
                +{variant.expected_ctr_lift.toFixed(1)}%
              </div>
            </div>
          </div>

          <Separator className="my-3" />

          {/* Creative spec summary */}
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <Globe size={12} className="text-brand-blue" />
              <span className="text-text-secondary">Web URL:</span>
              <span className="text-text-primary font-mono truncate">
                {String(linkData?.link || "—")}
              </span>
            </div>
            <div className="flex items-start gap-2">
              <Sparkles size={12} className="text-brand-orange mt-0.5" />
              <span className="text-text-secondary">Message:</span>
              <span className="text-text-primary">
                {String(linkData?.message || "—")}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Smartphone size={12} className="text-brand-purple" />
              <span className="text-text-secondary">App ID:</span>
              <span className="text-text-primary font-mono">
                {String(app?.application_id || "—")}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Monitor size={12} className="text-brand-green" />
              <span className="text-text-secondary">CTA:</span>
              <span className="text-text-primary">
                {String((linkData?.call_to_action as Record<string, unknown> | undefined)?.type || "—")}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Generation Form
// ---------------------------------------------------------------------------

function GenerationForm({
  campaigns,
  onGenerate,
  isGenerating,
}: {
  campaigns: CampaignRecord[];
  onGenerate: (data: Record<string, unknown>) => void;
  isGenerating: boolean;
}) {
  const sessionId = useSessionId();
  const [campaignId, setCampaignId] = useState(campaigns[0]?.adset_id || "");
  const [name, setName] = useState("");
  const [webUrl, setWebUrl] = useState("");
  const [message, setMessage] = useState("");
  const [event, setEvent] = useState("PURCHASE");
  const [callToAction, setCallToAction] = useState("LEARN_MORE");
  const [applicationId, setApplicationId] = useState("");
  const [pageId, setPageId] = useState("");
  const [pixelId, setPixelId] = useState("");
  const [androidDeeplink, setAndroidDeeplink] = useState("");
  const [iosDeeplink, setIosDeeplink] = useState("");
  const [catalogMode, setCatalogMode] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const selectedCampaign = campaigns.find((c) => c.adset_id === campaignId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs: string[] = [];
    if (!name.trim()) errs.push("Campaign name is required");
    if (!webUrl.trim()) errs.push("Website URL is required");
    if (!message.trim()) errs.push("Ad message is required");
    if (!applicationId.trim()) errs.push("Application ID is required");

    if (errs.length > 0) {
      setErrors(errs);
      return;
    }
    setErrors([]);

    onGenerate({
      session_id: sessionId,
      name: name.trim(),
      web_url: webUrl.trim(),
      application_id: applicationId.trim(),
      page_id: pageId.trim() || undefined,
      android_deeplink: androidDeeplink.trim() || undefined,
      ios_deeplink: iosDeeplink.trim() || undefined,
      event,
      catalog_mode: catalogMode,
      call_to_action: callToAction,
      message: message.trim(),
      pixel_id: pixelId.trim() || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Campaign picker row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1.5">Campaign (optional reference)</label>
          <div className="relative">
            <select
              value={campaignId}
              onChange={(e) => {
                setCampaignId(e.target.value);
                const c = campaigns.find((c) => c.adset_id === e.target.value);
                if (c) setName(c.name);
              }}
              className="appearance-none w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-sm text-text-primary outline-none focus:border-brand-blue/50 transition-all"
            >
              <option value="">— Select existing campaign —</option>
              {campaigns.map((c) => (
                <option key={c.adset_id} value={c.adset_id}>
                  {c.name} ({c.event})
                </option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1.5">Event Type</label>
          <div className="relative">
            <select
              value={event}
              onChange={(e) => setEvent(e.target.value)}
              className="appearance-none w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-sm text-text-primary outline-none focus:border-brand-blue/50 transition-all"
            >
              {EVENT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Name + URL */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1.5">Campaign Name *</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Spring Sale - Omnichannel"
            className="w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-sm text-text-primary placeholder-text-muted outline-none focus:border-brand-blue/50 transition-all"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1.5">Website URL *</label>
          <input
            type="url"
            value={webUrl}
            onChange={(e) => setWebUrl(e.target.value)}
            placeholder="https://example.com"
            className="w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-sm text-text-primary placeholder-text-muted outline-none focus:border-brand-blue/50 transition-all"
          />
        </div>
      </div>

      {/* Message */}
      <div>
        <label className="block text-xs font-medium text-text-muted mb-1.5">Ad Message *</label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Shop on web or open in app for a better experience."
          rows={3}
          className="w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-sm text-text-primary placeholder-text-muted outline-none focus:border-brand-blue/50 transition-all resize-none"
        />
      </div>

      {/* CTA + Page ID */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1.5">Call to Action</label>
          <div className="relative">
            <select
              value={callToAction}
              onChange={(e) => setCallToAction(e.target.value)}
              className="appearance-none w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-sm text-text-primary outline-none focus:border-brand-blue/50 transition-all"
            >
              {CTA_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
          </div>
        </div>
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1.5">Page ID</label>
          <input
            type="text"
            value={pageId}
            onChange={(e) => setPageId(e.target.value)}
            placeholder="Facebook Page ID"
            className="w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-sm text-text-primary placeholder-text-muted outline-none focus:border-brand-blue/50 transition-all"
          />
        </div>
      </div>

      {/* App + Pixel IDs */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1.5">Application ID *</label>
          <input
            type="text"
            value={applicationId}
            onChange={(e) => setApplicationId(e.target.value)}
            placeholder="Your App ID"
            className="w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-sm text-text-primary placeholder-text-muted outline-none focus:border-brand-blue/50 transition-all"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1.5">Pixel ID</label>
          <input
            type="text"
            value={pixelId}
            onChange={(e) => setPixelId(e.target.value)}
            placeholder="Meta Pixel ID"
            className="w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-sm text-text-primary placeholder-text-muted outline-none focus:border-brand-blue/50 transition-all"
          />
        </div>
      </div>

      {/* Deeplinks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1.5">Android Deeplink</label>
          <input
            type="text"
            value={androidDeeplink}
            onChange={(e) => setAndroidDeeplink(e.target.value)}
            placeholder="yourapp://product/123"
            className="w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-sm text-text-primary placeholder-text-muted outline-none focus:border-brand-blue/50 transition-all"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-text-muted mb-1.5">iOS Deeplink</label>
          <input
            type="text"
            value={iosDeeplink}
            onChange={(e) => setIosDeeplink(e.target.value)}
            placeholder="yourapp://product/123"
            className="w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-sm text-text-primary placeholder-text-muted outline-none focus:border-brand-blue/50 transition-all"
          />
        </div>
      </div>

      {/* Catalog mode toggle */}
      <label className="flex items-center gap-3 cursor-pointer">
        <div className="relative">
          <input
            type="checkbox"
            checked={catalogMode}
            onChange={(e) => setCatalogMode(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-10 h-5 rounded-full bg-surface-hover border border-surface-border/50 peer-checked:bg-brand-blue transition-colors" />
          <div className="absolute left-0.5 top-0.5 w-4 h-4 rounded-full bg-white peer-checked:translate-x-5 transition-transform" />
        </div>
        <div>
          <span className="text-sm font-medium text-text-primary">Advantage+ Catalog Mode</span>
          <p className="text-xs text-text-muted">Generate dynamic product-level creative with catalog templates</p>
        </div>
      </label>

      {/* Error messages */}
      <AnimatePresence>
        {errors.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="p-3 rounded-xl bg-red-500/5 border border-red-500/20"
          >
            {errors.map((err) => (
              <p key={err} className="text-xs text-red-400 flex items-center gap-1.5">
                <AlertCircle size={12} />
                {err}
              </p>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <Button type="submit" size="lg" disabled={isGenerating} className="w-full gap-2">
        {isGenerating ? (
          <>
            <RefreshCw size={16} className="animate-spin" />
            Generating Variants...
          </>
        ) : (
          <>
            <Zap size={16} />
            Generate Creative Variants
          </>
        )}
      </Button>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Main Creative Lab Page
// ---------------------------------------------------------------------------

export function CreativeLabPage() {
  const sessionId = useSessionId();
  const [campaigns, setCampaigns] = useState<CampaignRecord[]>([]);
  const [variants, setVariants] = useState<CreativeVariant[]>([]);
  const [history, setHistory] = useState<GenerationHistoryItem[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  // Fetch campaigns on mount
  useEffect(() => {
    fetch(`${API_BASE}/campaigns/ccco?session_id=${sessionId}`)
      .then((res) => (res.ok ? res.json() : []))
      .then(setCampaigns)
      .catch(() => {});
  }, []);

  const handleGenerate = async (formData: Record<string, unknown>) => {
    setIsGenerating(true);
    setError(null);
    setVariants([]);

    try {
      const res = await fetch(`${API_BASE}/creative/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          name: formData.name,
          web_url: formData.web_url,
          application_id: formData.application_id,
          page_id: formData.page_id || undefined,
          android_deeplink: formData.android_deeplink || undefined,
          ios_deeplink: formData.ios_deeplink || undefined,
          event: formData.event,
          catalog_mode: formData.catalog_mode,
        }),
      });

      if (res.ok) {
        const data: CreativeVariant[] = await res.json();
        setVariants(data);

        // Add to history
        const historyItem: GenerationHistoryItem = {
          id: `gen-${Date.now()}`,
          campaign_name: String(formData.name || ""),
          variants: data,
          timestamp: new Date().toISOString(),
        };
        setHistory((prev) => [historyItem, ...prev].slice(0, 10));
      } else {
        const err = await res.json().catch(() => ({ detail: "Generation failed" }));
        setError(err.detail || "Failed to generate creative variants");
      }
    } catch {
      setError("Unable to connect to backend. Start the server to generate creatives.");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">Creative Lab</h1>
            <p className="text-sm text-text-muted mt-1">Generate omnichannel creative variants, ad copy, and messages with AI</p>
          </div>
          <Button
            variant={showForm ? "outline" : "default"}
            size="lg"
            onClick={() => setShowForm(!showForm)}
            className="gap-2"
          >
            {showForm ? "Cancel" : <><Sparkles size={16} /> New Generation</>}
          </Button>
        </div>
      </motion.div>

      {/* Generation form */}
      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <Card className="border-brand-blue/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles size={16} className="text-brand-blue" />
                  Generate Creative Variants
                </CardTitle>
              </CardHeader>
              <CardContent>
                <GenerationForm
                  campaigns={campaigns}
                  onGenerate={handleGenerate}
                  isGenerating={isGenerating}
                />
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error state */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-4 rounded-xl bg-red-500/5 border border-red-500/20 text-sm text-red-400"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Generated variants */}
      {variants.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <CheckCircle2 size={18} className="text-brand-green" />
              Generated Variants
            </h2>
            <Badge variant="green">{variants.length} variants</Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {variants.map((variant, idx) => (
              <VariantCard key={variant.name} variant={variant} index={idx} />
            ))}
          </div>

          {/* Summary */}
          <Card className="mt-4 bg-gradient-to-br from-brand-green/5 to-brand-blue/5 border-brand-green/20">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-green/10 flex items-center justify-center">
                  <Zap size={20} className="text-brand-green" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text-primary">Estimated Impact</h3>
                  <p className="text-xs text-text-muted mt-0.5">
                    Using these creative variants with omnichannel deep links, you can expect an average{" "}
                    <span className="text-brand-green font-semibold">
                      +{variants.reduce((sum, v) => sum + v.expected_ctr_lift, 0) / variants.length}% CTR lift
                    </span>{" "}
                    compared to standard web-only ads.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Empty state */}
      {!showForm && variants.length === 0 && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            { label: "Omnichannel Creatives", desc: "Generate ad variants with web + app deep links for cross-channel campaigns" },
            { label: "Ad Copy", desc: "AI-powered headlines, primary text, and CTAs tailored to your audience" },
            { label: "Catalog Dynamic", desc: "Product-level dynamic creatives with Advantage+ catalog templates" },
            { label: "A/B Test Variants", desc: "Generate multiple creative variations to test CTR and conversion performance" },
            { label: "Deep Link Routing", desc: "Configure web fallback, app-only, or deeplink-with-fallback routing strategies" },
            { label: "Cross-Platform", desc: "Creatives optimized for Facebook, Instagram, Messenger, and Audience Network" },
          ].map((item) => (
            <Card key={item.label} className="hover:border-brand-blue/30 transition-all group">
              <CardContent className="p-5">
                <div className="w-10 h-10 rounded-xl bg-surface-hover flex items-center justify-center group-hover:bg-brand-blue/10 transition-colors mb-3">
                  <Palette size={20} className="text-text-muted group-hover:text-brand-blue transition-colors" />
                </div>
                <h3 className="text-sm font-semibold text-text-primary">{item.label}</h3>
                <p className="text-xs text-text-muted mt-1">{item.desc}</p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-3 text-brand-blue"
                  onClick={() => setShowForm(true)}
                >
                  Generate <ExternalLink size={12} className="ml-1" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Generation history */}
      {history.length > 0 && (
        <div>
          <Separator className="my-6" />
          <h2 className="text-lg font-semibold text-text-primary mb-4">Generation History</h2>
          <div className="space-y-2">
            {history.map((item) => (
              <Card key={item.id} className="hover:border-surface-border transition-all cursor-pointer">
                <CardContent className="p-4 flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-medium text-text-primary">{item.campaign_name}</h4>
                    <p className="text-xs text-text-muted mt-0.5">
                      {item.variants.length} variants · {new Date(item.timestamp).toLocaleDateString()} ·{" "}
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                  <Badge variant="green" className="text-[10px]">
                    Avg lift +{item.variants.reduce((s, v) => s + v.expected_ctr_lift, 0) / item.variants.length}%
                  </Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
