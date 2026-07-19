import { motion } from "framer-motion";
import { Sparkles, ThumbsUp, X, TrendingDown } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatCurrency } from "@/lib/utils";
import type { AIRecommendation } from "@/types";

interface RecommendationCardProps {
  recommendation: AIRecommendation;
  onApprove?: (id: string) => void;
  onDismiss?: (id: string) => void;
  delay?: number;
}

export function RecommendationCard({
  recommendation,
  onApprove,
  onDismiss,
  delay = 0,
}: RecommendationCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35, ease: "easeOut" }}
    >
      <Card className="group hover:border-brand-blue/30 transition-all duration-300">
        <CardContent className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1.5">
                <div className="w-6 h-6 rounded-lg bg-brand-purple/10 flex items-center justify-center flex-shrink-0">
                  <Sparkles size={12} className="text-brand-purple" />
                </div>
                <span className="text-sm font-semibold text-text-primary truncate">
                  {recommendation.title}
                </span>
                <Badge variant="purple" className="text-[10px]">
                  {recommendation.confidence}% confidence
                </Badge>
              </div>
              <p className="text-xs text-text-secondary mb-3 line-clamp-2">
                {recommendation.description}
              </p>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-text-muted">Impact</span>
                  <span className="text-sm font-semibold text-brand-green">
                    {formatCurrency(recommendation.impact)}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <TrendingDown size={14} className="text-brand-green" />
                  <span className="text-xs font-medium text-brand-green">
                    {recommendation.expectedChange}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <Button
                variant="green"
                size="sm"
                onClick={() => onApprove?.(recommendation.id)}
                className="opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <ThumbsUp size={14} className="mr-1" />
                Approve
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onDismiss?.(recommendation.id)}
                className="opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <X size={14} />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
