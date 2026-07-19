import { motion } from "framer-motion";
import {
  TrendingDown,
  Sparkles,
  Rocket,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { TimelineEvent } from "@/types";

const eventIcons: Record<TimelineEvent["type"], React.ReactNode> = {
  optimization: <TrendingDown size={14} />,
  creative: <Sparkles size={14} />,
  launch: <Rocket size={14} />,
  alert: <AlertTriangle size={14} />,
  approval: <CheckCircle2 size={14} />,
};

const eventColors: Record<TimelineEvent["type"], string> = {
  optimization: "text-brand-blue",
  creative: "text-brand-purple",
  launch: "text-brand-green",
  alert: "text-brand-orange",
  approval: "text-brand-green",
};

const eventBgColors: Record<TimelineEvent["type"], string> = {
  optimization: "bg-brand-blue/10",
  creative: "bg-brand-purple/10",
  launch: "bg-brand-green/10",
  alert: "bg-brand-orange/10",
  approval: "bg-brand-green/10",
};

interface TimelineProps {
  events: TimelineEvent[];
}

export function Timeline({ events }: TimelineProps) {
  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-[19px] top-2 bottom-2 w-[1px] bg-surface-border/50" />

      <div className="space-y-0">
        {events.map((event, idx) => (
          <motion.div
            key={event.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.08, duration: 0.3 }}
            className="relative flex items-start gap-4 pb-5 last:pb-0"
          >
            {/* Dot */}
            <div
              className={cn(
                "relative z-10 w-[38px] h-[38px] rounded-xl flex items-center justify-center flex-shrink-0",
                eventBgColors[event.type]
              )}
            >
              <span className={eventColors[event.type]}>{eventIcons[event.type]}</span>
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0 pt-1">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-xs text-text-muted font-mono">{event.time}</span>
                <span className="text-xs font-medium text-text-primary">{event.label}</span>
              </div>
              <p className="text-xs text-text-secondary">{event.description}</p>
              {event.impact && (
                <span className="inline-block mt-1 text-[11px] font-medium text-brand-green">
                  {event.impact}
                </span>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
