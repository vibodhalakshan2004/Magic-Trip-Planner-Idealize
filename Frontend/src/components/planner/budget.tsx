"use client";

import { AlertTriangle, CalendarDays, CheckCircle2, Gauge, Luggage, Printer, Share2, ShieldCheck, WalletCards } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TravelerToolkit } from "@/components/planner/TravelerToolkit";
import type { Budget, Hotel, Place, RoutePlan, Trip } from "@/lib/api/types";
import { money, minutes } from "@/lib/utils/format";

export function BudgetSummaryCards({ budget }: { budget: Budget }) {
  const color = budget.budget_status === "within_budget" ? "border-emerald-200 bg-emerald-50 text-emerald-900" : budget.budget_status === "near_limit" ? "border-amber-200 bg-amber-50 text-amber-900" : "border-rose-200 bg-rose-50 text-rose-900";
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <div className={`rounded-md border p-5 ${color}`}>
        <CheckCircle2 className="h-5 w-5" />
        <p className="mt-3 text-sm font-bold uppercase tracking-normal">{budget.budget_status.replace("_", " ")}</p>
        <p className="text-3xl font-black">{money(budget.total_estimated_cost_lkr)}</p>
      </div>
      <div className="rounded-md border border-slate-200 bg-white p-5">
        <WalletCards className="h-5 w-5 text-slate-500" />
        <p className="mt-3 text-sm font-bold text-slate-500">Budget range</p>
        <p className="text-xl font-black text-slate-950">{money(budget.budget_min_lkr)} - {money(budget.budget_max_lkr)}</p>
      </div>
      <div className="rounded-md border border-slate-200 bg-white p-5">
        <Gauge className="h-5 w-5 text-slate-500" />
        <p className="mt-3 text-sm font-bold text-slate-500">{budget.over_budget_amount_lkr > 0 ? "Over budget" : "Remaining"}</p>
        <p className="text-xl font-black text-slate-950">{money(budget.over_budget_amount_lkr > 0 ? budget.over_budget_amount_lkr : budget.remaining_budget_lkr)}</p>
      </div>
    </div>
  );
}

export function BudgetBreakdown({ budget }: { budget: Budget }) {
  return (
    <div className="grid gap-4">
      <div className="grid gap-3 md:grid-cols-3">
        {[
          ["Places", budget.selected_places_cost_lkr],
          ["Hotels", budget.hotel_cost_lkr],
          ["Food", budget.food_cost_lkr],
          ["Transport", budget.transport_cost_lkr],
          ["Other", budget.other_cost_lkr],
          ["Buffer", budget.buffer_lkr],
        ].map(([label, value]) => (
          <div key={label} className="rounded-md border border-slate-200 bg-white p-4">
            <p className="text-sm font-bold text-slate-500">{label}</p>
            <p className="text-xl font-black text-slate-950">{money(Number(value))}</p>
          </div>
        ))}
      </div>
      <div className="rounded-md border border-slate-200 bg-white p-4">
        <h3 className="font-black text-slate-950">Detailed breakdown</h3>
        <div className="mt-3 grid gap-2">
          {budget.breakdown.map((item, index) => <div key={index} className="flex justify-between gap-4 border-t border-slate-100 pt-2 text-sm"><span><b>{item.category}</b> · {item.description}</span><b>{money(item.amount_lkr)}</b></div>)}
        </div>
      </div>
      {[...budget.warnings, ...budget.suggestions].length ? (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="mr-2 inline h-4 w-4" />{[...budget.warnings, ...budget.suggestions].join(" ")}
        </div>
      ) : null}
      <p className="rounded-md bg-slate-100 p-4 text-sm text-slate-700">{budget.summary}</p>
    </div>
  );
}

