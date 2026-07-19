import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Bot,
  Send,
  Sparkles,
  BrainCircuit,
  Lightbulb,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  PenLine,
  TrendingUp,
  DollarSign,
  Target,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { useAIChat, type ChatMessage, type ProviderInfo } from "@/hooks/useAIChat";

const suggestionChips = [
  { label: "Improve my ROAS", icon: <TrendingUp size={14} /> },
  { label: "Optimize my budget", icon: <DollarSign size={14} /> },
  { label: "Why is CPA rising?", icon: <Target size={14} /> },
  { label: "Generate ad headlines", icon: <PenLine size={14} /> },
  { label: "Creative best practices", icon: <Lightbulb size={14} /> },
];

function ProviderBadge({ provider, providers }: { provider?: string; providers: ProviderInfo[] }) {
  if (!provider || provider === "system" || provider === "offline" || provider === "error") {
    const colorMap: Record<string, string> = {
      system: "bg-brand-purple/10 text-brand-purple border-brand-purple/20",
      offline: "bg-surface-hover text-text-muted border-surface-border",
      error: "bg-red-500/10 text-red-400 border-red-500/20",
    };
    return (
      <span className={cn("text-[10px] px-1.5 py-0.5 rounded-full border font-medium", colorMap[provider || "system"] || "")}>
        {provider || "system"}
      </span>
    );
  }

  const info = providers.find((p) => p.name === provider);
  const colorMap: Record<string, string> = {
    claude: "bg-brand-orange/10 text-brand-orange border-brand-orange/20",
    openai: "bg-brand-green/10 text-brand-green border-brand-green/20",
  };

  return (
    <span className={cn("text-[10px] px-1.5 py-0.5 rounded-full border font-medium", colorMap[provider] || "bg-brand-blue/10 text-brand-blue border-brand-blue/20")}>
      {info?.label || provider}
    </span>
  );
}

export function AIStudioPage() {
  const {
    messages,
    isLoading,
    providers,
    sendMessage,
    fetchProviders,
  } = useAIChat();

  const [input, setInput] = useState("");
  const [showProviders, setShowProviders] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    sendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChipClick = (label: string) => {
    sendMessage(label);
  };

  const availableCount = providers.filter((p) => p.status === "available").length;
  const totalCount = providers.length;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">AI Studio</h1>
          <p className="text-sm text-text-muted mt-1">
            Ask Claude or OpenAI anything about your campaigns
          </p>
        </div>
        <button
          onClick={() => setShowProviders(!showProviders)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-card border border-surface-border/50 text-xs text-text-secondary hover:text-text-primary transition-all"
        >
          <Bot size={14} />
          {availableCount}/{totalCount} active
          {showProviders ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* Provider status panel */}
      <AnimatePresence>
        {showProviders && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <Card>
              <CardContent className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {providers.length === 0 && (
                    <div className="col-span-2 text-sm text-text-muted text-center py-2">
                      No providers detected. Start the backend server.
                    </div>
                  )}
                  {providers.map((p) => (
                    <div key={p.name} className="flex items-start gap-3 p-3 rounded-xl bg-surface-hover">
                      <div className="w-8 h-8 rounded-lg bg-surface-card flex items-center justify-center flex-shrink-0">
                        <Bot size={16} className={
                          p.status === "available" ? "text-brand-green"
                          : p.status === "no_key" ? "text-brand-orange"
                          : "text-text-muted"
                        } />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-semibold text-text-primary">{p.label}</span>
                          <Badge variant={
                            p.status === "available" ? "green"
                            : p.status === "no_key" ? "orange"
                            : "outline"
                          } className="text-[10px]">
                            {p.status === "available" ? "Ready"
                              : p.status === "no_key" ? "No Key"
                              : p.status}
                          </Badge>
                        </div>
                        <p className="text-xs text-text-muted mt-1">{p.description}</p>
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {p.capabilities.map((cap) => (
                            <span key={cap} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-card text-text-muted">
                              {cap.replace(/_/g, " ")}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Chat area */}
      <Card className="min-h-[400px] flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-4 max-h-[500px]">
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}
            >
              <div
                className={cn(
                  "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
                  msg.role === "user"
                    ? "bg-brand-blue text-white"
                    : "bg-surface-hover text-text-primary"
                )}
              >
                {msg.provider && msg.provider !== "user" && (
                  <div className="flex items-center gap-2 mb-2">
                    <ProviderBadge provider={msg.provider} providers={providers} />
                    {msg.routingNote && (
                      <span className="text-[10px] text-text-muted">{msg.routingNote}</span>
                    )}
                  </div>
                )}
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
            </motion.div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-surface-hover rounded-2xl px-4 py-3">
                <div className="flex gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-2 h-2 rounded-full bg-text-muted animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <Separator />

        {/* Input */}
        <div className="p-4">
          <div className="flex items-center gap-3 bg-surface-hover rounded-2xl px-4 py-3">
            <Bot size={20} className="text-brand-blue flex-shrink-0" />
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about campaigns, creative, or strategy..."
              className="flex-1 bg-transparent text-text-primary placeholder-text-muted outline-none text-sm"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="p-2 rounded-xl bg-brand-blue text-white hover:bg-brand-blue/90 disabled:opacity-40 transition-all flex-shrink-0"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </Card>

      {/* Suggestion chips */}
      <div className="flex flex-wrap gap-2">
        {suggestionChips.map((chip) => (
          <button
            key={chip.label}
            onClick={() => handleChipClick(chip.label)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-card border border-surface-border/50 text-xs text-text-secondary hover:text-text-primary hover:border-brand-blue/30 hover:bg-surface-hover transition-all"
          >
            {chip.icon}
            {chip.label}
          </button>
        ))}
      </div>
    </div>
  );
}
