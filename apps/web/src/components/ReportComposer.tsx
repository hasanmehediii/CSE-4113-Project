"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useCivicLocale } from "@/hooks/useCivicLocale";
import { mutate, uploadImage } from "@/lib/api-client";
import { message, useResource, type Category, type Complaint, type Road } from "@/lib/civic";
import { isDhakaLocation, parseReportLocation, type ReportLocation } from "@/lib/report-location";
import { CivicShell, CivicForm, CivicFileInput, Feedback } from "./CivicUI";
import LocationPicker from "./map/LocationPicker";

function ReportIcon({ type }: { type: "report" | "road" | "pin" | "photo" }) {
  return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {type === "report" && <><path d="M8 4H5a1 1 0 0 0-1 1v16h16V5a1 1 0 0 0-1-1h-3M8 2h8v5H8zM8 11h8M8 15h5" /></>}
    {type === "road" && <><path d="m6 3-3 18M18 3l3 18M12 3v3m0 5v3m0 5v2" /></>}
    {type === "pin" && <><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></>}
    {type === "photo" && <><path d="M4 6h4l2-3h4l2 3h4a1 1 0 0 1 1 1v13H3V7a1 1 0 0 1 1-1Z" /><circle cx="12" cy="12" r="3.5" /></>}
  </svg>;
}

