import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Puzzle,
  CheckCircle2,
  Circle,
  ExternalLink,
  CreditCard,
  Bot,
  Coins,
  RefreshCw,
  AlertCircle,
  Lock,
  Unlock,
  Sparkles,
  Key,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api";
import { useSessionId } from "@/contexts/AuthContext";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ProviderInfo {
  name: string;
  label: string;
  status: "available" | "no_key" | "error" | "unavailable";
  description: string;
  capabilities: string[];
}

interface KeyStatus {
  provider: string;
  configured: boolean;
  label: string | null;
}

interface IntegrationCard {
  id: string;
  name: string;
  icon: string;
  color: string;
  category: "ad_platform" | "ai" | "billing";
  description: string;
}

// ── Integration definitions ───────────────────────────────────────────

const integrationCards: IntegrationCard[] = [
  { id: "meta", name: "Meta Ads", icon: "M", color: "text-brand-blue", category: "ad_platform", description: "Campaign management, audience sync, insight ingestion" },
  { id: "google", name: "Google Ads", icon: "G", color: "text-brand-green", category: "ad_platform", description: "Cross-platform budget coordination" },
  { id: "tiktok", name: "TikTok", icon: "T", color: "text-text-muted", category: "ad_platform", description: "TikTok campaign management" },
  { id: "linkedin", name: "LinkedIn", icon: "in", color: "text-brand-blue", category: "ad_platform", description: "B2B campaign orchestration" },
  { id: "stripe", name: "Stripe", icon: "$", color: "text-brand-purple", category: "billing", description: "Subscription billing and payment processing" },
  { id: "claude", name: "Claude (Anthropic)", icon: "C", color: "text-brand-orange", category: "ai", description: "Strategic analysis and optimization" },
  { id: "openai", name: "OpenAI (GPT-4o)", icon: "O", color: "text-brand-green", category: "ai", description: "Creative generation and ad copy" },
  { id: "gemma", name: "Gemma 4 (Local)", icon: "G4", color: "text-brand-purple", category: "ai", description: "Offline orchestration and workflow automation" },
];

// ── Sub-components ────────────────────────────────────────────────────

