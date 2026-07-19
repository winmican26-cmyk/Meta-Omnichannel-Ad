import { motion } from "framer-motion";
import { GripVertical } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";

interface WorkflowNodeProps {
  label: string;
  icon?: React.ReactNode;
  variant?: "default" | "ai" | "success" | "warning";
  connected?: boolean;
  isFirst?: boolean;
  isLast?: boolean;
}

export function WorkflowNode({
  label,
  icon,
  variant = "default",
  connected = true,
  isFirst = false,
  isLast = false,
}: WorkflowNodeProps) {
  const variantStyles = {
    default: "border-surface-border bg-surface-card",
    ai: "border-brand-blue/30 bg-brand-blue/5",
    success: "border-brand-green/30 bg-brand-green/5",
    warning: "border-brand-orange/30 bg-brand-orange/5",
  };

  return (
    <div className="flex items-center gap-3 group">
      {/* Connector line */}
      {!isFirst && (
        <div className="w-8 h-[1px] bg-surface-border/50 flex-shrink-0" />
      )}

      <motion.div
        whileHover={{ scale: 1.02 }}
        className={cn(
          "flex items-center gap-2 px-3 py-2 rounded-xl border text-sm font-medium transition-all duration-200 cursor-pointer",
          variantStyles[variant],
          "hover:shadow-lg"
        )}
      >
        <GripVertical size={14} className="text-text-muted opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
        {icon && <span className="flex-shrink-0">{icon}</span>}
        <span className="text-text-primary">{label}</span>
      </motion.div>

      {/* Connector line */}
      {!isLast && (
        <div className="w-8 h-[1px] bg-surface-border/50 flex-shrink-0" />
      )}
    </div>
  );
}
