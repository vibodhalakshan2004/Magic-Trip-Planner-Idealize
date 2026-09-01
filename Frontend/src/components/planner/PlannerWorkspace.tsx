"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "@/lib/api/client";
import * as budgetApi from "@/lib/api/budget";
import * as destinationApi from "@/lib/api/destination";
import * as hotelApi from "@/lib/api/hotels";
import * as preferenceApi from "@/lib/api/preferences";
import * as routeApi from "@/lib/api/routes";
import * as tripApi from "@/lib/api/trips";
import type { ManualRouteStop, Place, RoutePlan, RouteStop, SavedPreferencePrompt } from "@/lib/api/types";
import { useAuthStore } from "@/lib/store/auth-store";
import { usePlannerStore } from "@/lib/store/planner-store";
import { ApiErrorAlert } from "@/components/ApiErrorAlert";
import { AppShell } from "@/components/AppShell";
import { LoadingState } from "@/components/LoadingState";
import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";
import { BudgetBreakdown, BudgetSummaryCards, FinalTripSummary } from "@/components/planner/budget";
import { PlaceSearchCombobox, PlaceSuggestionCard, SelectedPlacesPanel } from "@/components/planner/cards";
import { DailyHotelSelection } from "@/components/planner/DailyHotelSelection";
import { PlannerStepper } from "@/components/planner/PlannerStepper";
import { PreferenceForm } from "@/components/planner/PreferenceForm";
import { RouteSection } from "@/components/planner/RouteSection";
import { SavedPreferenceDecisionModal } from "@/components/planner/SavedPreferenceDecisionModal";
import { TripForm, type TripFormValues } from "@/components/planner/TripForm";
import { AutoPlanner, VersionHistory } from "@/components/planner/PlanningTools";
import { ShareTrip } from "@/components/planner/ShareTrip";
import { money } from "@/lib/utils/format";

type StepId = "preferences" | "trip" | "places" | "place-select" | "route" | "route-hotels" | "budget" | "final" | string;

