import { useState, useEffect, useCallback } from "react";
import { Globe, Search, X } from "lucide-react";

// Common countries for targeting
const AVAILABLE_COUNTRIES = [
  { code: "US", name: "United States" },
  { code: "CA", name: "Canada" },
  { code: "GB", name: "United Kingdom" },
  { code: "AU", name: "Australia" },
  { code: "DE", name: "Germany" },
  { code: "FR", name: "France" },
  { code: "IT", name: "Italy" },
  { code: "ES", name: "Spain" },
  { code: "NL", name: "Netherlands" },
  { code: "BR", name: "Brazil" },
  { code: "MX", name: "Mexico" },
  { code: "JP", name: "Japan" },
  { code: "KR", name: "South Korea" },
  { code: "IN", name: "India" },
  { code: "SE", name: "Sweden" },
  { code: "NO", name: "Norway" },
  { code: "DK", name: "Denmark" },
  { code: "FI", name: "Finland" },
  { code: "CH", name: "Switzerland" },
  { code: "SG", name: "Singapore" },
  { code: "NZ", name: "New Zealand" },
  { code: "AE", name: "UAE" },
  { code: "ZA", name: "South Africa" },
  { code: "AR", name: "Argentina" },
  { code: "CO", name: "Colombia" },
  { code: "CL", name: "Chile" },
  { code: "IE", name: "Ireland" },
  { code: "PT", name: "Portugal" },
  { code: "BE", name: "Belgium" },
  { code: "AT", name: "Austria" },
];

interface StepAudienceProps {
  data: Record<string, unknown>;
  onChange: (data: Record<string, unknown>) => void;
}

export function StepAudience({ data, onChange }: StepAudienceProps) {
  const [search, setSearch] = useState("");
  const selectedCountries: string[] = (data?.countries as string[]) || ["US"];
  const selectedNames: string[] = (data?.country_names as string[]) || ["United States"];

  const toggleCountry = useCallback(
    (code: string, name: string) => {
      let newCodes: string[];
      let newNames: string[];

      if (selectedCountries.includes(code)) {
        newCodes = selectedCountries.filter((c) => c !== code);
        newNames = selectedNames.filter((n, i) => selectedCountries[i] !== code);
        // Ensure at least one country remains
        if (newCodes.length === 0) return;
      } else {
        newCodes = [...selectedCountries, code];
        newNames = [...selectedNames, name];
      }

      onChange({
        countries: newCodes,
        country_names: newNames,
      });
    },
    [selectedCountries, selectedNames, onChange],
  );

  const filtered = AVAILABLE_COUNTRIES.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.code.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-4">
      <div className="mb-2">
        <h3 className="text-lg font-semibold text-text-primary">Where is your audience?</h3>
        <p className="text-sm text-text-muted mt-1">
          Select the countries you want to target. You can target multiple countries.
        </p>
      </div>

      {/* Selected countries */}
      {selectedCountries.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selectedCountries.map((code, i) => {
            const name = selectedNames[i] || code;
            return (
              <span
                key={code}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-brand-blue/10 text-brand-blue text-sm font-medium"
              >
                <Globe size={14} />
                {name} ({code})
                <button
                  onClick={() => toggleCountry(code, name)}
                  className="ml-0.5 hover:bg-brand-blue/20 rounded-full p-0.5"
                  disabled={selectedCountries.length <= 1}
                >
                  <X size={14} />
                </button>
              </span>
            );
          })}
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search countries..."
          className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-surface-card border border-surface-border text-text-primary placeholder:text-text-muted/50 focus:outline-none focus:ring-2 focus:ring-brand-blue/30 focus:border-brand-blue/50 text-sm"
        />
      </div>

      {/* Country grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 max-h-64 overflow-y-auto scrollbar-thin pr-1">
        {filtered.map((country) => {
          const isSelected = selectedCountries.includes(country.code);
          return (
            <button
              key={country.code}
              onClick={() => toggleCountry(country.code, country.name)}
              className={`text-left px-3 py-2 rounded-lg border text-sm transition-all duration-200 ${
                isSelected
                  ? "border-brand-blue/50 bg-brand-blue/5 text-brand-blue"
                  : "border-surface-border bg-surface-card text-text-secondary hover:border-surface-elevated hover:text-text-primary"
              }`}
            >
              <span className="font-medium">{country.name}</span>
              <span className="text-xs opacity-60 ml-1">({country.code})</span>
            </button>
          );
        })}
        {filtered.length === 0 && (
          <p className="col-span-full text-center text-sm text-text-muted py-8">
            No countries match your search.
          </p>
        )}
      </div>

      <p className="text-xs text-text-muted">
        {selectedCountries.length} {selectedCountries.length === 1 ? "country" : "countries"} selected
      </p>
    </div>
  );
}
