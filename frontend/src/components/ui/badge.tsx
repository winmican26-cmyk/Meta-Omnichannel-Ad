import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-surface-hover text-text-secondary",
        blue: "bg-brand-blue/10 text-brand-blue",
        purple: "bg-brand-purple/10 text-brand-purple",
        green: "bg-brand-green/10 text-brand-green",
        orange: "bg-brand-orange/10 text-brand-orange",
        outline: "border border-surface-border text-text-muted",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
