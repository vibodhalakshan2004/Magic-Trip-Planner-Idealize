"use client";

import { ArrowDownUp, ChevronDown, ChevronUp, Clock, CloudRain, Coffee, Navigation, RefreshCw, Route, Sparkles, TimerReset } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";
import { RouteMap } from "@/components/planner/RouteMap";
import type { Hotel, ManualRouteStop, Place, RouteDay, RoutePlan, RouteSegment, RouteStop } from "@/lib/api/types";
import { dayLabel, minutes } from "@/lib/utils/format";

export function RouteSection({
  tripId,
  places,
  hotels,
  route,
  activeStop,
  setActiveStop,
  onGenerate,
  onConfirm,
  onNext,
  busy,
}: {
  tripId?: string;
  places: Place[];
  hotels: Hotel[];
  route: RoutePlan | null;
  activeStop: RouteStop | null;
  setActiveStop: (stop: RouteStop) => void;
  onGenerate: (body: { day_start_time: string; return_to_start_location?: boolean; return_to_hotel?: boolean; include_hotels?: boolean; manual_schedule?: ManualRouteStop[] }) => void;
  onConfirm: () => void;
  onNext: () => void;
  busy: boolean;
}) {
  const [customising, setCustomising] = useState(false);

  if (!route) return <OptimalRouteGenerator tripId={tripId} busy={busy} onGenerate={onGenerate} />;

  const confirmed = route.route_status === "confirmed";

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-emerald-200 bg-emerald-50 p-4">
        <div>
          <p className="text-sm font-bold text-emerald-800">
            <Sparkles className="mr-1 inline h-4 w-4" />
            Optimised route · {route.total_distance_km ?? 0} km · {minutes(route.total_travel_time_minutes)} · {confirmed ? "Confirmed" : "Draft"}
          </p>
          {route.summary ? <p className="mt-1 text-xs text-emerald-700">{route.summary}</p> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" type="button" onClick={() => setCustomising((value) => !value)}>
            <ArrowDownUp className="h-4 w-4" />
            {customising ? "Hide schedule" : "Edit schedule"}
          </Button>
          <Button variant="secondary" type="button" disabled={busy} onClick={() => onGenerate({ day_start_time: "08:00", return_to_start_location: true })}>
            <RefreshCw className="h-4 w-4" /> Regenerate
          </Button>
        </div>
      </div>

      {customising ? (
        <CustomSchedulePanel
          places={places}
          route={route}
          busy={busy}
          onRecalculate={(manual, dayStartTime) => {
            onGenerate({ day_start_time: dayStartTime, return_to_start_location: true, manual_schedule: manual });
            setCustomising(false);
          }}
        />
      ) : null}

      <QuickReplanPanel places={places} route={route} busy={busy} onGenerate={onGenerate} />

      <RouteMap days={route.days} hotels={hotels} activeStop={activeStop} onSelectStop={setActiveStop} />
      <ItineraryTimeline days={route.days} activeStop={activeStop} onSelectStop={setActiveStop} />

      <div className="flex flex-wrap gap-2">
        {!confirmed ? <Button disabled={busy} onClick={onConfirm}>Confirm route</Button> : null}
        <Button disabled={!confirmed} onClick={onNext}>Next: Daily hotels</Button>
      </div>
    </div>
  );
}

function QuickReplanPanel({ places, route, busy, onGenerate }: {
  places: Place[];
  route: RoutePlan;
  busy: boolean;
  onGenerate: (body: { day_start_time: string; return_to_start_location?: boolean; manual_schedule?: ManualRouteStop[] }) => void;
}) {
  const placeByKey = new Map(places.map((place) => [place.place_key, place]));
  const current = route.days.flatMap((day) => day.stops.map((stop) => ({
    place_key: stop.place_key ?? stop.name.toLowerCase().replace(/[^a-z0-9]+/g, "_"),
    day_number: day.day_number,
    start_time: stop.start_time ?? null,
    visit_duration_hours: stop.visit_duration_hours ?? 1,
  })));

  function shiftLate() {
    onGenerate({ day_start_time: "10:00", return_to_start_location: true, manual_schedule: current.map((stop) => ({ ...stop, start_time: shiftTime(stop.start_time, 120) })) });
  }

  function relaxed() {
    onGenerate({ day_start_time: "09:00", return_to_start_location: true, manual_schedule: current.map((stop) => ({ ...stop, visit_duration_hours: Math.min(12, Math.max(0.5, (stop.visit_duration_hours ?? 1) * 1.25)) })) });
  }

  function rainFriendly() {
    const indoor = new Set(["culture", "food", "shopping", "religious", "historical"]);
    const reordered = route.days.flatMap((day) => {
      const dayStops = current.filter((stop) => stop.day_number === day.day_number);
      return [...dayStops].sort((a, b) => Number(indoor.has(placeByKey.get(b.place_key)?.category ?? "")) - Number(indoor.has(placeByKey.get(a.place_key)?.category ?? "")));
    });
    onGenerate({ day_start_time: "09:00", return_to_start_location: true, manual_schedule: reordered });
  }

  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <p className="text-sm font-black text-slate-950">One-click replan</p>
      <p className="mt-1 text-xs text-slate-500">Your selected places stay in the trip while timing or order changes.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <Button variant="secondary" disabled={busy} onClick={shiftLate}><TimerReset className="h-4 w-4" />Started two hours late</Button>
        <Button variant="secondary" disabled={busy} onClick={relaxed}><Coffee className="h-4 w-4" />Make the pace relaxed</Button>
        <Button variant="secondary" disabled={busy} onClick={rainFriendly}><CloudRain className="h-4 w-4" />Prioritize indoor stops</Button>
      </div>
    </div>
  );
}

