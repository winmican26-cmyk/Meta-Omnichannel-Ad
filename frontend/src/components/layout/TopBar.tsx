import { Search, Command, Bell, User, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TopBarProps {
  onSearchClick: () => void;
}

export function TopBar({ onSearchClick }: TopBarProps) {
  return (
    <header className="sticky top-0 z-30 h-[--topbar-height] bg-surface/80 backdrop-blur-xl border-b border-surface-border/50 flex items-center justify-between px-6">
      {/* Left: Search trigger */}
      <button
        onClick={onSearchClick}
        className="flex items-center gap-3 px-3 py-2 rounded-xl bg-surface-card border border-surface-border/50 text-text-muted text-sm w-72 hover:border-surface-border hover:text-text-secondary transition-all duration-200 group"
      >
        <Search size={16} className="flex-shrink-0" />
        <span className="flex-1 text-left">Search campaigns, AI, insights...</span>
        <kbd className="hidden sm:inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-surface-hover text-[10px] font-mono text-text-muted border border-surface-border/50">
          <Command size={10} />
          K
        </kbd>
      </button>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" className="relative">
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-brand-orange" />
        </Button>
        <Button variant="ghost" size="icon" className="rounded-full">
          <User size={18} />
        </Button>
      </div>
    </header>
  );
}
