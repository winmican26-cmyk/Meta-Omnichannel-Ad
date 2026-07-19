import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Settings,
  User,
  Bell,
  Shield,
  CreditCard,
  Bot,
  Key,
  Eye,
  EyeOff,
  CheckCircle2,
  XCircle,
  Trash2,
  Sparkles,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { useAIChat, type ProviderInfo, type KeyInfo } from "@/hooks/useAIChat";

const sections = [
  { id: "profile", label: "Profile", icon: <User size={18} />, description: "Manage your account details" },
  { id: "notifications", label: "Notifications", icon: <Bell size={18} />, description: "Configure alert preferences" },
  { id: "security", label: "Security", icon: <Shield size={18} />, description: "API keys and access controls" },
  { id: "billing", label: "Billing", icon: <CreditCard size={18} />, description: "Subscription and payment methods" },
];

function AIProviderSettings() {
  const { providers, keys, saveKey, deleteKey, fetchProviders, fetchKeys } = useAIChat();
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [keyInputs, setKeyInputs] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [messages, setMessages] = useState<Record<string, { type: "success" | "error"; text: string }>>({});

  useEffect(() => {
    fetchProviders();
    fetchKeys();
  }, [fetchProviders, fetchKeys]);

  const handleSave = async (provider: string) => {
    const key = keyInputs[provider];
    if (!key) return;
    setSaving((prev) => ({ ...prev, [provider]: true }));
    try {
      const result = await saveKey(provider, key);
      if (result.status === "saved") {
        setMessages((prev) => ({ ...prev, [provider]: { type: "success", text: result.message } }));
        setKeyInputs((prev) => ({ ...prev, [provider]: "" }));
      } else {
        setMessages((prev) => ({ ...prev, [provider]: { type: "error", text: result.detail || "Failed to save key" } }));
      }
    } catch {
      setMessages((prev) => ({ ...prev, [provider]: { type: "error", text: "Failed to connect to backend" } }));
    } finally {
      setSaving((prev) => ({ ...prev, [provider]: false }));
    }
  };

  const handleDelete = async (provider: string) => {
    await deleteKey(provider);
    setMessages((prev) => ({ ...prev, [provider]: { type: "success", text: "Key removed" } }));
  };

  const hasKey = (provider: string) => keys.some((k) => k.provider === provider);

  const providerLabels: Record<string, { label: string; description: string; icon: string }> = {
    claude: {
      label: "Claude (Anthropic)",
      description: "Strategic analysis, optimization, and recommendations",
      icon: "Claude",
    },
    openai: {
      label: "OpenAI (GPT-4o)",
      description: "Creative generation, ad copy, and quick answers",
      icon: "GPT",
    },
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <Bot size={18} className="text-brand-purple" />
        <h3 className="text-base font-semibold text-text-primary">AI Providers</h3>
      </div>

      <div className="space-y-3">
        {Object.entries(providerLabels).map(([id, info]) => (
          <Card key={id}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="w-10 h-10 rounded-xl bg-surface-hover flex items-center justify-center flex-shrink-0">
                    <Sparkles size={18} className="text-brand-purple" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-semibold text-text-primary">{info.label}</h4>
                      {hasKey(id) ? (
                        <Badge variant="green" className="text-[10px]">
                          <CheckCircle2 size={10} className="mr-0.5" /> Connected
                        </Badge>
                      ) : (
                        <Badge variant="orange" className="text-[10px]">
                          <XCircle size={10} className="mr-0.5" /> Not configured
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-text-muted mt-0.5">{info.description}</p>

                    {/* Key input */}
                    <div className="mt-3">
                      {hasKey(id) ? (
                        <div className="flex items-center gap-2">
                          <div className="flex-1 px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-xs text-text-muted font-mono">
                            ••••••••••••{keys.find((k) => k.provider === id)?.label ? ` (${keys.find((k) => k.provider === id)?.label})` : ""}
                          </div>
                          <Button variant="destructive" size="sm" onClick={() => handleDelete(id)}>
                            <Trash2 size={14} />
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <div className="flex-1 relative">
                            <input
                              type={showKeys[id] ? "text" : "password"}
                              value={keyInputs[id] || ""}
                              onChange={(e) => setKeyInputs((prev) => ({ ...prev, [id]: e.target.value }))}
                              placeholder={`Enter ${info.label} API key...`}
                              className="w-full px-3 py-2 rounded-lg bg-surface-hover border border-surface-border/50 text-xs text-text-primary placeholder-text-muted outline-none focus:border-brand-blue/50 transition-all pr-8"
                            />
                            <button
                              onClick={() => setShowKeys((prev) => ({ ...prev, [id]: !prev[id] }))}
                              className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                            >
                              {showKeys[id] ? <EyeOff size={14} /> : <Eye size={14} />}
                            </button>
                          </div>
                          <Button
                            variant="default"
                            size="sm"
                            onClick={() => handleSave(id)}
                            disabled={!keyInputs[id] || saving[id]}
                          >
                            {saving[id] ? "Saving..." : "Save"}
                          </Button>
                        </div>
                      )}
                    </div>

                    {/* Message */}
                    <AnimatePresence>
                      {messages[id] && (
                        <motion.div
                          initial={{ opacity: 0, y: -5 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -5 }}
                          className={cn(
                            "mt-2 text-xs px-3 py-1.5 rounded-lg",
                            messages[id].type === "success"
                              ? "bg-brand-green/10 text-brand-green"
                              : "bg-red-500/10 text-red-400"
                          )}
                        >
                          {messages[id].text}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick reference */}
      <Card className="bg-surface-hover/50">
        <CardContent className="p-4">
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Smart Routing Reference</h4>
          <div className="text-xs text-text-secondary space-y-1">
            <p><span className="text-brand-orange font-medium">Claude</span> — Strategy, analysis, optimization, forecasting, reasoning</p>
            <p><span className="text-brand-green font-medium">OpenAI</span> — Creative, copywriting, headlines, image generation, quick answers</p>
            <p className="text-text-muted mt-1">Messages are automatically routed to the best AI based on content. You can also force a provider from AI Studio.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export function SettingsPage() {
  const [showAISettings, setShowAISettings] = useState(false);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Settings</h1>
        <p className="text-sm text-text-muted mt-1">Manage your account and preferences</p>
      </div>

      {/* AI Providers (featured) */}
      <Card
        className="bg-gradient-to-br from-brand-purple/5 to-brand-blue/5 border-brand-purple/20 cursor-pointer hover:border-brand-purple/40 transition-all"
        onClick={() => setShowAISettings(!showAISettings)}
      >
        <CardContent className="p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-purple to-brand-blue flex items-center justify-center">
                <Bot size={24} className="text-white" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-text-primary">AI Providers</h3>
                <p className="text-sm text-text-muted">Configure Claude and OpenAI API keys for AI-powered features</p>
              </div>
            </div>
            <Badge variant="purple" className="text-xs">
              {showAISettings ? "Close" : "Configure"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      <AnimatePresence>
        {showAISettings && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <AIProviderSettings />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Other settings */}
      <Separator />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sections.map((section) => (
          <Card key={section.id} className="hover:border-surface-border transition-all cursor-pointer">
            <CardContent className="p-5 flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-surface-hover flex items-center justify-center">
                <span className="text-text-muted">{section.icon}</span>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text-primary">{section.label}</h3>
                <p className="text-xs text-text-muted mt-0.5">{section.description}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
