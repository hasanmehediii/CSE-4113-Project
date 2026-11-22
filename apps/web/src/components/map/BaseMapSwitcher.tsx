"use client";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import { BASE_MAP_CHOICES, type BaseMapChoice } from "@/lib/map-tiles";

const LABELS: Record<BaseMapChoice, string> = { auto: "Auto", streets: "Streets", light: "Light", dark: "Dark" };

export default function BaseMapSwitcher({ choice, onChange }: { choice: BaseMapChoice; onChange: (choice: BaseMapChoice) => void }) {
  const { tr } = useCivicLocale();
  return <div className="base-map-switcher" role="group" aria-label={tr("Map style")}>
    {BASE_MAP_CHOICES.map(value => <button key={value} type="button" aria-pressed={choice === value}
      title={value === "auto" ? tr("Follows the site's light or dark theme") : undefined}
      onClick={() => onChange(value)}>{tr(LABELS[value])}</button>)}
  </div>;
}
