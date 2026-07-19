import { useState, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { CommandPalette } from "@/components/ai/CommandPalette";
import { FloatingAI } from "@/components/ai/FloatingAI";
import { cn } from "@/lib/utils";

export function Shell() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [aiOpen, setAiOpen] = useState(false);

  // Command palette keyboard shortcut (Ctrl+K / Cmd+K)
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <div className="min-h-screen">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((prev) => !prev)}
      />

      <div
        className={cn(
          "transition-all duration-300",
          sidebarCollapsed ? "ml-[--sidebar-collapsed-width]" : "ml-[--sidebar-width]"
        )}
      >
        <TopBar onSearchClick={() => setCommandOpen(true)} />

        <main className="min-h-[calc(100vh-var(--topbar-height))] p-6">
          <Outlet />
        </main>
      </div>

      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
      <FloatingAI open={aiOpen} onToggle={() => setAiOpen((prev) => !prev)} />
    </div>
  );
}
