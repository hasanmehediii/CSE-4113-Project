"use client";
import { useRef, type FormEvent } from "react";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import type { PredictionFailure, RoadForecast } from "@/lib/road-map";

interface Props {
  at: string; rain: string; horizon: number; hazard: "waterlogging" | "traffic";
  forecast: RoadForecast | null; error: PredictionFailure | null; predicting: boolean; stale: boolean;
  onAt: (value: string) => void; onRain: (value: string) => void;
  onHorizon: (value: number) => void; onHazard: (value: "waterlogging" | "traffic") => void;
  onPredict: (event: FormEvent) => void;
}

export default function RoadPredictionPanel(props: Props) {
  const { tr, number } = useCivicLocale();
  const form = useRef<HTMLFormElement>(null);
  return <section className="road-prediction-panel">
    <span className="road-demo-badge">{tr("SYNTHETIC MODEL · DEMO")}</span>
    <h3>{tr("Look ahead, plan your route")}</h3>
    <p>{tr("Explore rainwater and traffic risk. These are simulated scenarios, not a verified forecast.")}</p>
    <form ref={form} onSubmit={props.onPredict}>
      <label>{tr("Date & time · Asia/Dhaka (UTC+6)")}<input type="datetime-local" required value={props.at} onChange={event => props.onAt(event.target.value)} /></label>
      <label>{tr("Forecast horizon · minutes")}<select value={props.horizon} onChange={event => props.onHorizon(Number(event.target.value))}>
        {[30, 60, 120].map(value => <option key={value} value={value}>{number(value)}</option>)}
      </select></label>
      <label>{tr("Scenario rainfall · mm in one hour")}<input type="number" required min="0" max="150" step="0.1" aria-describedby="road-rain-help" value={props.rain} onChange={event => props.onRain(event.target.value)} /></label>
      <small id="road-rain-help" className="road-rain-help">{tr("You choose this amount. It is not taken from the Dhaka weather widget or any live weather feed.")}</small>
      <button type="submit" className="button" disabled={props.predicting}>{tr(props.predicting ? "Predicting…" : "Predict road risk")}</button>
    </form>
    <div className="road-form-tabs" role="group" aria-label={tr("Risk type")}>
      <button type="button" aria-pressed={props.hazard === "waterlogging"} onClick={() => props.onHazard("waterlogging")}>{tr("Rainwater")}</button>
      <button type="button" aria-pressed={props.hazard === "traffic"} onClick={() => props.onHazard("traffic")}>{tr("Traffic jam")}</button>
    </div>
    {/* Retry resubmits the same inputs through the form, so browser validation still applies. */}
    {props.error && <div role="alert" className="road-form-error">
      <p>{tr(props.error.message)} <button type="button" className="road-retry" disabled={props.predicting} onClick={() => form.current?.requestSubmit()}>{tr("Retry")}</button></p>
      {/* The ML service's own reason is for whoever runs the service; it is not translated. */}
      {props.error.detail && <details className="road-error-detail"><summary>{tr("Technical details")}</summary><code>{props.error.detail}</code></details>}
    </div>}
    {props.stale && <p role="status">{tr("Inputs changed. Run the prediction again to update the map.")}</p>}
    {props.forecast && !props.stale && <>
      <p className="road-model-version">{tr("Scenario result")} · {props.forecast.at.replace("T", " ")}<br />{props.forecast.model_version}</p>
      {props.forecast.aggregation === "maximum_segment_probability" && <p>{tr("Each road shows the highest probability among its mapped segments and directions.")}</p>}
    </>}
    {!props.forecast && !props.predicting && <p role="status">{tr("Choose your inputs and run a prediction. Gray roads have no prediction yet.")}</p>}
  </section>;
}
