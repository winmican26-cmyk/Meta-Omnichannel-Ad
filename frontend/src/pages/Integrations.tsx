import { Puzzle, CheckCircle2, Circle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const integrations = [
  { name: "Meta", icon: "M", status: "connected" as const, color: "text-brand-blue" },
  { name: "Google Ads", icon: "G", status: "available" as const, color: "text-brand-green" },
  { name: "TikTok", icon: "T", status: "available" as const, color: "text-text-muted" },
  { name: "LinkedIn", icon: "in", status: "available" as const, color: "text-brand-blue" },
  { name: "Stripe", icon: "$", status: "connected" as const, color: "text-brand-purple" },
  { name: "Claude", icon: "C", status: "connected" as const, color: "text-brand-orange" },
  { name: "OpenAI", icon: "O", status: "connected" as const, color: "text-brand-green" },
];

export function IntegrationsPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Integrations</h1>
        <p className="text-sm text-text-muted mt-1">Connect your marketing channels and tools</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {integrations.map((item) => (
          <Card key={item.name} className="hover:border-surface-border transition-all">
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-surface-hover flex items-center justify-center text-sm font-bold">
                    <span className={item.color}>{item.icon}</span>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-text-primary">{item.name}</h3>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {item.status === "connected" ? (
                        <>
                          <CheckCircle2 size={12} className="text-brand-green" />
                          <span className="text-[11px] text-brand-green">Connected</span>
                        </>
                      ) : (
                        <>
                          <Circle size={12} className="text-text-muted" />
                          <span className="text-[11px] text-text-muted">Available</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <Button
                  variant={item.status === "connected" ? "outline" : "default"}
                  size="sm"
                >
                  {item.status === "connected" ? "Configure" : "Connect"}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
