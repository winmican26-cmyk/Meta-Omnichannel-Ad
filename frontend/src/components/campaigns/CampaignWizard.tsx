import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ChevronLeft, ChevronRight, Rocket, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { WIZARD_STEPS, WIZARD_STEP_LABELS } from "@/types";
import type { WizardStep, CampaignDraft, ValidateStepResponse, DraftLaunchResponse } from "@/types";
import { useCampaignBuilder } from "@/hooks/useCampaignBuilder";
import { StepObjective } from "./StepObjective";
import { StepAudience } from "./StepAudience";
import { StepBudget } from "./StepBudget";
import { StepCreative } from "./StepCreative";
import { StepReview } from "./StepReview";

interface CampaignWizardProps {
  draft: CampaignDraft | null;
  onClose: () => void;
  onLaunched: (result: DraftLaunchResponse) => void;
}

export function CampaignWizard({ draft, onClose, onLaunched }: CampaignWizardProps) {
  const {
    activeDraft,
    currentStepIndex,
    loading,
    launching,
    error,
    createDraft,
    loadDraft,
    updateStep,
    validateStep,
    launchDraft,
    setActiveDraft,
  } = useCampaignBuilder();

  const [currentStep, setCurrentStep] = useState(0);
  const [stepData, setStepData] = useState<Record<string, unknown>>({});
  const [validation, setValidation] = useState<ValidateStepResponse | null>(null);
  const [saving, setSaving] = useState(false);
  const [launchResult, setLaunchResult] = useState<DraftLaunchResponse | null>(null);

  useEffect(() => {
    if (draft) {
      setActiveDraft(draft);
      setCurrentStep(Math.max(0, (draft.current_step || 1) - 1));
    } else {
      // Create a new draft
      createDraft().then((id) => {
        if (id) loadDraft(id);
      });
    }
  }, [draft?.id]);

  // Reset step data when step changes
  useEffect(() => {
    if (activeDraft?.step_data) {
      const stepName = WIZARD_STEPS[currentStep];
      const data = (activeDraft.step_data as Record<string, unknown>)[stepName] as Record<string, unknown> || {};
      setStepData(data);
      setValidation(null);
    }
  }, [currentStep, activeDraft]);

  const handleNext = useCallback(async () => {
    if (!activeDraft) return;
    const stepName = WIZARD_STEPS[currentStep];

    // Save the current step
    setSaving(true);
    await updateStep(activeDraft.id, stepName, stepData);
    setSaving(false);

    // Validate
    const result = await validateStep(activeDraft.id, stepName);
    setValidation(result);

    if (result?.valid) {
      // Check if this is a "review" step going to launch
      if (stepName === "review") {
        handleLaunch();
      } else {
        setCurrentStep((prev) => Math.min(prev + 1, WIZARD_STEPS.length - 1));
      }
    }
  }, [activeDraft, currentStep, stepData, updateStep, validateStep]);

  const handleBack = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  }, [currentStep]);

  const handleLaunch = useCallback(async () => {
    if (!activeDraft) return;
    const result = await launchDraft(activeDraft.id);
    if (result) {
      setLaunchResult(result);
      onLaunched(result);
    }
  }, [activeDraft, launchDraft, onLaunched]);

  const handleStepDataChange = useCallback((data: Record<string, unknown>) => {
    setStepData(data);
    setValidation(null);
  }, []);

  const stepName = WIZARD_STEPS[currentStep] as WizardStep;

  const renderStep = () => {
    switch (stepName) {
      case "objective":
        return <StepObjective data={stepData} onChange={handleStepDataChange} />;
      case "audience":
        return <StepAudience data={stepData} onChange={handleStepDataChange} />;
      case "budget":
        return <StepBudget data={stepData} onChange={handleStepDataChange} />;
      case "creative":
        return <StepCreative data={stepData} onChange={handleStepDataChange} />;
      case "review":
        return <StepReview draft={activeDraft} />;
      default:
        return null;
    }
  };

  const isLastStep = currentStep === WIZARD_STEPS.length - 1;
  const isFirstStep = currentStep === 0;

  // Success state
  if (launchResult?.success) {
    return (
      <Card className="max-w-2xl mx-auto">
        <CardContent className="p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-brand-green/20 flex items-center justify-center mx-auto mb-4">
            <Rocket size={32} className="text-brand-green" />
          </div>
          <h2 className="text-xl font-bold text-text-primary mb-2">Campaign Launched!</h2>
          <p className="text-text-muted mb-6">{launchResult.message}</p>
          {launchResult.adset_id && (
            <div className="text-left bg-surface-hover rounded-lg p-4 mb-6 font-mono text-sm text-text-secondary space-y-1">
              <p>Ad Set ID: {launchResult.adset_id}</p>
              {launchResult.creative_id && <p>Creative ID: {launchResult.creative_id}</p>}
              {launchResult.ad_id && <p>Ad ID: {launchResult.ad_id}</p>}
            </div>
          )}
          <Button onClick={onClose} variant="default" size="lg">
            Back to Campaigns
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-text-primary">New Campaign</h2>
        <button
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-surface-hover text-text-muted hover:text-text-primary transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      {/* Step Indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {WIZARD_STEPS.map((step, index) => {
            const isActive = index === currentStep;
            const isCompleted = index < currentStep;
            const stepLabel = WIZARD_STEP_LABELS[step as WizardStep];

            return (
              <div key={step} className="flex items-center flex-1 last:flex-none">
                <div className="flex flex-col items-center">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 ${
                      isActive
                        ? "bg-brand-blue text-white shadow-lg shadow-brand-blue/30 scale-110"
                        : isCompleted
                          ? "bg-brand-green text-white"
                          : "bg-surface-hover text-text-muted"
                    }`}
                  >
                    {isCompleted ? (
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      index + 1
                    )}
                  </div>
                  <span
                    className={`text-xs mt-1.5 font-medium ${
                      isActive ? "text-text-primary" : "text-text-muted"
                    }`}
                  >
                    {stepLabel}
                  </span>
                </div>
                {index < WIZARD_STEPS.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-3 rounded-full ${
                      isCompleted ? "bg-brand-green" : "bg-surface-border"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-2 p-3 mb-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          {renderStep()}
        </motion.div>
      </AnimatePresence>

      {/* Validation Errors */}
      {validation && !validation.valid && (
        <div className="flex items-start gap-2 p-3 mt-4 rounded-lg bg-brand-orange/10 border border-brand-orange/20 text-brand-orange text-sm">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <div>
            <p className="font-medium">Please complete all required fields:</p>
            <ul className="list-disc list-inside mt-1 text-text-secondary">
              {validation.missing_fields.map((f) => (
                <li key={f}>{f.replace(/_/g, " ")}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex items-center justify-between mt-8 pt-6 border-t border-surface-border">
        <Button
          variant="ghost"
          onClick={isFirstStep ? onClose : handleBack}
          className="gap-2"
        >
          <ChevronLeft size={16} />
          {isFirstStep ? "Cancel" : "Back"}
        </Button>

        <div className="flex items-center gap-3">
          <span className="text-xs text-text-muted">
            Step {currentStep + 1} of {WIZARD_STEPS.length}
          </span>
          <Button
            variant="default"
            onClick={handleNext}
            disabled={saving || loading || launching}
            className="gap-2"
          >
            {saving || loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Saving...
              </>
            ) : launching ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Launching...
              </>
            ) : isLastStep ? (
              <>
                <Rocket size={16} />
                Launch Campaign
              </>
            ) : (
              <>
                Next
                <ChevronRight size={16} />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
