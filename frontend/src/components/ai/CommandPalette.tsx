import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Sparkles,
  Rocket,
  TrendingUp,
  BarChart3,
  Palette,
  Target,
  Command,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface CommandItem {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  action: () => void;
  category: string;
}

const commands: CommandItem[] = [
  {
    id: "launch-campaign",
    label: "Launch a campaign for Sweden",
    description: "Create and deploy a new campaign targeting Sweden",
    icon: <Rocket size={16} />,
    action: () => {},
    category: "Campaigns",
  },
  {
    id: "worst-ad",
    label: "Show my worst-performing ad",
    description: "Find the ad with the lowest ROAS",
    icon: <TrendingUp size={16} />,
    action: () => {},
    category: "Analytics",
  },
  {
    id: "generate-creatives",
    label: "Generate 5 image variations",
    description: "Use AI to create new creative variants",
    icon: <Palette size={16} />,
    action: () => {},
    category: "Creative",
  },
  {
    id: "increase-budget",
    label: "Increase budget by 10%",
    description: "Scale up the campaign budget",
    icon: <BarChart3 size={16} />,
    action: () => {},
    category: "Campaigns",
  },
  {
    id: "optimize-roas",
    label: "How can I improve my ROAS?",
    description: "Get AI-powered optimization suggestions",
    icon: <Sparkles size={16} />,
    action: () => {},
    category: "AI Studio",
  },
  {
    id: "forecast",
    label: "Forecast tomorrow's performance",
    description: "Predict spend, CPA, and conversions",
    icon: <Target size={16} />,
    action: () => {},
    category: "Analytics",
  },
];

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = query
    ? commands.filter(
        (c) =>
          c.label.toLowerCase().includes(query.toLowerCase()) ||
          c.description.toLowerCase().includes(query.toLowerCase())
      )
    : commands;

  // Reset selection when results change
  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery("");
    }
  }, [open]);

  // Keyboard navigation
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filtered.length - 1));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      }
      if (e.key === "Enter" && filtered[selectedIndex]) {
        filtered[selectedIndex].action();
        onClose();
      }
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, filtered, selectedIndex, onClose]);

  // Group filtered results by category
  const grouped = filtered.reduce<Record<string, CommandItem[]>>((acc, cmd) => {
    if (!acc[cmd.category]) acc[cmd.category] = [];
    acc[cmd.category].push(cmd);
    return acc;
  }, {});

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            onClick={onClose}
          />

          {/* Palette */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -20 }}
            transition={{ type: "spring", stiffness: 400, damping: 35 }}
            className="fixed top-[15%] left-1/2 -translate-x-1/2 w-full max-w-xl z-50"
          >
            <div className="rounded-2xl bg-surface-card border border-surface-border/50 shadow-2xl overflow-hidden ai-glow">
              {/* Search input */}
              <div className="flex items-center gap-3 px-4 h-14 border-b border-surface-border/50">
                <Search size={18} className="text-text-muted flex-shrink-0" />
                <input
                  ref={inputRef}
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask anything or type a command..."
                  className="flex-1 bg-transparent text-text-primary placeholder-text-muted outline-none text-sm"
                />
                <kbd className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-surface-hover text-[10px] font-mono text-text-muted">
                  <Command size={10} />
                  K
                </kbd>
              </div>

              {/* Results */}
              <div className="max-h-80 overflow-y-auto scrollbar-thin p-2">
                {Object.entries(grouped).map(([category, items]) => (
                  <div key={category}>
                    <div className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                      {category}
                    </div>
                    {items.map((cmd, idx) => {
                      const globalIdx = commands.indexOf(cmd);
                      return (
                        <button
                          key={cmd.id}
                          className={cn(
                            "flex items-center gap-3 w-full px-3 py-2.5 rounded-xl text-left transition-all duration-150",
                            globalIdx === selectedIndex
                              ? "bg-brand-blue/10 text-brand-blue"
                              : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
                          )}
                          onClick={() => {
                            cmd.action();
                            onClose();
                          }}
                          onMouseEnter={() => setSelectedIndex(globalIdx)}
                        >
                          <span className="flex-shrink-0">{cmd.icon}</span>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate">
                              {cmd.label}
                            </div>
                            <div className="text-xs text-text-muted truncate">
                              {cmd.description}
                            </div>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                ))}
                {filtered.length === 0 && (
                  <div className="py-8 text-center text-sm text-text-muted">
                    No results found for "{query}"
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