export default function ReportComposer() {
  const { tr, label, number } = useCivicLocale();
  const categories = useResource<Category[]>("/categories");
  const roads = useResource<Road[]>("/map/roads");
  const [kind, setKind] = useState("complaint");
  const [position, setPosition] = useState({ latitude: "", longitude: "" });
  const [roadId, setRoadId] = useState("");
  const [busy, setBusy] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState("");
  const [locationError, setLocationError] = useState("");
  const [manualOpen, setManualOpen] = useState(false);
  const locationPanel = useRef<HTMLElement>(null);
  const alive = useRef(true);
  const locationRevision = useRef(0);
  const router = useRouter();
  const point = parseReportLocation(position.latitude, position.longitude);

  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);

  function selectLocation(next: ReportLocation, road = "") {
    locationRevision.current += 1;
    setPosition({ latitude: next.latitude.toFixed(6), longitude: next.longitude.toFixed(6) });
    setRoadId(road);
    setLocationError("");
  }

  function locate() {
    if (!navigator.geolocation) { setLocationError("Your browser does not support location access."); return; }
    const revision = ++locationRevision.current;
    setLocating(true);
    setLocationError("");
    navigator.geolocation.getCurrentPosition(result => {
      if (!alive.current) return;
      setLocating(false);
      // A delayed GPS response must not overwrite a pin the user just chose.
      if (revision !== locationRevision.current) return;
      const next = { latitude: result.coords.latitude, longitude: result.coords.longitude };
      if (isDhakaLocation(next)) selectLocation(next);
      else setLocationError("Report locations must be within the Dhaka service area.");
    }, () => {
      if (!alive.current) return;
      setLocating(false);
      if (revision === locationRevision.current) setLocationError("Location access failed. Pick a place on the map or enter coordinates.");
    }, { timeout: 10000, enableHighAccuracy: true, maximumAge: 30000 });
  }

  function enterCoordinate(key: "latitude" | "longitude", value: string) {
    locationRevision.current += 1;
    setPosition(previous => ({ ...previous, [key]: value }));
    setRoadId("");
    setLocationError("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    if (!point) {
      setLocationError("Choose a location on the map or enter valid Dhaka coordinates.");
      locationPanel.current?.focus();
      return;
    }
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    try {
      const links = String(data.get("images") || "").split("\n").map(value => value.trim()).filter(Boolean);
      const file = data.get("photo");
      if (links.length + (file instanceof File && file.size ? 1 : 0) > 5) throw new Error("Add at most 5 images in total.");
      if (file instanceof File && file.size) links.push(await uploadImage(file));
      const row = await mutate<Complaint>("/complaints", {
        kind, title: data.get("title"), description: data.get("description"), address: data.get("address"),
        category_code: data.get("category_code"), road_id: roadId || null, ...point,
        condition: kind === "complaint" ? "bad" : data.get("condition"), images: links,
      });
      router.push(`/complaints/${row.id}`);
    } catch (cause) { setError(message(cause)); }
    finally { setBusy(false); }
  }

  return <CivicShell title={tr("A small report. A useful change.")} intro={tr("Tell your community what is happening. Each report or road update earns 1 point. False reports can forfeit your points.")}>
    <CivicForm className="civic-form report-composer" onSubmit={submit} onInvalidCapture={event => {
      if (event.target instanceof HTMLElement) {
        const details = event.target.closest<HTMLDetailsElement>(".report-coordinates");
        if (details) { details.open = true; setManualOpen(true); }
      }
    }}>
      <fieldset className="report-layout" disabled={busy}>
        <section className="report-panel report-details" aria-labelledby="report-details-title">
          <div className="report-section-heading"><span className="report-step">{number(1)}</span><div><h2 id="report-details-title">{tr("Tell us what happened")}</h2><p>{tr("A few details help the right team take action.")}</p></div></div>
          <fieldset className="report-type-group"><legend>{tr("What would you like to share?")}</legend><div className="report-type-options">
            {(["complaint", "road_update"] as const).map(type => <label key={type} className={`report-type-option${kind === type ? " selected" : ""}`}>
              <input type="radio" name="kind" value={type} checked={kind === type} onChange={() => setKind(type)} />
              <span className="report-type-icon"><ReportIcon type={type === "complaint" ? "report" : "road"} /></span>
              <span><strong>{tr(type === "complaint" ? "Civic complaint" : "Road update")}</strong><small>{tr(type === "complaint" ? "Flag a problem to be fixed" : "Share the latest road condition")}</small></span>
            </label>)}
          </div></fieldset>
          <label>{tr("Short title")}<input name="title" required minLength={5} maxLength={180} placeholder={tr("Water overflowing on Dhanmondi Road 12")} /></label>
          <div className={kind === "road_update" ? "report-field-pair" : undefined}>
            <label>{tr("Category")}<select name="category_code" required defaultValue=""><option value="" disabled>{tr("Select a category")}</option>{categories.data?.map(category => <option key={category.code} value={category.code}>{label(category.code, category.label)}</option>)}</select></label>
            {kind === "road_update" && <label>{tr("Observed condition")}<select name="condition"><option value="bad">{tr("Bad")}</option><option value="good">{tr("Good")}</option><option value="unknown">{tr("Unknown")}</option></select></label>}
          </div>
          <label>{tr("What did you observe?")}<textarea name="description" required minLength={10} maxLength={5000} rows={4} placeholder={tr("Describe the problem, when you noticed it, and who is affected.")} /></label>
          <label>{tr("Street / landmark")}<input name="address" required minLength={3} maxLength={300} placeholder={tr("Road, area, or a nearby landmark")} /></label>
          <Feedback error={categories.error} retry={() => void categories.reload()} />
        </section>

        <section className="report-panel report-location" aria-labelledby="report-location-title" tabIndex={-1} ref={locationPanel}>
          <div className="report-section-heading"><span className="report-step">{number(2)}</span><div><h2 id="report-location-title">{tr("Pin the exact spot")}</h2><p id="report-map-help">{tr("Click the map to drop a pin. Drag it to adjust.")}</p></div><span className="report-section-icon"><ReportIcon type="pin" /></span></div>
          <LocationPicker value={point} onChange={selectLocation} onError={setLocationError} disabled={busy} />
          <div className={`report-location-status${point ? " is-selected" : ""}`} role="status"><span aria-hidden="true">{point ? "✓" : "○"}</span>{tr(point ? "Location selected" : "No location selected yet")}</div>
          <button type="button" className="button secondary report-locate" onClick={locate} disabled={locating || busy}><ReportIcon type="pin" />{tr(locating ? "Finding your location…" : "Use my current location")}</button>
          {!!roads.data?.length && <label className="report-road-shortcut">{tr("Or choose a known road")}<select name="road_id" value={roadId} onChange={event => {
            const road = roads.data?.find(row => row.id === event.target.value);
            if (road) selectLocation(road, road.id);
            else setRoadId("");
          }}><option value="">{tr("Use my precise report location")}</option>{roads.data.map(road => <option key={road.id} value={road.id}>{road.name}</option>)}</select></label>}
          <details className="report-coordinates" open={manualOpen} onToggle={event => setManualOpen(event.currentTarget.open)}>
            <summary>{tr("Enter coordinates manually")}</summary><div className="report-field-pair">
              <label>{tr("Latitude")}<input name="latitude" type="number" step="any" min={23.6} max={24} value={position.latitude} onChange={event => enterCoordinate("latitude", event.target.value)} placeholder="23.770000" /></label>
              <label>{tr("Longitude")}<input name="longitude" type="number" step="any" min={90.2} max={90.6} value={position.longitude} onChange={event => enterCoordinate("longitude", event.target.value)} placeholder="90.390000" /></label>
            </div>
          </details>
          <small>{tr("Report locations must be within the Dhaka service area.")}</small>
          <Feedback error={locationError} />
        </section>

        <section className="report-panel report-evidence" aria-labelledby="report-evidence-title">
          <div className="report-section-heading"><span className="report-step">{number(3)}</span><div><h2 id="report-evidence-title">{tr("Add a little evidence")} <span className="report-optional">{tr("Optional")}</span></h2><p>{tr("A clear photo makes your report easier to understand.")}</p></div><span className="report-section-icon"><ReportIcon type="photo" /></span></div>
          <div className="report-photo-box"><CivicFileInput /><small>{tr("JPEG, PNG or WebP · up to 5 MB")}</small></div>
          <details className="report-image-links"><summary>{tr("Have an image link instead?")}</summary><label>{tr("Or add image links (optional, one HTTPS link per line)")}<textarea name="images" rows={2} placeholder="https://example.com/photo.jpg" /></label></details>
          <small>{tr("At most 5 images total. Photos are public; avoid faces, IDs, and private information.")}</small>
        </section>

        <div className="report-submit-bar"><div className="report-reward"><span aria-hidden="true">✦</span><div><strong>{tr("Your city. Your contribution.")}</strong><small>{tr("Earn 1 community point for sharing an update.")}</small></div></div><button className="button" disabled={busy || !categories.data?.length}>{busy ? tr("Submitting…") : tr("Publish report · earn 1 point")}<span aria-hidden="true">↗</span></button></div>
      </fieldset>
      <Feedback error={error} />
    </CivicForm>
  </CivicShell>;
}
