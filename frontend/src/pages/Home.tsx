import { motion } from "framer-motion";
import {
  Sparkles,
  TrendingUp,
  DollarSign,
  Target,
  BrainCircuit,
  ChevronRight,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { MetricCard } from "@/components/ai/MetricCard";
import { RecommendationCard } from "@/components/ai/RecommendationCard";
import { Timeline } from "@/components/ai/Timeline";
import { formatCurrency, formatNumber } from "@/lib/utils";
import type { MetricCardData, AIRecommendation, TimelineEvent } from "@/types";

// ─── Sample data ────────────────────────────────────────────────────────

const metrics: MetricCardData[] = [
  {
    label: "Today's Spend",
    value: formatCurrency(1247),
    change: 12.3,
    trend: "up",
  },
  {
    label: "Today's ROAS",
    value: "3.8x",
    change: 24.5,
    trend: "up",
  },
  {
    label: "Predicted CPA",
    value: formatCurrency(4.61),
    change: -8.2,
    trend: "down",
  },
  {
    label: "AI Confidence",
    value: "92%",
    change: 3.1,
    trend: "up",
  },
];

const recommendations: AIRecommendation[] = [
  {
    id: "rec-1",
    title: "Increase Instagram budget 15%",
    description:
      "Instagram Stories are outperforming Feed by 34% on CPA. Shifting budget would capture additional conversions at a lower cost.",
    impact: 183,
    impactLabel: "Estimated savings",
    confidence: 96,
    expectedChange: "CPA ↓18%",
    action: "Adjust budget",
    source: "claude",
    timestamp: "2026-07-19T10:30:00Z",
  },
  {
    id: "rec-2",
    title: "Pause underperforming creative set",
    description:
      'Creative variant "Spring Sale v3" has 0.9% CTR vs. 2.4% average. Pausing would improve overall campaign efficiency.',
    impact: 94,
    impactLabel: "Potential savings",
    confidence: 88,
    expectedChange: "CTR ↑1.5%",
    action: "Pause creative",
    source: "rule-engine",
    timestamp: "2026-07-19T09:15:00Z",
  },
  {
    id: "rec-3",
    title: "Expand audience targeting - lookalike",
    description:
      "Current 1% lookalike is saturated (reach frequency 4.2). A 3% lookalike would reach 340K new users at similar CPA.",
    impact: 210,
    impactLabel: "Estimated uplift",
    confidence: 78,
    expectedChange: "Reach +45%",
    action: "Expand audience",
    source: "claude",
    timestamp: "2026-07-19T08:00:00Z",
  },
];

const timelineEvents: TimelineEvent[] = [
  {
    id: "evt-1",
    time: "Yesterday",
    label: "Claude lowered bid",
    type: "optimization",
    description: "Reduced bid by 8% on Instagram placements to improve CPA",
    impact: "CPA improved 12%",
  },
  {
    id: "evt-2",
    time: "2 days ago",
    label: "Creative regenerated",
    type: "creative",
    description: "Generated 3 new image variants for Spring Sale campaign",
    impact: "CTR +4%",
  },
  {
    id: "evt-3",
    time: "3 days ago",
    label: "Campaign launched",
    type: "launch",
    description: "Summer Collection campaign went live across Facebook & Instagram",
    impact: "ROAS +14%",
  },
  {
    id: "evt-4",
    time: "5 days ago",
    label: "Audience refreshed",
    type: "optimization",
    description: "Expanded lookalike audience from 1% to 3% after saturation detected",
    impact: "Reach +28%",
  },
];

export function HomePage() {
  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-2xl font-bold text-text-primary">
            Good morning, Mike
          </h1>
          <p className="text-sm text-text-muted mt-1">
            3 campaigns need attention. Claude has found{" "}
            <span className="text-brand-green font-semibold">2 optimizations</span>.
          </p>
        </div>
        <Button variant="default" size="lg" className="gap-2">
          <BrainCircuit size={18} />
          Review Suggestions
          <ChevronRight size={16} />
        </Button>
      </motion.div>

      {/* Metric cards row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {metrics.map((metric, idx) => (
          <MetricCard key={metric.label} data={metric} delay={idx * 0.08} />
        ))}
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Recommendations */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
              <Sparkles size={18} className="text-brand-purple" />
              Claude Recommendations
            </h2>
            <Badge variant="purple">Updated 10 min ago</Badge>
          </div>

          {recommendations.map((rec, idx) => (
            <RecommendationCard
              key={rec.id}
              recommendation={rec}
              delay={idx * 0.1}
            />
          ))}
        </div>

        {/* Right: Campaign Timeline */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
            <TrendingUp size={18} className="text-brand-blue" />
            Campaign Timeline
          </h2>

          <Card>
            <CardContent className="p-5">
              <Timeline events={timelineEvents} />
            </CardContent>
          </Card>

          {/* AI Context Panel */}
          <Card className="bg-gradient-to-br from-brand-purple/5 to-brand-blue/5 border-brand-blue/20">
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-brand-purple/10 flex items-center justify-center flex-shrink-0">
                  <BrainCircuit size={16} className="text-brand-purple" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-text-primary mb-1">
                    Claude's Insight
                  </h3>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    "I noticed Instagram is outperforming Facebook 3:1 on ROAS.
                    Consider shifting 15% of Facebook budget to Instagram for
                    the next 7 days."
                  </p>
                  <div className="flex items-center gap-3 mt-3">
                    <Badge variant="green" className="text-[10px]">
                      Expected CPA ↓12%
                    </Badge>
                    <Button variant="ghost" size="sm" className="text-xs">
                      Apply
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
