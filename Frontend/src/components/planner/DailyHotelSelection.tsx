"use client";

import { Home, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import * as hotelApi from "@/lib/api/hotels";
import type { Hotel, RoutePlan } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";
import { LoadingState } from "@/components/LoadingState";
import { money, minutes } from "@/lib/utils/format";
import { SmartImage } from "@/components/planner/cards";

export function DailyHotelSelection({
  tripId,
  route,
  selectedHotels,
  activeDay,
  onSaved,
  onError,
  onNext,
}: {
  tripId: string;
  route: RoutePlan;
  selectedHotels: Hotel[];
  activeDay: number;
  onSaved: (hotels: Hotel[]) => void;
  onError: (error: unknown) => void;
  onNext: () => void;
}) {
  const [hotelType, setHotelType] = useState("any");
  const [preference, setPreference] = useState("");
  const [manualQuery, setManualQuery] = useState("");
  const [rooms, setRooms] = useState(1);
  const [radiusKm, setRadiusKm] = useState(20);
  const [suggestions, setSuggestions] = useState<Hotel[]>([]);
  const [busy, setBusy] = useState(false);
  const [searched, setSearched] = useState(false);
  const [goingHome, setGoingHome] = useState(false);

  const selectedByDay = useMemo(() => new Map(selectedHotels.filter((hotel) => hotel.day_number).map((hotel) => [hotel.day_number, hotel])), [selectedHotels]);
  const totalDays = Math.max(route.days.length, 1);
  const isLastDay = activeDay === totalDays;
  const currentSelection = selectedByDay.get(activeDay);

  async function refreshSelections() {
    const hotels = await hotelApi.getDailyHotelSelections(tripId);
    onSaved(hotels);
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    onError(undefined);
    try {
      await action();
    } catch (error) {
      onError(error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-5">
      {busy ? <LoadingState title="Updating hotel options" description="Finding stays near this day route endpoint and calculating transfer costs." /> : null}

      <div className="grid gap-4 rounded-md border border-slate-200 bg-slate-50 p-4">
        <h3 className="font-bold text-slate-800">1. Select Accommodation</h3>
        <div className="grid gap-4 md:grid-cols-5">
          <Field label="Hotel type">
            <select className={inputClass} value={hotelType} onChange={(event) => setHotelType(event.target.value)}>
              <option>any</option>
              <option>hotel</option>
              <option>guest_house</option>
              <option>villa</option>
              <option>resort</option>
              <option>hostel</option>
              <option>homestay</option>
              <option>apartment</option>
            </select>
          </Field>
          <Field label="Rooms">
            <input className={inputClass} type="text" inputMode="numeric" value={rooms} onChange={(event) => setRooms(Number(event.target.value) || 1)} />
          </Field>
          <Field label="Search radius">
            <select className={inputClass} value={radiusKm} onChange={(event) => setRadiusKm(Number(event.target.value))}><option value={10}>10 km</option><option value={20}>20 km</option><option value={35}>35 km</option><option value={50}>50 km</option></select>
          </Field>
          <Field label="Preference">
            <input className={inputClass} value={preference} onChange={(event) => setPreference(event.target.value)} placeholder="Quiet, budget, view..." />
          </Field>
          <Field label="Manual search">
            <input className={inputClass} value={manualQuery} onChange={(event) => setManualQuery(event.target.value)} placeholder="Hotel, area, city..." />
          </Field>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button disabled={busy} onClick={() => run(async () => {
            const response = await hotelApi.suggestDailyHotels(tripId, activeDay, { hotel_type: hotelType, hotel_preference: manualQuery || preference, rooms, max_results: 8, radius_km: radiusKm });
            setSuggestions(response.suggestions);
            setSearched(true);
          })}>
            <RefreshCw className="h-4 w-4" />
            Search hotels for day {activeDay}
          </Button>
          {isLastDay ? (
            <Button variant="secondary" disabled={busy} onClick={() => run(async () => {
              await hotelApi.selectDailyHotel(tripId, activeDay, null, true);
              await refreshSelections();
              setGoingHome(true);
            })}>
              <Home className="h-4 w-4" />
              Go directly home
            </Button>
          ) : null}
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {suggestions.map((hotel) => (
          <article key={`${hotel.hotel_key}-${hotel.name}`} className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
            <div className="grid gap-0 sm:grid-cols-[150px_1fr]">
              <div className="h-40 bg-slate-100 sm:h-full">
                <SmartImage src={hotel.image_url} alt={hotel.name} kind="hotel" className="h-full w-full object-cover" />
              </div>
              <div className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-black text-slate-950">{hotel.name}</h3>
                  {hotel.rating_estimate ? <span className="rounded bg-amber-50 px-2 py-1 text-xs font-black text-amber-700">{hotel.rating_estimate.toFixed(1)}</span> : null}
                </div>
                <p className="mt-1 text-sm text-slate-500">{hotel.short_description || "Accommodation near this day's route endpoint."}</p>
                <p className="mt-2 text-xs font-bold text-sky-700">Open map data · price and availability must be confirmed</p>
                <div className="mt-3 grid gap-1 text-xs font-bold text-slate-600">
                  <span>{hotel.area || hotel.distance_summary || "Near selected route area"}</span>
                  <span>{hotel.transfer_distance_km ?? 0} km transfer - {minutes(hotel.transfer_time_minutes)}</span>
                  {hotel.total_estimated_price_lkr ? <span>{money(hotel.total_estimated_price_lkr)}</span> : <span>Price range not available</span>}
                </div>
                <Button className="mt-3 w-full" disabled={busy} onClick={() => run(async () => {
                  await hotelApi.selectDailyHotel(tripId, activeDay, hotel);
                  await refreshSelections();
                  setGoingHome(false);
                })}>Select for day {activeDay}</Button>
              </div>
            </div>
          </article>
        ))}
      </div>

      {!busy && suggestions.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-300 bg-white p-5 text-sm font-semibold text-slate-500">
          {searched ? `No matching accommodation found within ${radiusKm} km. Try a wider radius, another type, or a hotel name.` : "Search by hotel name, area, city, or location to find accommodation for this day."}
        </div>
      ) : null}

      {currentSelection ? (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <b>Selected for day {activeDay}:</b> {currentSelection.name}
          {currentSelection.area ? ` - ${currentSelection.area}` : ""}
          {currentSelection.transfer_distance_km ? ` - ${currentSelection.transfer_distance_km} km transfer - ${minutes(currentSelection.transfer_time_minutes)}` : ""}
        </div>
      ) : null}

      {isLastDay && goingHome ? (
        <div className="rounded-md border border-blue-200 bg-blue-50 p-4 text-sm font-semibold text-blue-900">
          Day {activeDay} will finish with the route back to your trip start location.
        </div>
      ) : null}

      <div className="mt-4 flex gap-3">
        <Button disabled={busy || (!currentSelection && !(isLastDay && goingHome))} onClick={onNext} className="w-full">
          {isLastDay ? "Review Final Route Map" : `Save & Go To Day ${activeDay + 1}`}
        </Button>
      </div>
    </div>
  );
}