function MetaOAuthCard() {
  return (
    <Card className="border-brand-blue/20 bg-gradient-to-br from-brand-blue/5 to-transparent">
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-brand-blue/10 flex items-center justify-center">
              <span className="text-lg font-bold text-brand-blue">M</span>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary">Meta Ads Account</h3>
              <p className="text-xs text-text-muted mt-0.5">
                Connect your Meta Business account to manage campaigns, sync insights, and optimize performance
              </p>
            </div>
          </div>
          <a
            href={`${API_BASE}/auth/login`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-1.5 h-8 rounded-lg px-3 text-xs font-medium bg-brand-blue text-white hover:bg-brand-blue/90 shadow-lg shadow-brand-blue/20 transition-all"
          >
            <ExternalLink size={14} />
            Connect
          </a>
        </div>
        <div className="mt-4 p-3 rounded-xl bg-surface-hover/50 border border-surface-border/20">
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <Lock size={12} />
            <span>Your connection is secured with OAuth 2.0. Tokens are encrypted at rest.</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StripeBillingCard() {
  const sessionId = useSessionId();
  const [loading, setLoading] = useState(false);
  const [portalUrl, setPortalUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const openBillingPortal = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/billing/portal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          customer_id: "demo-customer-id", // FIXME: use real customer ID
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setPortalUrl(data.portal_url);
        window.open(data.portal_url, "_blank", "noopener");
      } else {
        const errData = await res.json().catch(() => ({}));
        setError(errData.detail || "Billing portal unavailable");
      }
    } catch {
      setError("Unable to connect to backend. Start the server to access billing.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="border-brand-purple/20 bg-gradient-to-br from-brand-purple/5 to-transparent">
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-brand-purple/10 flex items-center justify-center">
              <CreditCard size={22} className="text-brand-purple" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary">Subscription & Billing</h3>
              <p className="text-xs text-text-muted mt-0.5">
                Manage your plan, payment methods, and billing history via Stripe
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={openBillingPortal}
            disabled={loading}
            className="gap-1.5"
          >
            {loading ? (
              <RefreshCw size={14} className="animate-spin" />
            ) : (
              <ExternalLink size={14} />
            )}
            {loading ? "Opening..." : "Manage"}
          </Button>
        </div>
        <AnimatePresence>
          {error && (
            <motion.p
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              className="mt-3 text-xs text-red-400"
            >
              {error}
            </motion.p>
          )}
          {portalUrl && (
            <motion.p
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-3 text-xs text-brand-green"
            >
              Billing portal opened in new tab
            </motion.p>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}

function CreditBalanceCard() {
  const sessionId = useSessionId();
  const [balance, setBalance] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/credits/balance?session_id=${sessionId}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setBalance(data?.credits_balance ?? null))
      .catch(() => setBalance(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-brand-orange/10 flex items-center justify-center">
            <Coins size={22} className="text-brand-orange" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-text-primary">Credit Balance</h3>
            <p className="text-xs text-text-muted mt-0.5">Credits are used for AI operations and campaign actions</p>
          </div>
          <div className="text-right">
            {loading ? (
              <RefreshCw size={16} className="animate-spin text-text-muted" />
            ) : (
              <>
                <div className="text-2xl font-bold text-text-primary">
                  {balance !== null ? balance : "—"}
                </div>
                <div className="text-[10px] text-text-muted">credits</div>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function AIProviderStatus({ provider }: { provider: ProviderInfo }) {
  const [keyStatus, setKeyStatus] = useState<KeyStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/ai/keys/${provider.name}/status`)
      .then((res) => (res.ok ? res.json() : null))
      .then(setKeyStatus)
      .catch(() => setKeyStatus(null))
      .finally(() => setLoading(false));
  }, [provider.name]);

  const isAvailable =
    keyStatus?.configured ||
    provider.status === "available" ||
    provider.name === "gemma"; // Gemma is always available

  const statusColor = isAvailable
    ? "text-brand-green"
    : provider.name === "gemma"
      ? "text-brand-purple"
      : "text-text-muted";

  const statusLabel = isAvailable
    ? provider.name === "gemma"
      ? "Ready (Offline)"
      : "Connected"
    : "Not configured";

  return (
    <div className="flex items-center justify-between py-2.5">
      <div className="flex items-center gap-2">
        <div className={cn("w-2 h-2 rounded-full", isAvailable ? "bg-brand-green" : "bg-text-muted")} />
        <span className="text-sm text-text-primary">{provider.label}</span>
      </div>
      <div className="flex items-center gap-2">
        {loading ? (
          <RefreshCw size={12} className="animate-spin text-text-muted" />
        ) : (
          <span className={cn("text-xs font-medium", statusColor)}>{statusLabel}</span>
        )}
      </div>
    </div>
  );
}

function AIProvidersCard() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const res = await fetch(`${API_BASE}/ai/providers`);
        if (res.ok) setProviders(await res.json());
      } catch {
        // Backend unavailable — show defaults
      } finally {
        setLoading(false);
      }
    };
    fetchProviders();
  }, []);

  const displayProviders = providers.length > 0 ? providers : [
    { name: "claude", label: "Claude (Anthropic)", status: "no_key" as const, description: "", capabilities: [] },
    { name: "openai", label: "OpenAI (GPT-4o)", status: "no_key" as const, description: "", capabilities: [] },
    { name: "gemma", label: "Gemma 4 (Local)", status: "available" as const, description: "", capabilities: [] },
  ];

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-center gap-2 mb-4">
          <Bot size={18} className="text-brand-purple" />
          <h3 className="text-sm font-semibold text-text-primary">AI Providers</h3>
          {loading && <RefreshCw size={12} className="animate-spin text-text-muted ml-auto" />}
        </div>
        <div className="divide-y divide-surface-border/30">
          {displayProviders.map((p) => (
            <AIProviderStatus key={p.name} provider={p} />
          ))}
        </div>
        <div className="mt-4 pt-3 border-t border-surface-border/30">
          <a
            href="/settings"
            className="inline-flex items-center justify-center gap-1.5 w-full h-8 rounded-lg text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-surface-hover transition-all"
          >
            <Key size={12} />
            Manage API Keys in Settings
          </a>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Ad platform sub-card ──────────────────────────────────────────────

function AdPlatformCard({
  integration,
  isConnected,
}: {
  integration: IntegrationCard;
  isConnected: boolean;
}) {
  return (
    <Card key={integration.id} className="hover:border-surface-border transition-all group">
      <CardContent className="p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-surface-hover flex items-center justify-center text-sm font-bold group-hover:bg-brand-blue/10 transition-colors">
              <span className={cn(integration.color, "transition-colors")}>{integration.icon}</span>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary">{integration.name}</h3>
              <p className="text-xs text-text-muted mt-0.5">{integration.description}</p>
              <div className="flex items-center gap-1.5 mt-1">
                {isConnected ? (
                  <>
                    <CheckCircle2 size={12} className="text-brand-green" />
                    <span className="text-[11px] text-brand-green">Connected</span>
                  </>
                ) : (
                  <>
                    <Circle size={12} className="text-text-muted" />
                    <span className="text-[11px] text-text-muted">Available</span>
                  </>
                )}
              </div>
            </div>
          </div>
          <Button
            variant={isConnected ? "outline" : "ghost"}
            size="sm"
            disabled={!isConnected}
          >
            {isConnected ? "Configure" : "Coming soon"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Integrations Page
// ---------------------------------------------------------------------------

export function IntegrationsPage() {
  const sessionId = useSessionId();
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-text-primary">Integrations</h1>
        <p className="text-sm text-text-muted mt-1">Connect your marketing channels, AI providers, and billing</p>
      </motion.div>

      {/* Credit balance */}
      <CreditBalanceCard />

      {/* Featured: Meta OAuth + Stripe Billing */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MetaOAuthCard />
        <StripeBillingCard />
      </div>

      {/* AI Providers */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Sparkles size={18} className="text-brand-purple" />
          <h2 className="text-base font-semibold text-text-primary">AI Provider Status</h2>
        </div>
        <AIProvidersCard />
      </div>

      {/* Ad Platform Integrations */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Puzzle size={18} className="text-brand-blue" />
          <h2 className="text-base font-semibold text-text-primary">Ad Platforms</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {integrationCards
            .filter((i) => i.category === "ad_platform")
            .map((integration) => (
              <AdPlatformCard
                key={integration.id}
                integration={integration}
                isConnected={integration.id === "meta"}
              />
            ))}
        </div>
      </div>

      {/* Footer note */}
      <div className="p-4 rounded-xl bg-surface-hover/30 border border-surface-border/20 text-center">
        <div className="flex items-center justify-center gap-2 text-xs text-text-muted">
          <Lock size={12} />
          <span>All API keys and tokens are encrypted at rest using Fernet (AES-128).</span>
        </div>
      </div>
    </div>
  );
}
