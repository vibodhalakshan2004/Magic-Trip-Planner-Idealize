import { Calendar, MapPinned, Trash2 } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import type { Trip } from "@/lib/api/types";
import { dateTime, money } from "@/lib/utils/format";

export function DashboardTripCard({ trip, deleting, onDelete }: { trip: Trip; deleting?: boolean; onDelete: (trip: Trip) => void }) {
  return (
    <article className="rounded-md border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <Link href={`/planner/${trip.id}`} className="min-w-0 flex-1">
          <h3 className="font-black text-slate-950 hover:text-emerald-700">{trip.start_location} to {trip.destination}</h3>
          <p className="mt-1 text-sm text-slate-500"><Calendar className="mr-1 inline h-4 w-4" />{trip.start_date} - {trip.end_date}</p>
        </Link>
        <div className="flex items-center gap-2">
          <MapPinned className="h-5 w-5 text-emerald-600" />
          <Button type="button" variant="danger" disabled={deleting} aria-label={`Delete trip to ${trip.destination}`} onClick={() => onDelete(trip)}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <p className="mt-3 text-sm text-slate-600">{trip.travelers} travelers · {trip.transport_type} · {money(trip.budget_min)} - {money(trip.budget_max)}</p>
      <div className="mt-3 grid gap-1 text-xs font-medium text-slate-500 sm:grid-cols-2">
        <span>Created: {dateTime(trip.created_at)}</span>
        <span>Last modified: {dateTime(trip.updated_at ?? trip.created_at)}</span>
      </div>
    </article>
  );
}
