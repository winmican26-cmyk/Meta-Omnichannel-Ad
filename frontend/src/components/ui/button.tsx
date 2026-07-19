import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-blue/50 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-brand-blue text-white hover:bg-brand-blue/90 shadow-lg shadow-brand-blue/20",
        destructive:
          "bg-red-500/10 text-red-400 hover:bg-red-500/20 border border-red-500/20",
        outline:
          "border border-surface-border bg-transparent hover:bg-surface-hover text-text-secondary hover:text-text-primary",
        secondary:
          "bg-surface-card text-text-primary hover:bg-surface-hover border border-surface-border",
        ghost:
          "text-text-secondary hover:text-text-primary hover:bg-surface-hover",
        link: "text-brand-blue underline-offset-4 hover:underline",
        green:
          "bg-brand-green/10 text-brand-green hover:bg-brand-green/20 border border-brand-green/20",
        purple:
          "bg-brand-purple/10 text-brand-purple hover:bg-brand-purple/20 border border-brand-purple/20",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 rounded-lg px-3 text-xs",
        lg: "h-12 rounded-xl px-6 text-base",
        xl: "h-14 rounded-2xl px-8 text-lg",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