function shiftTime(value: string | null | undefined, minutesToAdd: number) {
  if (!value) return null;
  const [hours, minutes] = value.split(":").map(Number);
  if (!Number.isFinite(hours) || !Number.isFinite(minutes)) return value;
  const total = (hours * 60 + minutes + minutesToAdd) % (24 * 60);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

function OptimalRouteGenerator({
  tripId,
  busy,
  onGenerate,
}: {
  tripId?: string;
  busy: boolean;
  onGenerate: (body: { day_start_time: string; return_to_start_location?: boolean }) => void;
}) {
  const [start, setStart] = useState("08:00");

  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 p-5">
      <div className="flex items-center gap-3">
        <Sparkles className="h-6 w-6 text-emerald-600" />
        <div>
          <p className="font-black text-slate-950">Build the most practical route</p>
          <p className="text-sm text-slate-500">The route starts from your trip start location, spreads places across your trip days, and returns home on the final day.</p>
        </div>
      </div>

      <div className="mt-5">
        <Field label="Default day start time">
          <input className={inputClass} type="time" value={start} onChange={(event) => setStart(event.target.value)} />
        </Field>
      </div>

      <Button className="mt-4 w-full" disabled={!tripId || busy} onClick={() => onGenerate({ day_start_time: start, return_to_start_location: true })}>
        <Route className="h-4 w-4" />
        {busy ? "Generating route..." : "Generate optimal route"}
      </Button>
    </div>
  );
}

