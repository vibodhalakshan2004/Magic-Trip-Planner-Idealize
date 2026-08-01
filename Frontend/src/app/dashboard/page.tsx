"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Compass, Heart, Plus, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiErrorAlert } from "@/components/ApiErrorAlert";
import { AppShell } from "@/components/AppShell";
import { DashboardTripCard } from "@/components/DashboardTripCard";
import { LoadingState } from "@/components/LoadingState";
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
      <div className="flex flex-col justify-between gap-5 md:flex-row md:items-end">
        <div>
          <p className="text-xs font-extrabold tracking-[0.15em] text-[#d56535]">YOUR TRIPS</p>
          <h1 className="mt-2 font-[family-name:var(--font-display)] text-4xl tracking-[-0.03em] text-[#123c32] sm:text-5xl">
            {user?.name ? `Ayubowan, ${user.name.split(" ")[0]}.` : "Welcome back."}
          </h1>
          <p className="mt-2 text-[#60766f]">Continue a plan or start somewhere new.</p>
        </div>
        <Link href="/planner/new" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#17453a] px-5 text-sm font-bold text-white shadow-[0_8px_18px_rgba(23,69,58,.14)] transition hover:-translate-y-0.5 hover:bg-[#0f382f]">
          <Plus className="h-4 w-4" /> Plan a new trip
        </Link>
      </div>
      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_340px]">
        <section className="grid content-start gap-4">
          <ApiErrorAlert error={error} onRetry={() => setError(undefined)} />
          <ApiErrorAlert error={trips.error} onRetry={() => trips.refetch()} />
          {trips.isPending ? (
            <LoadingState title="Finding your trips" description="Your saved plans will appear here in a moment." />
          ) : sortedTrips.length ? (
            sortedTrips.map((trip) => <DashboardTripCard key={trip.id} trip={trip} deleting={deletingId === trip.id} onDelete={removeTrip} />)
          ) : (
            <div className="rounded-2xl border border-dashed border-[#17453a]/20 bg-white/70 px-6 py-12 text-center">
              <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#e6efe9] text-[#17453a]"><Compass className="h-5 w-5" /></span>
              <p className="mt-4 text-lg font-extrabold text-[#173e34]">Your first trip starts here</p>
              <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-[#60766f]">Add your dates and budget, then we’ll help you turn them into a day-by-day Sri Lanka plan.</p>
              <Button className="mt-5" onClick={() => router.push("/planner/new")}>Plan my first trip <ArrowRight className="h-4 w-4" /></Button>
            </div>
          )}
        </section>
        <aside className="grid content-start gap-4">
          <div className="rounded-2xl border border-[#17453a]/10 bg-[#123c32] p-5 text-white">
            <div className="flex items-center justify-between">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10"><SlidersHorizontal className="h-4 w-4" /></span>
              <Link href="/planner/new" className="text-xs font-bold text-[#f4a16f] hover:text-white">Edit in planner</Link>
            </div>
            <p className="mt-5 text-lg font-extrabold">Your travel style</p>
            {prefs.data ? (
              <>
                <p className="mt-2 text-sm leading-6 text-[#cbdcd4]">{titleCase(prefs.data.travel_style)} pace · {titleCase(prefs.data.food_preference)} food</p>
                <p className="mt-1 text-sm font-bold text-white">{money(prefs.data.budget_min)} – {money(prefs.data.budget_max)}</p>
              </>
            ) : (
              <p className="mt-2 text-sm leading-6 text-[#cbdcd4]">Save your pace, interests, and budget once to make future planning quicker.</p>
            )}
          </div>
          <div className="rounded-2xl border border-[#17453a]/10 bg-white p-5">
            <Heart className="h-4 w-4 text-[#d56535]" />
            <p className="mt-4 font-extrabold text-[#173e34]">A small planning tip</p>
            <p className="mt-2 text-sm leading-6 text-[#60766f]">Leave a little space between stops. Sri Lanka’s most memorable moments often happen between the pins.</p>
          </div>
        </aside>
      </div>
    </AppShell>
  );
}

function titleCase(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