export function PlannerWorkspace({ tripId }: { tripId?: string }) {
  const router = useRouter();
  const authenticated = useAuthStore((state) => state.authenticated);
  const authHydrated = useAuthStore((state) => state.hydrated);
  const store = usePlannerStore();
  const resetPlanner = usePlannerStore((state) => state.reset);
  const [active, setActive] = useState<StepId>(tripId ? "places" : "trip");
  const [error, setError] = useState<unknown>();
  const [busy, setBusy] = useState<string | null>(null);
  const [prompt, setPrompt] = useState<{ data: SavedPreferencePrompt; retry: (useSaved: boolean) => Promise<void> } | null>(null);
  const [activeStop, setActiveStop] = useState<RouteStop | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const runInFlight = useRef(false);

  async function run(label: string, fn: () => Promise<void>) {
    if (runInFlight.current) return;
    runInFlight.current = true;
    setError(undefined);
    setBusy(label);
    try {
      await fn();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
      runInFlight.current = false;
    }
  }

  async function restore(id: string) {
    await run("restore", async () => {
      const trip = await tripApi.getTrip(id);
      const [places, hotels] = await Promise.all([
        destinationApi.getSelectedPlaces(id).catch((err) => (err instanceof ApiError && err.status === 404 ? [] : Promise.reject(err))),
        hotelApi.getDailyHotelSelections(id).catch((err) => (err instanceof ApiError && err.status === 404 ? [] : Promise.reject(err))),
      ]);
      const route = places.length ? await routeApi.getLatestRoute(id).catch((err) => (err instanceof ApiError && err.status === 404 ? null : Promise.reject(err))) : null;
      const budget = places.length ? await budgetApi.getLatestBudget(id).catch((err) => (err instanceof ApiError && err.status === 404 ? null : Promise.reject(err))) : null;
      store.hydrateTrip({ trip, selectedPlaces: places, selectedHotels: hotels, routePlan: route, budget });
      setActive(nextRestoreStep({ places: places.length, route, hasBudget: !!budget }));
      setToast("Trip restored");
    });
  }

  async function runWithPreference(action: (useSaved?: boolean | null) => Promise<void>) {
    setError(undefined);
    setBusy(active);
    try {
      await action(null);
    } catch (err) {
      if (err instanceof ApiError && err.preferencePrompt) {
        setPrompt({ data: err.preferencePrompt, retry: async (useSaved) => { setPrompt(null); await run(active, async () => action(useSaved)); } });
      } else {
        setError(err);
      }
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => {
    if (authHydrated && !authenticated) router.replace("/login");
  }, [authenticated, authHydrated, router]);

  useEffect(() => {
    if (!tripId) return;
    const timer = window.setTimeout(() => void restore(tripId), 0);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tripId]);

  useEffect(() => {
    if (tripId) return;
    const timer = window.setTimeout(() => {
      resetPlanner();
      setActive("trip");
      setError(undefined);
      setToast(null);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [resetPlanner, tripId]);

  const steps = useMemo(() => {
    const hasTrip = !!store.trip;
    const hasPlaces = store.selectedPlaces.length > 0;
    const routeConfirmed = store.routePlan?.route_status === "confirmed";
    
    const baseSteps = [
      { id: "preferences", label: "Preferences", complete: false, optional: true },
      { id: "trip", label: "Trip setup", complete: hasTrip },
      { id: "places", label: "Destination ideas", complete: store.suggestedPlaces.length > 0 || hasPlaces, disabled: !hasTrip, reason: !hasTrip ? "Create trip first" : undefined },
      { id: "place-select", label: "Place selection", complete: hasPlaces, disabled: !hasTrip, reason: !hasTrip ? "Create trip first" : undefined },
      { id: "route", label: "Route map", complete: !!store.routePlan, disabled: !hasPlaces, reason: !hasPlaces ? "Select places first" : store.stale.route ? "Regenerate route" : undefined },
    ];

    const daySteps = [];
    if (routeConfirmed && store.routePlan) {
      const lastDayNumber = store.routePlan.days.at(-1)?.day_number;
      for (const day of store.routePlan.days) {
        daySteps.push({
          id: `day-${day.day_number}`,
          label: `Day ${day.day_number}`,
          complete: store.selectedHotels.some(h => h.day_number === day.day_number) || (day.day_number === lastDayNumber && !!store.budget),
          disabled: false,
        });
      }
    }

    const tailSteps = [
      { id: "route-hotels", label: "Map w/ Hotels", complete: store.selectedHotels.length > 0, disabled: !routeConfirmed, reason: !routeConfirmed ? "Confirm route first" : undefined },
      { id: "budget", label: "Budget", complete: !!store.budget, disabled: !routeConfirmed, reason: !routeConfirmed ? "Confirm route first" : store.stale.budget ? "Recalculate budget" : undefined },
      { id: "final", label: "Final summary", complete: !!store.budget, disabled: !hasTrip, reason: !hasTrip ? "Create trip first" : undefined },
    ];

    return [...baseSteps, ...daySteps, ...tailSteps];
  }, [store.trip, store.selectedPlaces.length, store.selectedHotels, store.suggestedPlaces.length, store.routePlan, store.budget, store.stale]);

  function choosePlace(place: Place) {
    const normalized = normalizePlace(place);
    const exists = store.selectedPlaces.some((p) => placeIdentity(p) === placeIdentity(normalized));
    if (!exists && (!Number.isFinite(normalized.latitude) || !Number.isFinite(normalized.longitude))) {
      setError(new Error("This suggestion has no verified map location. Find it with place search before adding it."));
      return;
    }
    store.setSelectedPlaces(exists ? store.selectedPlaces.filter((p) => placeIdentity(p) !== placeIdentity(normalized)) : [...store.selectedPlaces, normalized]);
  }

  async function savePlaces() {
    if (!store.trip || !store.selectedPlaces.length) return setError(new Error("Select at least one place before saving."));
    await run("save-places", async () => {
      const result = await destinationApi.selectPlaces(store.trip!.id, store.selectedPlaces);
      store.setSelectedPlaces(result.selected_places);
      setToast(result.message);
      setActive("route");
    });
  }

  return (
    <AppShell>
      {!authHydrated ? <LoadingState title="Restoring your session" description="Checking your saved login before opening the planner." /> : null}
      <div className="mb-7 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-xs font-extrabold tracking-[0.15em] text-[#d56535]">ITINERARY BUILDER</p>
          <h1 className="mt-2 font-[family-name:var(--font-display)] text-4xl tracking-[-0.03em] text-[#123c32] sm:text-5xl">
            {store.trip ? store.trip.destination : "Where are you heading?"}
          </h1>
          <p className="mt-2 text-[#60766f]">{store.trip ? `Starting in ${store.trip.start_location}` : "Start with the essentials. You can refine every detail afterwards."}</p>
        </div>
        {store.trip ? (
          <div className="rounded-xl border border-[#17453a]/10 bg-white px-4 py-3 shadow-[0_6px_20px_rgba(18,60,50,.04)]">
            <p className="text-[10px] font-extrabold tracking-wider text-[#789087]">PLANNED BUDGET</p>
            <p className="mt-0.5 text-sm font-extrabold text-[#173e34]">{money(store.trip.budget_min)} – {money(store.trip.budget_max)}</p>
          </div>
        ) : null}
      </div>
      {toast ? <div role="status" className="mb-4 rounded-xl border border-[#b9d7c5] bg-[#e9f4ed] p-3.5 text-sm font-bold text-[#19503f]">{toast}</div> : null}
      {store.trip ? <div className="mb-5 grid gap-3"><AutoPlanner tripId={store.trip.id} onComplete={async () => { await restore(store.trip!.id); setToast("Your complete plan is ready"); }} onError={setError} /><div className="grid gap-3 xl:grid-cols-2"><VersionHistory tripId={store.trip.id} onRestored={async () => { await restore(store.trip!.id); setToast("Trip version restored"); }} onError={setError} /><ShareTrip tripId={store.trip.id} onError={setError} /></div></div> : null}
      <div className="grid min-w-0 gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
        <PlannerStepper steps={steps} active={active} onSelect={(id) => { setError(undefined); setActive(id as StepId); }} />
        <div className="grid min-w-0 gap-4">
          <ApiErrorAlert error={error} onRetry={() => setError(undefined)} />
          {busy && busy !== "restore" ? <LoadingState title={busy === "save-places" ? "Saving selected places" : "Working on this step"} description="This can take a moment while the planner updates saved trip data." /> : null}
          {renderStep()}
        </div>
      </div>
      <SavedPreferenceDecisionModal prompt={prompt?.data ?? null} onChoose={(useSaved) => void prompt?.retry(useSaved)} onClose={() => setPrompt(null)} />
    </AppShell>
  );

  function renderStep() {
    if (busy === "restore") return <LoadingState title="Restoring your trip" description="Reading saved places, daily hotels, latest route, and latest budget." />;

    switch (active) {
      case "preferences":
        return <Panel title="Optional preferences" copy="Save your travel style, food needs, interests, transport, hotel type, and LKR range. We will still ask before reusing them."><PreferenceForm onSubmit={async (values) => run("preferences", async () => { await preferenceApi.savePreferences({ ...values, interests: split(values.interests) }); setToast("Preferences saved"); })} /></Panel>;
      case "trip":
        return <Panel title="Trip setup" copy="Start with the route shape. Destination suggestions, hotels, route, and budget all attach to this trip."><TripForm onSubmit={async (values: TripFormValues) => run("trip", async () => { store.reset(); const trip = await tripApi.createTrip(values); store.setTrip(trip); setToast("Trip created"); setActive("places"); router.replace(`/planner/${trip.id}`); })} /></Panel>;
      case "places":
        return <Panel title="Find places for your trip" copy="Share what you enjoy and we’ll suggest Sri Lanka stops that fit your route, pace, and budget."><GeneratePlaces onGenerate={(payload) => runWithPreference(async (useSaved) => { const response = await destinationApi.suggestPlaces(store.trip!.id, { ...payload, use_saved_preferences: useSaved }); store.setDestination(response); setToast("Destination ideas are ready"); setActive("place-select"); })} busy={busy === "places"} /></Panel>;
      case "place-select":
        return <Panel title="Select places" copy={store.destinationSummary || "Choose from generated suggestions or add custom OpenStreetMap places."}><div className="grid gap-5 xl:grid-cols-[1fr_320px]"><div className="grid gap-4"><PlaceSearchCombobox tripId={store.trip!.id} onAdd={choosePlace} /><div className="grid gap-4 md:grid-cols-2">{store.suggestedPlaces.map((place, index) => <PlaceSuggestionCard key={`${placeIdentity(place)}-${index}`} place={place} selected={store.selectedPlaces.some((p) => placeIdentity(p) === placeIdentity(place))} onToggle={choosePlace} />)}</div></div><div className="grid content-start gap-3"><SelectedPlacesPanel places={store.selectedPlaces} onRemove={(key) => store.setSelectedPlaces(store.selectedPlaces.filter((p) => p.place_key !== key))} /><Button disabled={busy === "save-places"} onClick={savePlaces}>Save selected places</Button></div></div></Panel>;
      case "route":
        return (
          <Panel title="Build your daily route" copy={store.routePlan ? "Your route is ready. Adjust the stop order or timing, then recalculate when it feels right." : "Turn your selected places into a practical day-by-day route with travel time included."}>
            <RouteSection
              tripId={store.trip?.id}
              places={store.selectedPlaces}
              hotels={[]}
              route={store.routePlan}
              activeStop={activeStop}
              setActiveStop={setActiveStop}
              onNext={() => setActive("day-1")}
              onConfirm={() => run("route-confirm", async () => {
                const route = await routeApi.confirmRoute(store.trip!.id);
                store.setRoute(route);
                setToast("Route confirmed");
                setActive("day-1");
              })}
              onGenerate={(body) =>
                run("route", async () => {
                  const route = await routeApi.generateRoute(store.trip!.id, body);
                  store.setRoute(route);
                  setToast(body.manual_schedule?.length ? "Route recalculated with your schedule" : "Optimal route generated");
                })
              }
              busy={busy === "route"}
            />
          </Panel>
        );
      case "route-hotels":
        return (
          <Panel title="Final route with hotels" copy="The map includes each selected accommodation transfer while preserving your day, time, and duration choices. Regenerate only when you want to change the plan.">
            <RouteSection
              tripId={store.trip?.id}
              places={store.selectedPlaces}
              hotels={store.selectedHotels}
              route={store.routePlan}
              activeStop={activeStop}
              setActiveStop={setActiveStop}
              onNext={() => setActive("budget")}
              nextLabel="Next: Budget"
              onConfirm={() => {}}
              onGenerate={(body) => run("route", async () => {
                const route = await routeApi.generateRoute(store.trip!.id, {
                  ...body,
                  include_hotels: true,
                  return_to_hotel: true,
                  return_to_start_location: true,
                  manual_schedule: body.manual_schedule?.length ? body.manual_schedule : manualScheduleFromRoute(store.routePlan),
                });
                store.setRoute(route);
                setToast("Final route generated with hotels");
              })}
              busy={busy === "route"}
            />
          </Panel>
        );
      case "budget":
        return <Panel title="Budget calculation" copy="Calculate your LKR estimate using selected places, confirmed route transport, daily hotels, food, and buffer."><BudgetSection budget={store.budget} hasRoute={!!store.routePlan} onNext={() => setActive("final")} onCalculate={(body) => run("budget", async () => { const budget = await budgetApi.calculateBudget(store.trip!.id, body); store.setBudget(budget); setToast("Budget calculated"); })} busy={busy === "budget"} /></Panel>;
      case "final":
        return <Panel title="Final trip summary" copy="A single view of your selected places, stays, route, and budget status."><FinalTripSummary trip={store.trip} places={store.selectedPlaces} hotels={store.selectedHotels} route={store.routePlan} budget={store.budget} /></Panel>;
    }
    
    if (active.startsWith("day-")) {
      const dayNumber = parseInt(active.split("-")[1], 10);
      const isLastDay = dayNumber === store.routePlan?.days.length;
      return (
        <Panel title={`Day ${dayNumber} planning`} copy="Pick a hotel for this day and estimate your food/other costs.">
          <DailyHotelSelection 
            key={dayNumber}
            tripId={store.trip!.id} 
            route={store.routePlan!} 
            selectedHotels={store.selectedHotels}
            activeDay={dayNumber}
            onSaved={(hotels) => { store.setSelectedHotels(hotels); setToast(`Day ${dayNumber} selection saved`); }} 
            onError={setError} 
            onNext={() => {
              if (!isLastDay) {
                setActive(`day-${dayNumber + 1}`);
                return;
              }
              void run("route", async () => {
                const route = await routeApi.generateRoute(store.trip!.id, {
                  day_start_time: "08:00",
                  include_hotels: true,
                  return_to_hotel: true,
                  return_to_start_location: true,
                  manual_schedule: manualScheduleFromRoute(store.routePlan),
                });
                store.setRoute(route);
                setToast("Final route generated with every selected hotel");
                setActive("route-hotels");
              });
            }}
          />
        </Panel>
      );
    }
  }
}

function Panel({ title, copy, children }: { title: string; copy: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-[#17453a]/10 bg-white p-5 shadow-[0_8px_30px_rgba(18,60,50,.04)] sm:p-7">
      <h2 className="text-2xl font-extrabold tracking-[-0.025em] text-[#173e34]">{title}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-[#60766f]">{copy}</p>
      <div className="mt-6">{children}</div>
    </section>
  );
}

function GeneratePlaces({ onGenerate, busy }: { onGenerate: (payload: { interests: string[]; trip_style: string; special_notes: string }) => void; busy: boolean }) {
  const [interests, setInterests] = useState("");
  const [tripStyle, setTripStyle] = useState("balanced");
  const [notes, setNotes] = useState("");
  return <div className="grid gap-4"><Field label="Interests"><input className={inputClass} placeholder="e.g. nature, hiking, photography" value={interests} onChange={(e) => setInterests(e.target.value)} /></Field><Field label="Trip style"><select className={inputClass} value={tripStyle} onChange={(e) => setTripStyle(e.target.value)}><option>relaxed</option><option>balanced</option><option>packed</option></select></Field><Field label="Special notes"><textarea className={`${inputClass} min-h-24`} placeholder="e.g. I prefer scenic places and less crowded locations" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field><Button disabled={busy} onClick={() => onGenerate({ interests: split(interests), trip_style: tripStyle, special_notes: notes })}>Generate destination ideas</Button></div>;
}




function BudgetSection({ budget, hasRoute, onCalculate, onNext, busy }: { budget: ReturnType<typeof usePlannerStore.getState>["budget"]; hasRoute: boolean; onCalculate: (body: { food_cost_per_person_per_day_lkr: number; shopping_other_cost_lkr: number }) => void; onNext: () => void; busy: boolean }) {
  const [food, setFood] = useState(2500);
  const [other, setOther] = useState(0);
  return <div className="grid gap-4">{!hasRoute ? <p className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-800">Route is not generated yet. Budget can continue, but transport costs may be less precise.</p> : null}<div className="grid gap-4 md:grid-cols-2"><Field label="Food per person per day LKR"><input className={inputClass} type="number" value={food} onChange={(e) => setFood(Number(e.target.value))} /></Field><Field label="Shopping and other LKR"><input className={inputClass} type="number" value={other} onChange={(e) => setOther(Number(e.target.value))} /></Field></div><Button disabled={busy} onClick={() => onCalculate({ food_cost_per_person_per_day_lkr: food, shopping_other_cost_lkr: other })}>Calculate budget</Button>{budget ? <><BudgetSummaryCards budget={budget} /><BudgetBreakdown budget={budget} /><Button onClick={onNext}>Next: Final summary</Button></> : null}</div>;
}

function split(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function normalizePlace(place: Place): Place {
  return { ...place, place_key: place.place_key || place.name.toLowerCase().replace(/[^a-z0-9]+/g, "_"), source: place.source || "openstreetmap", category: place.category || "other", suitable_for: place.suitable_for || [], warnings: place.warnings || [] };
}

function placeIdentity(place: Place) {
  return place.place_key || `${place.name}-${place.latitude ?? ""}-${place.longitude ?? ""}`;
}

function nextRestoreStep(state: { places: number; route: ReturnType<typeof usePlannerStore.getState>["routePlan"]; hasBudget: boolean }): StepId {
  if (state.hasBudget) return "final";
  if (state.route?.route_status === "confirmed") return "day-1";
  if (state.route) return "route";
  if (state.places > 0) return "route";
  return "places";
}

function manualScheduleFromRoute(route: RoutePlan | null): ManualRouteStop[] {
  if (!route) return [];
  return route.days.flatMap((day) =>
    day.stops.map((stop) => ({
      place_key: stop.place_key ?? stop.name.toLowerCase().replace(/[^a-z0-9]+/g, "_"),
      day_number: day.day_number,
      start_time: stop.start_time ?? null,
      visit_duration_hours: stop.visit_duration_hours ?? 1,
    })),
  );
}
