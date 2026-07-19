import { useState, useCallback } from "react";
import { API_BASE } from "@/lib/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  provider?: string;
  routingNote?: string;
  timestamp: string;
}

export interface ProviderInfo {
  name: string;
  label: string;
  status: "available" | "no_key" | "error" | "unavailable";
  description: string;
  capabilities: string[];
}

export interface KeyInfo {
  provider: string;
  label?: string;
  created_at?: string;
  updated_at?: string;
}

export function useAIChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hi, I'm the Marketing OS AI. I can help you optimize campaigns, generate creative, or answer marketing questions. I'll automatically route your question to the best AI model.\n\n**Claude** is best for strategy & analysis.\n**OpenAI** is best for creative generation.\n**Gemma 4** (local) handles offline orchestration & workflow automation.\n\nWhat would you like help with?",
      provider: "system",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [keys, setKeys] = useState<KeyInfo[]>([]);

  const fetchProviders = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/ai/providers`);
      if (res.ok) {
        setProviders(await res.json());
      }
    } catch {
      // Backend not available — providers will be shown as unknown
    }
  }, []);

  const fetchKeys = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/ai/keys`);
      if (res.ok) {
        setKeys(await res.json());
      }
    } catch {
      // Backend not available
    }
  }, []);

  const sendMessage = useCallback(
    async (content: string, preferredProvider?: string) => {
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      try {
        const res = await fetch(`${API_BASE}/ai/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: content,
            provider: preferredProvider || null,
          }),
        });

        if (!res.ok) {
          const errorData = await res.json().catch(() => ({}));
          const aiMsg: ChatMessage = {
            id: `ai-${Date.now()}`,
            role: "assistant",
            content: `Error: ${errorData.detail || res.statusText}`,
            provider: "error",
            timestamp: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, aiMsg]);
          return;
        }

        const data = await res.json();
        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: "assistant",
          content: data.response,
          provider: data.provider_used,
          routingNote: data.routing_note,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
      } catch {
        // Offline fallback — use local fallback responses
        const response = getFallbackResponse(content);
        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: "assistant",
          content: response,
          provider: "offline",
          routingNote: "offline mode (backend unreachable)",
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, aiMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const saveKey = useCallback(async (provider: string, key: string) => {
    const res = await fetch(`${API_BASE}/ai/keys`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, key }),
    });
    if (res.ok) {
      await fetchKeys();
      await fetchProviders();
    }
    return res.json();
  }, [fetchKeys, fetchProviders]);

  const deleteKey = useCallback(async (provider: string) => {
    const res = await fetch(`${API_BASE}/ai/keys/${provider}`, {
      method: "DELETE",
    });
    if (res.ok) {
      await fetchKeys();
      await fetchProviders();
    }
    return res.json();
  }, [fetchKeys, fetchProviders]);

  return {
    messages,
    setMessages,
    isLoading,
    providers,
    keys,
    fetchProviders,
    fetchKeys,
    sendMessage,
    saveKey,
    deleteKey,
  };
}

function getFallbackResponse(message: string): string {
  const q = message.toLowerCase();
  if (q.includes("roas"))
    return "To improve ROAS: 1) Refine audience targeting 2) Test new creative variants 3) Adjust bidding strategy 4) Audit placements.\n\nConnect Claude in Settings for a detailed AI analysis.";
  if (q.includes("cpa"))
    return "To lower CPA: 1) Remove low-converting audience segments 2) Refresh fatigued creatives 3) Optimize landing pages 4) Lower bids on expensive placements.";
  if (q.includes("budget"))
    return "Budget tips: 1) Shift from low to high-ROAS campaigns 2) Use dayparting 3) Increase max 20%/day.\n\nConnect an AI provider in Settings for automated recommendations.";
  if (q.includes("headline") || q.includes("copy"))
    return 'Here are 3 ad copy options:\n\n1. "Don\'t Just Sell. Scale."\n2. "Your Next Best Customer Is Waiting."\n3. "Results You Can Measure. Growth You Can Trust."\n\nConnect OpenAI in Settings for AI-generated copy.';
  if (q.includes("creative") || q.includes("ad"))
    return "Creative best practices:\n1) Test 3-5 variants per campaign\n2) Bold visuals + clear CTAs\n3) Refresh every 2-3 weeks\n4) Match format to platform";
  if (q.includes("hello") || q.includes("hi") || q.includes("hey"))
    return "Hello! I'm Marketing OS AI. Ask me about campaign optimization, creative generation, or analytics. What can I help with?";
  return "I'm in offline mode. For AI-powered analysis and creative generation, configure API keys in **Settings > Integrations > AI Providers**.";
}
