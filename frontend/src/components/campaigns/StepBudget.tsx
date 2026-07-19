import { useState, useEffect } from "react";
import { DollarSign, TrendingUp, ToggleLeft, ToggleRight } from "lucide-react";
import { formatCurrency } from "@/lib/utils";

interface StepBudgetProps {
  data: Record<string, unknown>;
  onChange: (data: Record<string, unknown>) => void;
}

export function StepBudget({ data, onChange }: StepBudgetProps) {
  const dailyBudgetCents = (data?.daily_budget_cents as number) || 5000;
  const bidAmountCents = (data?.bid_amount_cents as number | null) || null;
  const hasBidCap = (data?.has_bid_cap as boolean) || false;

  const handleBudgetChange = (value: number) => {
    onChange({
      daily_budget_cents: Math.max(100, value),
      bid_amount_cents: hasBidCap ? bidAmountCents : null,
      has_bid_cap: hasBidCap,
    });
  };

  const toggleBidCap = () => {
    const newHasBidCap = !hasBidCap;
    onChange({
      daily_budget_cents: dailyBudgetCents,
      bid_amount_cents: newHasBidCap ? (bidAmountCents || Math.round(dailyBudgetCents * 0.3)) : null,
      has_bid_cap: newHasBidCap,
    });
  };

  const handleBidChange = (value: number) => {
    onChange({
      daily_budget_cents: dailyBudgetCents,
      bid_amount_cents: value || null,
      has_bid_cap: hasBidCap,
    });
  };

  // Preset budgets (in cents / dollars)
  const presets = [
    { label: "Starter", cents: 500, dollars: 5 },
    { label: "Basic", cents: 1000, dollars: 10 },
    { label: "Standard", cents: 5000, dollars: 50 },
    { label: "Growth", cents: 25000, dollars: 250 },
    { label: "Scale", cents: 100000, dollars: 1000 },
  ];

  return (
    <div className="space-y-6">
      <div className="mb-2">
        <h3 className="text-lg font-semibold text-text-primary">Set your budget</h3>
        <p className="text-sm text-text-muted mt-1">
          Define your daily spending and optional bid controls.
        </p>
      </div>

      {/* Daily Budget */}
      <div className="space-y-3">
        <label className="flex items-center gap-2 text-sm font-medium text-text-primary">
          <DollarSign size={16} className="text-brand-green" />
          Daily Budget
        </label>

        {/* Preset chips */}
        <div className="flex flex-wrap gap-2">
          {presets.map((preset) => (
            <button
              key={preset.cents}
              onClick={() => handleBudgetChange(preset.cents)}
              className={`px-3 py-1.5 rounded-lg border text-sm font-medium transition-all ${
                dailyBudgetCents === preset.cents
                  ? "border-brand-blue bg-brand-blue/10 text-brand-blue"
                  : "border-surface-border text-text-secondary hover:border-surface-elevated hover:text-text-primary"
              }`}
            >
              ${preset.dollars}/day
            </button>
          ))}
        </div>

        {/* Custom input */}
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted font-medium">$</span>
          <input
            type="number"
            value={Math.round(dailyBudgetCents / 100)}
            onChange={(e) => handleBudgetChange(Math.max(1, parseInt(e.target.value) || 1) * 100)}
            min={1}
            className="w-full pl-8 pr-4 py-3 rounded-xl bg-surface-card border border-surface-border text-text-primary focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue/50 text-lg font-semibold"
          />
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">USD / day</span>
        </div>
      </div>

      {/* Advanced: Bid Cap */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm font-medium text-text-primary">
            <TrendingUp size={16} className="text-brand-purple" />
            Bid Cap (Advanced)
          </label>
          <button
            onClick={toggleBidCap}
            className={`flex items-center gap-2 text-sm transition-colors ${
              hasBidCap ? "text-brand-blue" : "text-text-muted"
            }`}
          >
            {hasBidCap ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
            {hasBidCap ? "Enabled" : "Disabled"}
          </button>
        </div>

        {hasBidCap && (
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted font-medium">$</span>
            <input
              type="number"
              value={bidAmountCents ? Math.round(bidAmountCents / 100) : ""}
               onChange={(e) => { const val = parseInt(e.target.value) * 100; handleBidChange(isNaN(val) ? 0 : val); }}
              placeholder="Enter max bid per result"
              min={1}
              className="w-full pl-8 pr-4 py-2.5 rounded-xl bg-surface-card border border-surface-border text-text-primary focus:outline-none focus:ring-2 focus:ring-brand-purple/30 focus:border-brand-purple/50 text-sm"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted text-xs">USD per result</span>
          </div>
        )}

        {hasBidCap && (
          <p className="text-xs text-text-muted">
            A bid cap sets the maximum you're willing to pay per result. Recommended when you want tighter cost control.
          </p>
        )}
      </div>

      {/* Summary */}
      <div className="p-4 rounded-xl bg-surface-hover border border-surface-border">
        <div className="flex items-center justify-between text-sm">
          <span className="text-text-muted">Estimated monthly spend</span>
          <span className="text-text-primary font-semibold">
            {formatCurrency((dailyBudgetCents / 100) * 30)}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm mt-2">
          <span className="text-text-muted">Daily budget</span>
          <span className="text-text-primary font-medium">{formatCurrency(dailyBudgetCents / 100)}</span>
        </div>
        {hasBidCap && bidAmountCents && (
          <div className="flex items-center justify-between text-sm mt-2">
            <span className="text-text-muted">Bid cap</span>
            <span className="text-text-primary font-medium">{formatCurrency(bidAmountCents / 100)}</span>
          </div>
        )}
      </div>
    </div>
  );
}
