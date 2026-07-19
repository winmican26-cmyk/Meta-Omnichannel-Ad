import { motion } from "framer-motion";
import { Megaphone, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function CampaignsPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Campaigns</h1>
          <p className="text-sm text-text-muted mt-1">Manage your active and draft campaigns</p>
        </div>
        <Button className="gap-2">
          <Plus size={16} />
          New Campaign
        </Button>
      </div>

      <Card>
        <CardContent className="p-12">
          <div className="flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-2xl bg-surface-hover flex items-center justify-center mb-4">
              <Megaphone size={32} className="text-text-muted" />
            </div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">Campaign Builder coming soon</h3>
            <p className="text-sm text-text-muted max-w-md">
              The Campaign Builder wizard will let you launch campaigns without seeing Meta terminology.
              Objective → Audience → Budget → Creative → Review → Launch.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
