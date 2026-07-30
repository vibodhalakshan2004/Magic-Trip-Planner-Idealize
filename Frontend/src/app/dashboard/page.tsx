"use client";

import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiErrorAlert } from "@/components/ApiErrorAlert";
import { AppShell } from "@/components/AppShell";
import { DashboardTripCard } from "@/components/DashboardTripCard";
import { Button } from "@/components/ui/button";
import { getPreferences } from "@/lib/api/preferences";
import { deleteTrip, listTrips } from "@/lib/api/trips";
import type { Trip } from "@/lib/api/types";
import { useAuthStore } from "@/lib/store/auth-store";
import { money } from "@/lib/utils/format";

export default function DashboardPage() {
  const router = useRouter();
  const authenticated = useAuthStore((state) => state.authenticated);
  const user = useAuthStore((state) => state.user);
  const authHydrated = useAuthStore((state) => state.hydrated);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<unknown>();
  const trips = useQuery({ queryKey: ["trips", user?.id], queryFn: listTrips, enabled: authHydrated && authenticated && !!user?.id });
  const prefs = useQuery({ queryKey: ["preferences", user?.id], queryFn: getPreferences, enabled: authHydrated && authenticated && !!user?.id });
  const sortedTrips = useMemo(
    () => [...(trips.data ?? [])].sort((a, b) => new Date(b.updated_at ?? b.created_at ?? 0).getTime() - new Date(a.updated_at ?? a.created_at ?? 0).getTime()),
    [trips.data],
  );

  useEffect(() => {
    if (authHydrated && !authenticated) router.replace("/login");
  }, [authenticated, authHydrated, router]);

  async function removeTrip(trip: Trip) {
    if (!window.confirm(`Delete trip to ${trip.destination}?`)) return;
    setError(undefined);
    setDeletingId(trip.id);
    try {
      await deleteTrip(trip.id);
      await trips.refetch();
    } catch (err) {
      setError(err);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <AppShell>
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-3xl font-black text-slate-950">Dashboard</h1>
          <p className="mt-2 text-slate-500">Pick up an old plan or start a fresh Sri Lanka route.</p>
        </div>
        <Link href="/planner/new" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-700"><Plus className="h-4 w-4" /> New trip</Link>
      </div>
      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_320px]">
        <section className="grid gap-4">
          <ApiErrorAlert error={error} onRetry={() => setError(undefined)} />
          <ApiErrorAlert error={trips.error} onRetry={() => trips.refetch()} />
          {sortedTrips.length ? (
            sortedTrips.map((trip) => <DashboardTripCard key={trip.id} trip={trip} deleting={deletingId === trip.id} onDelete={removeTrip} />)
          ) : (
            <div className="rounded-md border border-slate-200 bg-white p-8 text-center">
              <p className="font-black text-slate-950">No trips yet</p>
              <p className="mt-1 text-sm text-slate-500">Create a trip to generate places, hotels, route, and budget.</p>
              <Button className="mt-4" onClick={() => router.push("/planner/new")}>Create trip</Button>
            </div>
          )}
        </section>
        <aside className="grid content-start gap-4">
          <div className="rounded-md border border-slate-200 bg-white p-4">
            <p className="font-black text-slate-950">Saved preferences</p>
            {prefs.data ? <p className="mt-2 text-sm text-slate-600">{prefs.data.travel_style} · {prefs.data.food_preference} · {money(prefs.data.budget_min)} - {money(prefs.data.budget_max)}</p> : <p className="mt-2 text-sm text-slate-500">No saved preferences yet. You can add them in the planner.</p>}
          </div>
        </aside>
      </div>
    </AppShell>
  );
}
