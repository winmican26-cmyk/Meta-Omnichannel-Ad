import { Settings, User, Bell, Shield, CreditCard } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const sections = [
  { id: "profile", label: "Profile", icon: <User size={18} />, description: "Manage your account details" },
  { id: "notifications", label: "Notifications", icon: <Bell size={18} />, description: "Configure alert preferences" },
  { id: "security", label: "Security", icon: <Shield size={18} />, description: "API keys and access controls" },
  { id: "billing", label: "Billing", icon: <CreditCard size={18} />, description: "Subscription and payment methods" },
];

export function SettingsPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Settings</h1>
        <p className="text-sm text-text-muted mt-1">Manage your account and preferences</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sections.map((section) => (
          <Card key={section.id} className="hover:border-surface-border transition-all cursor-pointer">
            <CardContent className="p-5 flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-surface-hover flex items-center justify-center">
                <span className="text-text-muted">{section.icon}</span>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text-primary">{section.label}</h3>
                <p className="text-xs text-text-muted mt-0.5">{section.description}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
