import { ArrowUpRight, CalendarDays, MapPinned, Trash2, Users } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import type { Trip } from "@/lib/api/types";
import { dateTime, money } from "@/lib/utils/format";

export function DashboardTripCard({ trip, deleting, onDelete }: { trip: Trip; deleting?: boolean; onDelete: (trip: Trip) => void }) {
  return (
    <article className="group rounded-2xl border border-[#17453a]/10 bg-white p-5 shadow-[0_8px_30px_rgba(18,60,50,.05)] transition hover:-translate-y-0.5 hover:border-[#17453a]/20 hover:shadow-[0_14px_36px_rgba(18,60,50,.09)] sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <Link href={`/planner/${trip.id}`} className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#e6efe9] text-[#17453a]"><MapPinned className="h-4 w-4" /></span>
            <div className="min-w-0">
              <p className="text-xs font-bold text-[#789087]">{trip.start_location}</p>
              <h3 className="truncate text-xl font-extrabold tracking-[-0.025em] text-[#173e34] transition group-hover:text-[#d56535]">{trip.destination}</h3>
            </div>
          </div>
        </Link>
        <div className="flex items-center gap-2">
          <Link href={`/planner/${trip.id}`} aria-label={`Open trip to ${trip.destination}`} className="inline-flex h-11 w-11 items-center justify-center rounded-xl border border-[#17453a]/10 text-[#17453a] transition hover:bg-[#e6efe9]">
            <ArrowUpRight className="h-4 w-4" />
          </Link>
          <Button className="h-11 w-11 px-0" type="button" variant="danger" disabled={deleting} aria-label={`Delete trip to ${trip.destination}`} onClick={() => onDelete(trip)}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <div className="mt-5 flex flex-wrap gap-2 text-xs font-semibold text-[#526b63]">
        <span className="inline-flex items-center gap-1.5 rounded-lg bg-[#f3f5f1] px-2.5 py-2"><CalendarDays className="h-3.5 w-3.5" />{trip.start_date} – {trip.end_date}</span>
        <span className="inline-flex items-center gap-1.5 rounded-lg bg-[#f3f5f1] px-2.5 py-2"><Users className="h-3.5 w-3.5" />{trip.travelers} {trip.travelers === 1 ? "traveler" : "travelers"}</span>
        <span className="inline-flex items-center rounded-lg bg-[#f3f5f1] px-2.5 py-2 capitalize">{trip.transport_type}</span>
        <span className="inline-flex items-center rounded-lg bg-[#fdf0e8] px-2.5 py-2 font-bold text-[#9a4d2e]">{money(trip.budget_min)} – {money(trip.budget_max)}</span>
      </div>
      <div className="mt-4 grid gap-1 border-t border-[#17453a]/8 pt-4 text-[11px] font-medium text-[#789087] sm:grid-cols-2">
        <span>Created: {dateTime(trip.created_at)}</span>
        <span className="sm:text-right">Updated: {dateTime(trip.updated_at ?? trip.created_at)}</span>
      </div>
    </article>
  );
}
