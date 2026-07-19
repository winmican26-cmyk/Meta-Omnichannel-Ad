import { useState } from "react";
import { NavLink } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Megaphone,
  Bot,
  Palette,
  BarChart3,
  Puzzle,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
} from "lucide-react";

interface NavItemConfig {
  id: string;
  label: string;
  icon: React.ReactNode;
  path: string;
  badge?: number;
}

const navItems: NavItemConfig[] = [
  { id: "overview", label: "Overview", icon: <LayoutDashboard size={20} />, path: "/" },
  { id: "campaigns", label: "Campaigns", icon: <Megaphone size={20} />, path: "/campaigns" },
  { id: "ai-studio", label: "AI Studio", icon: <Bot size={20} />, path: "/ai-studio", badge: 2 },
  { id: "creative-lab", label: "Creative Lab", icon: <Palette size={20} />, path: "/creative-lab" },
  { id: "analytics", label: "Analytics", icon: <BarChart3 size={20} />, path: "/analytics" },
  { id: "integrations", label: "Integrations", icon: <Puzzle size={20} />, path: "/integrations" },
  { id: "settings", label: "Settings", icon: <Settings size={20} />, path: "/settings" },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen bg-surface-card border-r border-surface-border/50 flex flex-col transition-all duration-300",
        collapsed ? "w-[--sidebar-collapsed-width]" : "w-[--sidebar-width]"
      )}
    >
      {/* Logo */}
      <div className="flex items-center h-[--topbar-height] px-4 border-b border-surface-border/50">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-blue to-brand-purple flex items-center justify-center flex-shrink-0">
            <Sparkles size={16} className="text-white" />
          </div>
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "auto" }}
                exit={{ opacity: 0, width: 0 }}
                className="text-sm font-semibold text-text-primary whitespace-nowrap overflow-hidden"
              >
                Marketing OS
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-1 overflow-y-auto scrollbar-thin">
        {navItems.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group relative",
                isActive
                  ? "bg-brand-blue/10 text-brand-blue"
                  : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
              )
            }
          >
            {({ isActive }) => (
              <>
                <span className="flex-shrink-0">{item.icon}</span>
                <AnimatePresence mode="wait">
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex-1 truncate"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
                {item.badge && !collapsed && (
                  <span className="px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-brand-blue/20 text-brand-blue">
                    {item.badge}
                  </span>
                )}
                {isActive && (
                  <motion.div
                    layoutId="active-nav"
                    className="absolute inset-0 rounded-xl bg-brand-blue/10 -z-10"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="p-2 border-t border-surface-border/50">
        <button
          onClick={onToggle}
          className="flex items-center justify-center w-full py-2 px-3 rounded-xl text-text-muted hover:text-text-primary hover:bg-surface-hover transition-all duration-200"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </aside>
  );
}