export function FinalTripSummary({ trip, places, hotels, route, budget }: { trip: Trip | null; places: Place[]; hotels: Hotel[]; route: RoutePlan | null; budget: Budget | null }) {
  const packing = packingSuggestions(places);
  const today = route?.days.find((day) => day.date === new Date().toISOString().slice(0, 10));
  return (
    <div className="grid gap-4">
      <div className="rounded-md border border-slate-200 bg-white p-5">
        <h2 className="text-2xl font-black text-slate-950">{trip ? `${trip.start_location} to ${trip.destination}` : "Trip summary"}</h2>
        <p className="text-sm text-slate-500">{trip?.start_date} to {trip?.end_date} · {trip?.travelers} travelers · {trip?.transport_type}</p>
      </div>
      <div className="flex flex-wrap gap-2 print:hidden">
        <Button variant="secondary" onClick={() => window.print()}><Printer className="h-4 w-4" />Print / save PDF</Button>
        <Button variant="secondary" disabled={!trip || !route} onClick={() => trip && route && downloadCalendar(trip, route)}><CalendarDays className="h-4 w-4" />Export calendar</Button>
        <Button variant="secondary" disabled={!trip} onClick={() => trip && shareTrip(trip)}><Share2 className="h-4 w-4" />Share trip</Button>
      </div>
      {today ? (
        <div className="rounded-md border border-blue-200 bg-blue-50 p-5">
          <p className="text-sm font-black uppercase tracking-wide text-blue-800">Today - Day {today.day_number}</p>
          <p className="mt-1 text-xl font-black text-slate-950">{today.stops[0]?.name || "Travel day"}</p>
          <p className="text-sm text-slate-600">Start {today.start_time || "08:00"} - {today.day_distance_km ?? 0} km - {minutes(today.day_travel_time_minutes)}</p>
          {today.stops[0] ? <a className="mt-3 inline-block text-sm font-bold text-blue-700 underline" href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${today.stops[0].latitude},${today.stops[0].longitude}`)}`} target="_blank" rel="noreferrer">Open next stop in Maps</a> : null}
        </div>
      ) : null}
      <div className="grid gap-4 md:grid-cols-3">
        <SummaryCard title="Places" value={places.length} lines={places.map((p) => p.name)} />
        <SummaryCard title="Hotels" value={hotels.length} lines={hotels.map((h) => h.name)} />
        <SummaryCard title="Route" value={`${route?.total_distance_km ?? 0} km`} lines={[minutes(route?.total_travel_time_minutes), route?.map_provider || "Map provider pending"]} />
      </div>
      {budget ? <BudgetSummaryCards budget={budget} /> : <p className="rounded-md bg-slate-100 p-4 text-sm text-slate-600">Calculate budget to complete the final summary.</p>}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-md border border-slate-200 bg-white p-5">
          <h3 className="font-black text-slate-950"><Luggage className="mr-2 inline h-4 w-4 text-emerald-600" />Packing checklist</h3>
          <ul className="mt-3 grid gap-2 text-sm text-slate-600">{packing.map((item) => <li key={item}>□ {item}</li>)}</ul>
        </div>
        <div className="rounded-md border border-amber-200 bg-amber-50 p-5">
          <h3 className="font-black text-amber-950"><ShieldCheck className="mr-2 inline h-4 w-4" />Before you travel</h3>
          <ul className="mt-3 grid gap-2 text-sm text-amber-900">
            <li>Confirm hotel inventory, taxes, cancellation terms, and check-in time directly.</li>
            <li>Verify attraction hours, ticket rules, Poya-day closures, and transport schedules.</li>
            <li>Download offline maps and keep emergency contacts available without internet.</li>
            <li>Route, weather, and budget values are planning estimates, not guarantees.</li>
          </ul>
        </div>
      </div>
      {trip ? <TravelerToolkit trip={trip} places={places} hotels={hotels} route={route} budget={budget} /> : null}
    </div>
  );
}

function packingSuggestions(places: Place[]) {
  const categories = new Set(places.map((place) => place.category));
  const items = ["Passport/ID, booking confirmations, travel insurance", "Reusable water bottle, sunscreen, insect repellent", "Light rain jacket or compact umbrella", "Power bank and Sri Lanka-compatible power adapter"];
  if (categories.has("religious") || categories.has("culture")) items.push("Temple-appropriate clothing that covers shoulders and knees");
  if (categories.has("nature") || categories.has("adventure")) items.push("Comfortable walking shoes and a small first-aid kit");
  if (categories.has("beach")) items.push("Swimwear, quick-dry towel, hat, and reef-safe sunscreen");
  return items;
}

function shareTrip(trip: Trip) {
  const data = { title: `Trip to ${trip.destination}`, text: `${trip.start_location} to ${trip.destination}, ${trip.start_date} to ${trip.end_date}`, url: window.location.href };
  if (navigator.share) void navigator.share(data).catch(() => undefined);
  else void navigator.clipboard.writeText(window.location.href);
}

function createCalendarFile(trip: Trip, route: RoutePlan) {
  const events = route.days.flatMap((day) => day.stops.map((stop) => {
    const start = icsDate(day.date, stop.start_time || "09:00");
    const end = icsDate(day.date, stop.end_time || stop.start_time || "10:00");
    return ["BEGIN:VEVENT", `UID:${escapeIcs(`${trip.id}-${day.day_number}-${stop.place_key || stop.name}`)}@magictripplanner`, `DTSTART:${start}`, `DTEND:${end}`, `SUMMARY:${escapeIcs(stop.name)}`, `LOCATION:${escapeIcs(`${stop.latitude ?? ""},${stop.longitude ?? ""}`)}`, "DESCRIPTION:Generated by MagicTripPlanner. Verify opening hours and reservations.", "END:VEVENT"].join("\r\n");
  }));
  const content = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//MagicTripPlanner//Trip Itinerary//EN", ...events, "END:VCALENDAR"].join("\r\n");
  return {
    content,
    filename: `${trip.destination.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-itinerary.ics`,
  };
}

function downloadCalendar(trip: Trip, route: RoutePlan) {
  const calendar = createCalendarFile(trip, route);
  const href = URL.createObjectURL(new Blob([calendar.content], { type: "text/calendar;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = href;
  link.download = calendar.filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(href), 60_000);
}

function icsDate(day: string, time: string) {
  return `${day.replaceAll("-", "")}T${time.replace(":", "")}00`;
}

function escapeIcs(value: string) {
  return value.replaceAll("\\", "\\\\").replaceAll(";", "\\;").replaceAll(",", "\\,").replaceAll("\n", "\\n");
}

function SummaryCard({ title, value, lines }: { title: string; value: string | number; lines: (string | undefined)[] }) {
  return <div className="rounded-md border border-slate-200 bg-white p-4"><p className="text-sm font-bold text-slate-500">{title}</p><p className="text-2xl font-black text-slate-950">{value}</p><div className="mt-2 grid gap-1 text-sm text-slate-600">{lines.slice(0, 5).map((line, i) => line ? <span key={i}>{line}</span> : null)}</div></div>;
}
