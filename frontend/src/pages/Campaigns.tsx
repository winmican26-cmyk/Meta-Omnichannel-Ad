import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Megaphone,
  Plus,
  FileEdit,
  Trash2,
  Clock,
  Target,
  Globe,
  DollarSign,
  Loader2,
  Rocket,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CampaignWizard } from "@/components/campaigns/CampaignWizard";
import { useCampaignBuilder } from "@/hooks/useCampaignBuilder";
import type { CampaignDraft, DraftLaunchResponse } from "@/types";
import { formatCurrency } from "@/lib/utils";
import { API_BASE } from "@/lib/api";
import { useSessionId } from "@/contexts/AuthContext";

interface CampaignRecord {
  id: number;
  adset_id: string;
  name: string;
  event: string;
  status: string;
  created_at: string;
}

export function CampaignsPage() {
  const sessionId = useSessionId();
  const {
    drafts,
    loading,
    error,
    loadDrafts,
    deleteDraft,
    setActiveDraft,
  } = useCampaignBuilder();

  const [campaigns, setCampaigns] = useState<CampaignRecord[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(false);
  const [showWizard, setShowWizard] = useState(false);
  const [editingDraft, setEditingDraft] = useState<CampaignDraft | null>(null);
  const [launchResult, setLaunchResult] = useState<DraftLaunchResponse | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null);

  // Load campaigns and drafts on mount
  useEffect(() => {
    loadDrafts();
    loadCampaigns();
  }, []);

  const loadCampaigns = useCallback(async () => {
    setCampaignsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/campaigns/ccco?session_id=${sessionId}`);
      if (res.ok) {
        const data: CampaignRecord[] = await res.json();
        setCampaigns(data);
      }
    } catch {
      // Silently fail — campaigns may not be available
    } finally {
      setCampaignsLoading(false);
    }
  }, []);

  const handleNewCampaign = useCallback(() => {
    setEditingDraft(null);
    setLaunchResult(null);
    setShowWizard(true);
  }, []);

  const handleEditDraft = useCallback((draft: CampaignDraft) => {
    setEditingDraft(draft);
    setLaunchResult(null);
    setShowWizard(true);
  }, []);

  const handleWizardClose = useCallback(() => {
    setShowWizard(false);
    setEditingDraft(null);
  }, []);

  const handleLaunched = useCallback((result: DraftLaunchResponse) => {
    setLaunchResult(result);
    loadCampaigns();
    loadDrafts();
  }, [loadCampaigns, loadDrafts]);

  const handleDeleteDraft = useCallback(async (draftId: number) => {
    await deleteDraft(draftId);
    setDeleteConfirm(null);
  }, [deleteDraft]);

  const statusBadge = (status: string) => {
    const variants: Record<string, "blue" | "green" | "orange" | "default"> = {
      ACTIVE: "green",
      PAUSED: "orange",
      DRAFT: "blue",
    };
    return (
      <Badge variant={variants[status] || "default"}>{status}</Badge>
    );
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Campaigns</h1>
          <p className="text-sm text-text-muted mt-1">Manage your active and draft campaigns</p>
        </div>
        <Button onClick={handleNewCampaign} className="gap-2">
          <Plus size={16} />
          New Campaign
        </Button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Launch Success */}
      {launchResult && launchResult.success && (
        <Card className="border-brand-green/30">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-brand-green/20 flex items-center justify-center shrink-0">
              <Rocket size={20} className="text-brand-green" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-brand-green">{launchResult.message}</p>
              {launchResult.adset_id && (
                <p className="text-xs text-text-muted mt-0.5 font-mono truncate">
                  Ad Set: {launchResult.adset_id}
                </p>
              )}
            </div>
            <button
              onClick={() => setLaunchResult(null)}
              className="text-xs text-text-muted hover:text-text-primary"
            >
              Dismiss
            </button>
          </CardContent>
        </Card>
      )}

      {/* Active Campaigns */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Megaphone size={16} className="text-brand-blue" />
            Active Campaigns
          </CardTitle>
        </CardHeader>
        <CardContent>
          {campaignsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 size={20} className="animate-spin text-text-muted" />
            </div>
          ) : campaigns.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="w-12 h-12 rounded-2xl bg-surface-hover flex items-center justify-center mb-3">
                <Megaphone size={24} className="text-text-muted" />
              </div>
              <p className="text-sm text-text-muted">No campaigns yet</p>
              <p className="text-xs text-text-muted mt-1">
                Click "New Campaign" to create your first campaign
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {campaigns.map((campaign) => (
                <div
                  key={campaign.id}
                  className="flex items-center justify-between p-3 rounded-lg bg-surface-hover/50 hover:bg-surface-hover transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-text-primary truncate">
                      {campaign.name}
                    </p>
                    <p className="text-xs text-text-muted mt-0.5">
                      {campaign.event} &middot; {campaign.adset_id && `ID: ${campaign.adset_id.slice(0, 12)}...`}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs text-text-muted">
                      {new Date(campaign.created_at).toLocaleDateString()}
                    </span>
                    {statusBadge(campaign.status)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Draft Campaigns */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileEdit size={16} className="text-brand-purple" />
            Draft Campaigns
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 size={20} className="animate-spin text-text-muted" />
            </div>
          ) : drafts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <div className="w-12 h-12 rounded-2xl bg-surface-hover flex items-center justify-center mb-3">
                <FileEdit size={24} className="text-text-muted" />
              </div>
              <p className="text-sm text-text-muted">No drafts in progress</p>
              <p className="text-xs text-text-muted mt-1">
                Start a new campaign to create a draft
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {drafts.map((draft) => {
                const stepData = draft.step_data as Record<string, any>;
                const objective = stepData?.objective || {};
                const creative = stepData?.creative || {};
                const budget = stepData?.budget || {};

                return (
                  <div
                    key={draft.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-surface-hover/50 hover:bg-surface-hover transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {creative?.campaign_name || objective?.label || `Draft #${draft.id}`}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        {objective?.label && (
                          <span className="flex items-center gap-1 text-xs text-text-muted">
                            <Target size={10} />
                            {objective.label}
                          </span>
                        )}
                        {budget?.daily_budget_cents && (
                          <span className="flex items-center gap-1 text-xs text-text-muted">
                            <DollarSign size={10} />
                            {formatCurrency(budget.daily_budget_cents / 100)}/day
                          </span>
                        )}
                        <span className="flex items-center gap-1 text-xs text-text-muted">
                          <Clock size={10} />
                          Step {draft.current_step}/5
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {draft.is_complete ? (
                        <Badge variant="green">Complete</Badge>
                      ) : (
                        <Badge variant="blue">In Progress</Badge>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEditDraft(draft)}
                      >
                        Continue
                      </Button>
                      {deleteConfirm === draft.id ? (
                        <div className="flex items-center gap-1">
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleDeleteDraft(draft.id)}
                          >
                            Confirm
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setDeleteConfirm(null)}
                          >
                            Cancel
                          </Button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirm(draft.id)}
                          className="p-1.5 rounded-lg hover:bg-surface-hover text-text-muted hover:text-red-400 transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Campaign Wizard Modal */}
      <AnimatePresence>
        {showWizard && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-start justify-center pt-12 pb-8 px-4 overflow-y-auto"
          >
            {/* Backdrop */}
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={handleWizardClose}
            />

            {/* Wizard Panel */}
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.98 }}
              transition={{ duration: 0.2 }}
              className="relative w-full max-w-3xl bg-surface-card border border-surface-border rounded-2xl p-6 shadow-2xl"
            >
              <CampaignWizard
                draft={editingDraft}
                onClose={handleWizardClose}
                onLaunched={handleLaunched}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
