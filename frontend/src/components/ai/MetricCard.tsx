import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn, formatPercentage } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import type { MetricCardData } from "@/types";

interface MetricCardProps {
  data: MetricCardData;
  variant?: "default" | "compact";
  delay?: number;
}

export function MetricCard({ data, variant = "default", delay = 0 }: MetricCardProps) {
  const TrendIcon = data.trend === "up" 
    ? TrendingUp 
    : data.trend === "down" 
      ? TrendingDown 
      : Minus;

  const trendColor = data.trend === "up" 
    ? "text-brand-green" 
    : data.trend === "down" 
      ? "text-brand-orange" 
      : "text-text-muted";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease: "easeOut" }}
    >
      <Card className={cn(variant === "compact" ? "p-3" : "")}>
        <CardContent className={cn(variant === "default" ? "p-5" : "p-0")}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-text-muted uppercase tracking-wider">
              {data.label}
            </span>
            {data.change !== undefined && (
              <div className={cn("flex items-center gap-1 text-xs font-medium", trendColor)}>
                <TrendIcon size={12} />
                <span>{formatPercentage(data.change)}</span>
              </div>
            )}
          </div>
          <div className={cn(
            "font-semibold text-text-primary",
            variant === "default" ? "text-2xl" : "text-lg"
          )}>
            {data.value}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