function CustomSchedulePanel({
  places,
  route,
  busy,
  onRecalculate,
}: {
  places: Place[];
  route: RoutePlan;
  busy: boolean;
  onRecalculate: (manual: ManualRouteStop[], dayStartTime: string) => void;
}) {
  const allStops = useMemo(
    () =>
      route.days.flatMap((day) =>
        day.stops.map((stop) => ({
          place_key: stop.place_key ?? stop.name.toLowerCase().replace(/[^a-z0-9]+/g, "_"),
          day_number: day.day_number,
          start_time: stop.start_time ?? null,
          visit_duration_hours: stop.visit_duration_hours ?? 1,
          _dayStr: String(day.day_number),
          _hoursStr: String(stop.visit_duration_hours ?? 1),
        })),
      ),
    [route.days],
  );
  const [items, setItems] = useState(allStops);
  const [dayStart, setDayStart] = useState("08:00");
  const placeByKey = new Map(places.map((place) => [place.place_key, place]));

  function move(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= items.length) return;
    const next = [...items];
    [next[index], next[target]] = [next[target], next[index]];
    setItems(next);
  }

  function update(index: number, patch: Partial<(typeof items)[0]>) {
    setItems((previous) => previous.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)));
  }

  function buildManual(): ManualRouteStop[] {
    return items.map((item) => ({
      place_key: item.place_key,
      day_number: Math.max(1, parseInt(item._dayStr, 10) || 1),
      start_time: item.start_time ?? null,
      visit_duration_hours: Math.max(0.5, parseFloat(item._hoursStr) || 1),
    }));
  }

  return (
    <div className="rounded-md border border-blue-200 bg-blue-50 p-4">
      <p className="font-black text-slate-950">
        <ArrowDownUp className="mr-1 inline h-4 w-4 text-blue-600" />
        Edit route order and timing
      </p>
      <p className="text-xs text-slate-500">Change day assignment, order, start time, and visit duration, then recalculate distances, travel times, and costs.</p>

      <div className="my-4">
        <Field label="Day start time">
          <input className={inputClass} type="time" value={dayStart} onChange={(event) => setDayStart(event.target.value)} />
        </Field>
      </div>

      <div className="grid gap-2">
        {items.map((item, index) => {
          const place = placeByKey.get(item.place_key);
          return (
            <div key={`${item.place_key}-${index}`} className="grid gap-2 rounded-md border border-slate-200 bg-white p-3 md:grid-cols-[1fr_70px_110px_100px_auto] md:items-end">
              <div>
                <p className="text-sm font-bold text-slate-900">
                  <span className="mr-1 inline-block w-5 text-center text-xs font-black text-emerald-700">{index + 1}.</span>
                  {place?.name ?? item.place_key}
                </p>
                <p className="text-xs text-slate-500">{place?.category ?? "place"}</p>
              </div>
              <Field label="Day">
                <input className={inputClass} type="text" inputMode="numeric" value={item._dayStr} onChange={(event) => update(index, { _dayStr: event.target.value })} />
              </Field>
              <Field label="Start">
                <input className={inputClass} type="time" value={item.start_time ?? ""} onChange={(event) => update(index, { start_time: event.target.value || null })} />
              </Field>
              <Field label="Hours">
                <input className={inputClass} type="text" inputMode="decimal" value={item._hoursStr} onChange={(event) => update(index, { _hoursStr: event.target.value })} />
              </Field>
              <div className="flex gap-1">
                <button type="button" disabled={index === 0} onClick={() => move(index, -1)} className="inline-flex h-8 w-8 items-center justify-center rounded border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-30" title="Move up">
                  <ChevronUp className="h-4 w-4" />
                </button>
                <button type="button" disabled={index === items.length - 1} onClick={() => move(index, 1)} className="inline-flex h-8 w-8 items-center justify-center rounded border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 disabled:opacity-30" title="Move down">
                  <ChevronDown className="h-4 w-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <Button className="mt-4" disabled={busy} onClick={() => onRecalculate(buildManual(), dayStart)}>
        <Clock className="h-4 w-4" />
        {busy ? "Recalculating..." : "Recalculate route"}
      </Button>
    </div>
  );
}

function ItineraryTimeline({ days, activeStop, onSelectStop }: { days: RouteDay[]; activeStop: RouteStop | null; onSelectStop: (stop: RouteStop) => void }) {
  return (
    <div className="grid gap-4">
      {days.map((day) => (
        <section key={day.day_number} className="rounded-md border border-slate-200 bg-white p-4">
          <h3 className="font-black text-slate-950">{dayLabel(day.day_number, day.date, day.start_time)}</h3>
          <p className="mt-1 text-sm text-slate-500">
            {day.start_point_name} to {day.end_point_name} - {day.day_distance_km ?? 0} km - {minutes(day.day_travel_time_minutes)}
          </p>
          <div className="mt-4 grid gap-2">
            {day.stops.map((stop, index) => (
              <button key={`${stop.place_key ?? stop.name}-${index}`} type="button" onClick={() => onSelectStop(stop)} className={`rounded-md border p-3 text-left transition-colors ${activeStop?.name === stop.name ? "border-emerald-400 bg-emerald-50" : "border-slate-200 bg-slate-50 hover:bg-slate-100"}`}>
                <b className="text-slate-900">{stop.name}</b>
                <span className="block text-sm text-slate-500">
                  {stop.arrival_time || stop.start_time} - {stop.end_time} - {stop.category || "stop"}
                  {stop.travel_time_from_previous_minutes ? ` - ${minutes(stop.travel_time_from_previous_minutes)} from prev.` : null}
                </span>
                {stop.availability_warnings?.length ? <span className="mt-1 block text-xs font-semibold text-amber-700">{stop.availability_warnings[0]}</span> : null}
              </button>
            ))}
          </div>
          <TurnByTurnDirections segments={day.segments} />
        </section>
      ))}
    </div>
  );
}

function TurnByTurnDirections({ segments }: { segments: RouteSegment[] }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="mt-4 grid gap-2">
      {segments.map((segment, index) => {
        const id = `${segment.from_name}-${segment.to_name}-${index}`;
        const isOpen = open === id;
        return (
          <div key={id} className="rounded-md border border-slate-200">
            <button className="flex w-full items-center justify-between gap-3 p-3 text-left text-sm font-bold text-slate-800" type="button" onClick={() => setOpen(isOpen ? null : id)}>
              <span>
                <Navigation className="mr-2 inline h-4 w-4" />
                {segment.from_name} to {segment.to_name}
              </span>
              <span className="text-xs text-slate-500">
                {segment.distance_km ?? 0} km - {minutes(segment.duration_minutes)} <ChevronDown className={`inline h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`} />
              </span>
            </button>
            {isOpen ? (
              <ol className="grid gap-2 border-t border-slate-200 p-3 text-sm text-slate-600">
                {segment.instructions?.length ? segment.instructions.map((step, stepIndex) => <li key={stepIndex}>{step.instruction} <span className="text-xs text-slate-400">({step.distance_km ?? 0} km)</span></li>) : <li>No turn-by-turn instructions for this segment.</li>}
              </ol>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
