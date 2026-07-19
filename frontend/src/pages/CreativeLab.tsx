import { Palette } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function CreativeLabPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Creative Lab</h1>
        <p className="text-sm text-text-muted mt-1">Generate images, video, copy, and voiceovers with AI</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {["Images", "Videos", "Copy", "Voiceovers", "Carousels", "CTAs"].map((item) => (
          <Card key={item} className="hover:border-brand-blue/30 transition-all cursor-pointer group">
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-3">
                <div className="w-10 h-10 rounded-xl bg-surface-hover flex items-center justify-center group-hover:bg-brand-blue/10 transition-colors">
                  <Palette size={20} className="text-text-muted group-hover:text-brand-blue transition-colors" />
                </div>
                <Badge variant="outline" className="text-[10px]">Coming soon</Badge>
              </div>
              <h3 className="text-sm font-semibold text-text-primary">{item}</h3>
              <p className="text-xs text-text-muted mt-1">
                AI-powered {item.toLowerCase()} generation
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
