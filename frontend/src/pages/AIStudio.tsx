import { motion } from "framer-motion";
import { Bot, Send, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const recentQuestions = [
  "How can I improve my ROAS?",
  "Optimize budget across campaigns",
  "Why is CPA rising this week?",
  "Duplicate my best performing campaign",
  "Generate new creative for Spring Sale",
];

export function AIStudioPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">AI Studio</h1>
        <p className="text-sm text-text-muted mt-1">Ask Claude anything about your campaigns</p>
      </div>

      {/* Chat input */}
      <Card className="ai-glow border-brand-blue/20">
        <CardContent className="p-6">
          <div className="flex items-center gap-3 bg-surface-hover rounded-2xl px-4 py-3">
            <Bot size={20} className="text-brand-blue flex-shrink-0" />
            <input
              type="text"
              placeholder="How can I improve my ROAS?"
              className="flex-1 bg-transparent text-text-primary placeholder-text-muted outline-none text-sm"
            />
            <button className="p-2 rounded-xl bg-brand-blue text-white hover:bg-brand-blue/90 transition-all">
              <Send size={16} />
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Recent questions */}
      <div>
        <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-3">
          Recent Questions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {recentQuestions.map((q, idx) => (
            <motion.button
              key={q}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              className="flex items-center gap-3 p-4 rounded-xl bg-surface-card border border-surface-border/50 hover:border-brand-blue/30 hover:bg-surface-hover transition-all duration-200 text-left group"
            >
              <Sparkles size={16} className="text-brand-purple flex-shrink-0" />
              <span className="text-sm text-text-secondary group-hover:text-text-primary transition-colors">
                {q}
              </span>
            </motion.button>
          ))}
        </div>
      </div>
    </div>
  );
}
