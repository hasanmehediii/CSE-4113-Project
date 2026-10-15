"use client";
import { useCallback } from "react";
import { useApp } from "@/components/Providers";
import { civicDate, civicLabel, civicNumber, civicText } from "@/lib/civic-i18n";

export function useCivicLocale() {
  const { language } = useApp();
  const tr = useCallback((text: string) => civicText(text, language), [language]);
  const label = useCallback((value: string, fallback?: string) => civicLabel(value, language, fallback), [language]);
  const date = useCallback((value: number) => civicDate(value, language), [language]);
  const number = useCallback((value: number) => civicNumber(value, language), [language]);
  return { language, tr, label, date, number };
}
