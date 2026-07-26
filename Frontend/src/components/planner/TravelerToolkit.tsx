"use client";

import { Download, ExternalLink, NotebookPen, Plus, Trash2, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";
import { getTripToolkit, updateTripToolkit } from "@/lib/api/trips";
import type { Budget, Hotel, Place, RoutePlan, Trip, TripExpense, TripToolkit } from "@/lib/api/types";
import { money } from "@/lib/utils/format";

type Props = {
  trip: Trip;
  places: Place[];
  hotels: Hotel[];
  route: RoutePlan | null;
  budget: Budget | null;
};

const emptyToolkit = (tripId: string): TripToolkit => ({
  trip_id: tripId,
  traveler_notes: "",
  emergency_contact: "",
  checklist: [],
  expenses: [],
  total_expenses_lkr: 0,
});

export function TravelerToolkit({ trip, places, hotels, route, budget }: Props) {
  const [toolkit, setToolkit] = useState<TripToolkit>(() => emptyToolkit(trip.id));
  const [loadedTripId, setLoadedTripId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [checklistLabel, setChecklistLabel] = useState("");
  const [expense, setExpense] = useState({ description: "", amount: "", category: "other" as TripExpense["category"], paidBy: "Shared", date: "" });
  const [includePrivate, setIncludePrivate] = useState(false);

  useEffect(() => {
    let active = true;
    void getTripToolkit(trip.id)
      .then((value) => { if (active) setToolkit(value); })
      .catch(() => { if (active) setMessage("Toolkit could not be loaded. Your itinerary is still available."); })
      .finally(() => { if (active) setLoadedTripId(trip.id); });
    return () => { active = false; };
  }, [trip.id]);

  const loading = loadedTripId !== trip.id;

  const totalExpenses = useMemo(
    () => toolkit.expenses.reduce((total, item) => total + item.amount_lkr, 0),
    [toolkit.expenses],
  );
  const completedCount = toolkit.checklist.filter((item) => item.completed).length;

  function update<K extends keyof TripToolkit>(key: K, value: TripToolkit[K]) {
    setToolkit((current) => ({ ...current, [key]: value }));
    setMessage("");
  }

  function addChecklistItem(label: string) {
    const clean = label.trim();
    if (!clean) return;
    update("checklist", [...toolkit.checklist, { id: crypto.randomUUID(), label: clean, completed: false }]);
    setChecklistLabel("");
  }

  function addSuggestedChecklist() {
    const existing = new Set(toolkit.checklist.map((item) => item.label.toLowerCase()));
    const additions = suggestedChecklist(places)
      .filter((label) => !existing.has(label.toLowerCase()))
      .map((label) => ({ id: crypto.randomUUID(), label, completed: false }));
    update("checklist", [...toolkit.checklist, ...additions]);
  }

  function addExpense() {
    const amount = Number(expense.amount);
    if (!expense.description.trim() || !Number.isFinite(amount) || amount <= 0) {
      setMessage("Enter an expense description and an amount greater than zero.");
      return;
    }
    const item: TripExpense = {
      id: crypto.randomUUID(),
      description: expense.description.trim(),
      amount_lkr: amount,
      category: expense.category,
      paid_by: expense.paidBy.trim() || "Shared",
      expense_date: expense.date || null,
    };
    update("expenses", [...toolkit.expenses, item]);
    setExpense({ description: "", amount: "", category: "other", paidBy: "Shared", date: "" });
  }

  async function saveToolkit() {
    setSaving(true);
    setMessage("");
    try {
      const saved = await updateTripToolkit(trip.id, {
        traveler_notes: toolkit.traveler_notes,
        emergency_contact: toolkit.emergency_contact,
        checklist: toolkit.checklist,
        expenses: toolkit.expenses,
      });
      setToolkit(saved);
      setMessage("Traveler toolkit saved.");
    } catch {
      setMessage("Toolkit could not be saved. Check the connection and try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="grid gap-4 rounded-md border border-slate-200 bg-slate-50 p-5">
      <div>
        <h3 className="text-xl font-black text-slate-950"><NotebookPen className="mr-2 inline h-5 w-5 text-emerald-600" />Traveler toolkit</h3>
        <p className="mt-1 text-sm text-slate-600">Keep trip-critical notes, readiness tasks, and actual spending with this saved trip. No Google API is used.</p>
      </div>

      {loading ? <p className="text-sm font-semibold text-slate-500">Loading saved toolkit…</p> : null}
      {message ? <p aria-live="polite" className="rounded-md border border-slate-200 bg-white p-3 text-sm font-semibold text-slate-700">{message}</p> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="grid gap-4 rounded-md border border-slate-200 bg-white p-4">
          <Field label="Private trip notes">
            <textarea className={`${inputClass} min-h-28`} maxLength={5000} placeholder="Dietary needs, reservation references, accessibility needs…" value={toolkit.traveler_notes} onChange={(event) => update("traveler_notes", event.target.value)} />
          </Field>
          <Field label="Emergency contact or meeting instructions">
            <textarea className={`${inputClass} min-h-20`} maxLength={500} placeholder="Name, phone number, hotel desk, or agreed meeting point" value={toolkit.emergency_contact} onChange={(event) => update("emergency_contact", event.target.value)} />
          </Field>
          <p className="text-xs text-slate-500">This information is stored in your account. Avoid adding passport numbers or payment-card details.</p>
        </div>

        <div className="rounded-md border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="font-black text-slate-950">Readiness checklist</h4>
            <span className="text-xs font-bold text-slate-500">{completedCount}/{toolkit.checklist.length} complete</span>
          </div>
          <div className="mt-3 flex gap-2">
            <input aria-label="New checklist item" className={inputClass} maxLength={160} placeholder="Add a task" value={checklistLabel} onChange={(event) => setChecklistLabel(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") addChecklistItem(checklistLabel); }} />
            <Button variant="secondary" aria-label="Add checklist item" onClick={() => addChecklistItem(checklistLabel)}><Plus className="h-4 w-4" /></Button>
          </div>
          {!toolkit.checklist.length ? <Button className="mt-3" variant="ghost" onClick={addSuggestedChecklist}>Add suggested travel tasks</Button> : null}
          <ul className="mt-3 grid gap-2">
            {toolkit.checklist.map((item) => (
              <li key={item.id} className="flex items-center gap-2 rounded-md bg-slate-50 p-2 text-sm">
                <input aria-label={`Complete ${item.label}`} checked={item.completed} type="checkbox" onChange={(event) => update("checklist", toolkit.checklist.map((value) => value.id === item.id ? { ...value, completed: event.target.checked } : value))} />
                <span className={`flex-1 ${item.completed ? "text-slate-400 line-through" : "text-slate-700"}`}>{item.label}</span>
                <button aria-label={`Remove ${item.label}`} className="rounded p-1 text-rose-600 hover:bg-rose-50" onClick={() => update("checklist", toolkit.checklist.filter((value) => value.id !== item.id))}><Trash2 className="h-4 w-4" /></button>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="rounded-md border border-slate-200 bg-white p-4">
        <div className="grid gap-3 md:grid-cols-3">
          <div><p className="text-xs font-bold uppercase text-slate-500">Actual spend</p><p className="text-2xl font-black text-slate-950">{money(totalExpenses)}</p></div>
          <div><p className="text-xs font-bold uppercase text-slate-500">Per traveler</p><p className="text-2xl font-black text-slate-950">{money(totalExpenses / Math.max(trip.travelers, 1))}</p></div>
          <div><p className="text-xs font-bold uppercase text-slate-500">Against maximum budget</p><p className={`text-2xl font-black ${totalExpenses > trip.budget_max ? "text-rose-700" : "text-emerald-700"}`}>{money(trip.budget_max - totalExpenses)}</p></div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-5">
          <Field label="Expense"><input className={inputClass} maxLength={160} placeholder="Train tickets" value={expense.description} onChange={(event) => setExpense({ ...expense, description: event.target.value })} /></Field>
          <Field label="Amount LKR"><input className={inputClass} min="1" step="1" type="number" value={expense.amount} onChange={(event) => setExpense({ ...expense, amount: event.target.value })} /></Field>
          <Field label="Category"><select className={inputClass} value={expense.category} onChange={(event) => setExpense({ ...expense, category: event.target.value as TripExpense["category"] })}>{["accommodation", "food", "transport", "activities", "shopping", "other"].map((category) => <option key={category}>{category}</option>)}</select></Field>
          <Field label="Paid by"><input className={inputClass} maxLength={100} value={expense.paidBy} onChange={(event) => setExpense({ ...expense, paidBy: event.target.value })} /></Field>
          <Field label="Date"><input className={inputClass} type="date" value={expense.date} onChange={(event) => setExpense({ ...expense, date: event.target.value })} /></Field>
        </div>
        <Button className="mt-3" variant="secondary" onClick={addExpense}><Plus className="h-4 w-4" />Add actual expense</Button>
        <div className="mt-4 grid gap-2">
          {toolkit.expenses.map((item) => (
            <div key={item.id} className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-2 text-sm">
              <span className="min-w-0 flex-1"><b>{item.description}</b> · {item.category} · paid by {item.paid_by}{item.expense_date ? ` · ${item.expense_date}` : ""}</span>
              <b>{money(item.amount_lkr)}</b>
              <button aria-label={`Remove expense ${item.description}`} className="rounded p-1 text-rose-600 hover:bg-rose-50" onClick={() => update("expenses", toolkit.expenses.filter((value) => value.id !== item.id))}><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Button disabled={saving || loading} onClick={() => void saveToolkit()}>{saving ? "Saving…" : "Save toolkit"}</Button>
        <Button variant="secondary" onClick={() => downloadOfflineItinerary({ trip, places, hotels, route, budget, toolkit, includePrivate })}><Download className="h-4 w-4" />Download offline itinerary</Button>
        <label className="flex items-center gap-2 text-sm text-slate-600"><input checked={includePrivate} type="checkbox" onChange={(event) => setIncludePrivate(event.target.checked)} />Include notes, contact, checklist, and expenses</label>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-md border border-blue-200 bg-blue-50 p-4">
          <h4 className="font-black text-blue-950"><Users className="mr-2 inline h-4 w-4" />Transport handoff</h4>
          <a className="mt-2 inline-flex items-center gap-1 text-sm font-bold text-blue-800 underline" href={mapsDirectionsUrl(trip)} target="_blank" rel="noreferrer">Open trip directions in Google Maps <ExternalLink className="h-3 w-3" /></a>
          <p className="mt-2 text-xs text-blue-800">Opening this link does not consume the project&apos;s Google API quota. Verify schedules and road conditions directly.</p>
        </div>
        <div className="rounded-md border border-violet-200 bg-violet-50 p-4">
          <h4 className="font-black text-violet-950">Booking verification</h4>
          {hotels.length ? <ul className="mt-2 grid gap-1 text-sm">{hotels.slice(0, 5).map((hotel) => <li key={hotel.hotel_key}><a className="font-bold text-violet-800 underline" href={hotelSearchUrl(hotel, trip)} target="_blank" rel="noreferrer">Check {hotel.name} availability</a></li>)}</ul> : <p className="mt-2 text-sm text-violet-800">Select daily hotels to receive verification links.</p>}
          <p className="mt-2 text-xs text-violet-800">Prices in the planner are estimates; confirm inventory, taxes, and cancellation terms before paying.</p>
        </div>
      </div>
    </section>
  );
}

function suggestedChecklist(places: Place[]) {
  const categories = new Set(places.map((place) => place.category));
  const items = ["Confirm accommodation and cancellation terms", "Verify transport schedules", "Save insurance and booking references", "Download offline maps", "Pack ID, medication, charger, and rain protection"];
  if (categories.has("religious") || categories.has("culture")) items.push("Pack clothing suitable for religious sites");
  if (categories.has("nature") || categories.has("adventure")) items.push("Pack walking shoes and a small first-aid kit");
  return items;
}

function mapsDirectionsUrl(trip: Trip) {
  const transit = ["public_transport", "train", "bus"].includes(trip.transport_type);
  const params = new URLSearchParams({ api: "1", origin: trip.start_location, destination: trip.destination, travelmode: transit ? "transit" : "driving" });
  return `https://www.google.com/maps/dir/?${params}`;
}

function hotelSearchUrl(hotel: Hotel, trip: Trip) {
  const query = hotel.search_query || `${hotel.name} ${hotel.area || trip.destination} Sri Lanka official booking`;
  return `https://www.google.com/search?q=${encodeURIComponent(query)}`;
}

function downloadOfflineItinerary({ trip, places, hotels, route, budget, toolkit, includePrivate }: Props & { toolkit: TripToolkit; includePrivate: boolean }) {
  const html = offlineItineraryHtml({ trip, places, hotels, route, budget, toolkit, includePrivate });
  const href = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = href;
  link.download = `${slug(trip.destination)}-offline-itinerary.html`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(href), 60_000);
}

function offlineItineraryHtml({ trip, places, hotels, route, budget, toolkit, includePrivate }: Props & { toolkit: TripToolkit; includePrivate: boolean }) {
  const days = route?.days.map((day) => `<section><h2>Day ${day.day_number} · ${escapeHtml(day.date)}</h2><p>${escapeHtml(day.start_point_name || trip.start_location)} to ${escapeHtml(day.end_point_name || trip.destination)}</p><ol>${day.stops.map((stop) => `<li><b>${escapeHtml(stop.start_time || "")}</b> ${escapeHtml(stop.name)}${stop.note ? `<br><small>${escapeHtml(stop.note)}</small>` : ""}</li>`).join("")}</ol></section>`).join("") || "<p>No route has been generated.</p>";
  const privateSection = includePrivate ? `<section><h2>Private traveler toolkit</h2><p><b>Notes:</b> ${escapeHtml(toolkit.traveler_notes || "None")}</p><p><b>Emergency contact:</b> ${escapeHtml(toolkit.emergency_contact || "None")}</p><h3>Checklist</h3><ul>${toolkit.checklist.map((item) => `<li>${item.completed ? "☑" : "☐"} ${escapeHtml(item.label)}</li>`).join("") || "<li>None</li>"}</ul><h3>Actual expenses</h3><ul>${toolkit.expenses.map((item) => `<li>${escapeHtml(item.description)} — LKR ${item.amount_lkr.toLocaleString("en-LK")} — ${escapeHtml(item.paid_by)}</li>`).join("") || "<li>None</li>"}</ul></section>` : "";
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(trip.destination)} itinerary</title><style>body{font-family:system-ui,sans-serif;max-width:850px;margin:auto;padding:32px;color:#172033}h1,h2,h3{color:#064e3b}section{border-top:1px solid #dbe3ea;padding:16px 0}li{margin:8px 0}.notice{background:#fff7d6;padding:12px;border-radius:8px}@media print{body{padding:0}}</style></head><body><h1>${escapeHtml(trip.start_location)} to ${escapeHtml(trip.destination)}</h1><p>${escapeHtml(trip.start_date)} to ${escapeHtml(trip.end_date)} · ${trip.travelers} travelers · ${escapeHtml(trip.transport_type)}</p><p class="notice">Offline planning copy. Verify live opening hours, reservations, weather, fares, and transport schedules before travel.</p>${days}<section><h2>Selected places</h2><ul>${places.map((place) => `<li>${escapeHtml(place.name)}</li>`).join("") || "<li>None</li>"}</ul><h2>Accommodation</h2><ul>${hotels.map((hotel) => `<li>${escapeHtml(hotel.name)}${hotel.day_number ? ` — Day ${hotel.day_number}` : ""}</li>`).join("") || "<li>None</li>"}</ul></section><section><h2>Budget estimate</h2><p>${budget ? `Estimated total: LKR ${budget.total_estimated_cost_lkr.toLocaleString("en-LK")} (${escapeHtml(budget.budget_status.replaceAll("_", " "))})` : "Not calculated"}</p></section>${privateSection}<footer><small>Generated by MagicTripPlanner. This file contains no live data and works without internet.</small></footer></body></html>`;
}

function escapeHtml(value: string) {
  return value.replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character] || character);
}

function slug(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "trip";
}
