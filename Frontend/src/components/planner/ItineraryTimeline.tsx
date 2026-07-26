"use client";

import { ChevronDown, Navigation } from "lucide-react";
import { useState } from "react";
import type { RouteDay, RouteSegment, RouteStop } from "@/lib/api/types";
import { dayLabel, minutes } from "@/lib/utils/format";

export function ItineraryTimeline({ days, activeStop, onSelectStop }: { days: RouteDay[]; activeStop: RouteStop | null; onSelectStop: (stop: RouteStop) => void }) {
  return (
    <div className="grid gap-4">
      {days.map((day) => (
        <section key={day.day_number} className="rounded-md border border-slate-200 bg-white p-4">
          <h3 className="font-black text-slate-950">{dayLabel(day.day_number, day.date, day.start_time)}</h3>
          <p className="mt-1 text-sm text-slate-500">{day.start_point_name} to {day.end_point_name} · {day.day_distance_km ?? 0} km · {minutes(day.day_travel_time_minutes)}</p>
          <div className="mt-4 grid gap-2">
            {day.stops.map((stop, index) => (
              <button
                key={`${stop.name}-${index}`}
                type="button"
                onClick={() => onSelectStop(stop)}
                className={`rounded-md border p-3 text-left ${activeStop?.name === stop.name ? "border-emerald-400 bg-emerald-50" : "border-slate-200 bg-slate-50"}`}
              >
                <b>{stop.name}</b>
                <span className="block text-sm text-slate-500">{stop.arrival_time || stop.start_time} - {stop.end_time} · {stop.category || "stop"}</span>
                {stop.note ? <span className="block text-sm text-slate-600">{stop.note}</span> : null}
              </button>
            ))}
          </div>
          <TurnByTurnDirections segments={day.segments} />
        </section>
      ))}
    </div>
  );
}

export function TurnByTurnDirections({ segments }: { segments: RouteSegment[] }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="mt-4 grid gap-2">
      {segments.map((segment, index) => {
        const id = `${segment.from_name}-${segment.to_name}-${index}`;
        const isOpen = open === id;
        return (
          <div key={id} className="rounded-md border border-slate-200">
            <button className="flex w-full items-center justify-between gap-3 p-3 text-left text-sm font-bold text-slate-800" type="button" onClick={() => setOpen(isOpen ? null : id)}>
              <span><Navigation className="mr-2 inline h-4 w-4" />{segment.from_name} to {segment.to_name}</span>
              <span className="text-xs text-slate-500">{segment.distance_km ?? 0} km · {minutes(segment.duration_minutes)} <ChevronDown className="inline h-4 w-4" /></span>
            </button>
            {isOpen ? (
              <ol className="grid gap-2 border-t border-slate-200 p-3 text-sm text-slate-600">
                {segment.instructions?.length ? segment.instructions.map((step, stepIndex) => <li key={stepIndex}>{step.instruction} <span className="text-xs text-slate-400">({step.distance_km ?? 0} km)</span></li>) : <li>No turn instructions returned for this segment.</li>}
              </ol>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
