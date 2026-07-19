import { useState, useCallback } from "react";
import type {
  WizardStep,
  CampaignDraft,
  DraftCreateResponse,
  DraftUpdateResponse,
  ValidateStepResponse,
  DraftLaunchResponse,
  StepData,
} from "@/types";
import { API_BASE } from "@/lib/api";
import { useSessionId } from "@/contexts/AuthContext";

interface UseCampaignBuilderReturn {
  drafts: CampaignDraft[];
  activeDraft: CampaignDraft | null;
  currentStepIndex: number;
  loading: boolean;
  launching: boolean;
  error: string | null;
  createDraft: () => Promise<number | null>;
  loadDrafts: () => Promise<void>;
  loadDraft: (draftId: number) => Promise<void>;
  updateStep: (draftId: number, step: WizardStep, data: Record<string, unknown>) => Promise<DraftUpdateResponse | null>;
  validateStep: (draftId: number, step: WizardStep) => Promise<ValidateStepResponse | null>;
  launchDraft: (draftId: number) => Promise<DraftLaunchResponse | null>;
  deleteDraft: (draftId: number) => Promise<boolean>;
  setActiveDraft: (draft: CampaignDraft | null) => void;
}

export function useCampaignBuilder(): UseCampaignBuilderReturn {
  const sessionId = useSessionId();
  const [drafts, setDrafts] = useState<CampaignDraft[]>([]);
  const [activeDraft, setActiveDraft] = useState<CampaignDraft | null>(null);
  const [loading, setLoading] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentStepIndex = activeDraft ? activeDraft.current_step - 1 : 0;

  const createDraft = useCallback(async (): Promise<number | null> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/campaigns/builder/draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to create draft");
      }
      const data: DraftCreateResponse = await res.json();
      // Reload drafts and set this one as active
      await loadDrafts();
      const draft = (await fetch(`${API_BASE}/campaigns/builder/draft/${data.draft_id}?session_id=${sessionId}`).then((r) => r.json())) as CampaignDraft;
      setActiveDraft(draft);
      return data.draft_id;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to create draft";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDrafts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/campaigns/builder/drafts?session_id=${sessionId}`);
      if (!res.ok) throw new Error("Failed to load drafts");
      const data: CampaignDraft[] = await res.json();
      setDrafts(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load drafts";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDraft = useCallback(async (draftId: number) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/campaigns/builder/draft/${draftId}?session_id=${sessionId}`);
      if (!res.ok) throw new Error("Draft not found");
      const data: CampaignDraft = await res.json();
      setActiveDraft(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to load draft";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const updateStep = useCallback(
    async (draftId: number, step: WizardStep, data: Record<string, unknown>): Promise<DraftUpdateResponse | null> => {
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/campaigns/builder/draft/${draftId}/step/${step}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            step_data: data,
          }),
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to update step");
        }
        const result: DraftUpdateResponse = await res.json();
        // Refresh draft
        await loadDraft(draftId);
        return result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to update step";
        setError(msg);
        return null;
      }
    },
    [loadDraft],
  );

  const validateStep = useCallback(
    async (draftId: number, step: WizardStep): Promise<ValidateStepResponse | null> => {
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/campaigns/builder/draft/${draftId}/validate?step=${step}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to validate step");
        }
        return await res.json();
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to validate step";
        setError(msg);
        return null;
      }
    },
    [],
  );

  const launchDraft = useCallback(
    async (draftId: number): Promise<DraftLaunchResponse | null> => {
      setLaunching(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/campaigns/builder/draft/${draftId}/launch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to launch campaign");
        }
        const result: DraftLaunchResponse = await res.json();
        // Refresh drafts
        await loadDrafts();
        setActiveDraft(null);
        return result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to launch campaign";
        setError(msg);
        return null;
      } finally {
        setLaunching(false);
      }
    },
    [loadDrafts],
  );

  const deleteDraft = useCallback(async (draftId: number): Promise<boolean> => {
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/campaigns/builder/draft/${draftId}?session_id=${sessionId}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete draft");
      await loadDrafts();
      if (activeDraft?.id === draftId) setActiveDraft(null);
      return true;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to delete draft";
      setError(msg);
      return false;
    }
  }, [loadDrafts, activeDraft]);

  return {
    drafts,
    activeDraft,
    currentStepIndex,
    loading,
    launching,
    error,
    createDraft,
    loadDrafts,
    loadDraft,
    updateStep,
    validateStep,
    launchDraft,
    deleteDraft,
    setActiveDraft,
  };
}
