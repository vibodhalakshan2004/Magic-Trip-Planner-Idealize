"use client";

import { History, Loader2, RotateCcw, Sparkles, Square } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";
import { ApiError } from "@/lib/api/client";
import * as planningApi from "@/lib/api/planning";
import type { PlanningJob, TripVersion } from "@/lib/api/types";

export function AutoPlanner({ tripId, onComplete, onError }: { tripId: string; onComplete: () => Promise<void>; onError: (error: unknown) => void }) {
  const [job, setJob] = useState<PlanningJob | null>(null);
  const [loadingLatest, setLoadingLatest] = useState(true);
  const [advanced, setAdvanced] = useState(false);
  const [starting, setStarting] = useState(false);
  const [tripStyle, setTripStyle] = useState<"relaxed" | "balanced" | "packed">("balanced");
  const [interests, setInterests] = useState("");
  const [hotelType, setHotelType] = useState("any");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    let mounted = true;
    planningApi.getLatestJob(tripId).then((latest) => {
      if (mounted) setJob(latest);
    }).catch((error) => {
      // A planning job is optional. Older/manual trips can legitimately have
      // no job record, so that 404 must not obscure a valid saved itinerary.
      if (!(error instanceof ApiError && error.status === 404)) onError(error);
    }).finally(() => {
      if (mounted) setLoadingLatest(false);
    });
    return () => { mounted = false; };
  }, [tripId, onError]);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const timer = window.setTimeout(async () => {
      try {
        const next = await planningApi.getJob(job.id);
        setJob(next);
        if (next.status === "completed") await onComplete();
        if (next.status === "failed") onError(new Error(next.error || "Automatic planning failed."));
      } catch (error) {
        onError(error);
      }
    }, 1200);
    return () => window.clearTimeout(timer);
  }, [job, onComplete, onError]);

  async function start() {
    setStarting(true);
    onError(undefined);
    try {
      const next = await planningApi.createJob(
        tripId,
        {
          use_saved_preferences: true,
          interests: interests.split(",").map((value) => value.trim()).filter(Boolean),
          trip_style: tripStyle,
          special_notes: notes,
          max_places: 6,
          hotel_type: hotelType,
          hotel_preference: "",
          rooms: 1,
          food_cost_per_person_per_day_lkr: 2500,
          shopping_other_cost_lkr: 0,
        },
        crypto.randomUUID(),
      );
      setJob(next);
    } catch (error) {
      onError(error);
    } finally {
      setStarting(false);
    }
  }

  async function retry() {
    if (!job || job.status !== "failed") return;
    setStarting(true);
    onError(undefined);
    try {
      setJob(await planningApi.retryJob(job.id, crypto.randomUUID()));
    } catch (error) {
      onError(error);
    } finally {
      setStarting(false);
    }
  }

  const active = !!job && ["queued", "running"].includes(job.status);
  return (
    <section className="rounded-md border border-violet-200 bg-violet-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><p className="font-black text-violet-950">Plan it for me</p><p className="text-sm text-violet-700">Build places, route, daily stays, and budget in a recoverable background job.</p></div>
        <div className="flex gap-2">
          {!active && job?.status === "failed" ? <Button onClick={() => void retry()} disabled={starting}>{starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />} Resume plan</Button> : null}
          {!active && job?.status !== "failed" ? <Button onClick={() => void start()} disabled={starting || loadingLatest}>{starting || loadingLatest ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} {loadingLatest ? "Checking previous plan" : "Create full plan"}</Button> : null}
          {!active && job?.status === "failed" ? <Button variant="ghost" onClick={() => void start()} disabled={starting}>Start over (uses AI)</Button> : null}
          {active ? <Button variant="danger" onClick={() => void planningApi.cancelJob(job.id).then(setJob).catch(onError)}><Square className="h-4 w-4" /> Cancel</Button> : null}
          {!active ? <Button variant="ghost" onClick={() => setAdvanced((value) => !value)}>{advanced ? "Hide options" : "Options"}</Button> : null}
        </div>
      </div>
      {advanced && !active ? <div className="mt-4 grid gap-3 md:grid-cols-3"><Field label="Travel pace"><select className={inputClass} value={tripStyle} onChange={(event) => setTripStyle(event.target.value as typeof tripStyle)}><option value="relaxed">Relaxed</option><option value="balanced">Balanced</option><option value="packed">Packed</option></select></Field><Field label="Interests"><input className={inputClass} value={interests} onChange={(event) => setInterests(event.target.value)} placeholder="nature, culture, food" /></Field><Field label="Hotel type"><select className={inputClass} value={hotelType} onChange={(event) => setHotelType(event.target.value)}><option value="any">Any</option><option value="hotel">Hotel</option><option value="guest_house">Guest house</option><option value="resort">Resort</option><option value="hostel">Hostel</option></select></Field><div className="md:col-span-3"><Field label="Notes"><input className={inputClass} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Accessibility, pace, or must-see requests" /></Field></div></div> : null}
      {job ? <div className="mt-4" aria-live="polite"><div className="mb-1 flex justify-between text-xs font-bold text-violet-900"><span>{job.current_stage}</span><span>{job.progress}%</span></div><div className="h-2 overflow-hidden rounded-full bg-violet-100"><div className="h-full bg-violet-600 transition-all" style={{ width: `${job.progress}%` }} /></div>{job.status === "failed" ? <><p className="mt-2 text-sm font-semibold text-rose-700">{job.error}</p><p className="mt-1 text-xs text-violet-800">Resume plan reuses the saved places and does not generate new AI suggestions.</p></> : null}{job.status === "cancelled" ? <p className="mt-2 text-sm text-slate-600">Planning cancelled. Work saved before cancellation is still available.</p> : null}</div> : null}
    </section>
  );
}

export function VersionHistory({ tripId, onRestored, onError }: { tripId: string; onRestored: () => Promise<void>; onError: (error: unknown) => void }) {
  const [versions, setVersions] = useState<TripVersion[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setVersions(await planningApi.listVersions(tripId));
  }
  return <section className="rounded-md border border-slate-200 bg-white p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="flex items-center gap-2 font-black text-slate-950"><History className="h-4 w-4" /> Version history</p><p className="text-sm text-slate-500">Save a checkpoint or return to an earlier itinerary.</p></div><div className="flex gap-2"><Button variant="secondary" disabled={busy} onClick={async () => { setBusy(true); try { await planningApi.createVersion(tripId, "Manual checkpoint"); await refresh(); setOpen(true); } catch (error) { onError(error); } finally { setBusy(false); } }}>Save checkpoint</Button><Button variant="ghost" onClick={async () => { if (open) return setOpen(false); setOpen(true); try { await refresh(); } catch (error) { onError(error); } }}>{open ? "Hide" : "Show"}</Button></div></div>{open ? <div className="mt-3 grid gap-2">{versions.length ? versions.map((version) => <div key={version.id} className="flex items-center justify-between rounded border border-slate-200 p-3 text-sm"><div><p className="font-bold text-slate-900">v{version.version_number} · {version.label}</p><p className="text-xs text-slate-500">{new Date(version.created_at).toLocaleString()}</p></div><Button variant="ghost" disabled={busy} onClick={async () => { if (!window.confirm(`Restore version ${version.version_number}? A checkpoint of the current plan will be saved first.`)) return; setBusy(true); try { await planningApi.restoreVersion(tripId, version.id); await onRestored(); await refresh(); } catch (error) { onError(error); } finally { setBusy(false); } }}>Restore</Button></div>) : <p className="text-sm text-slate-500">No checkpoints yet.</p>}</div> : null}</section>;
}
