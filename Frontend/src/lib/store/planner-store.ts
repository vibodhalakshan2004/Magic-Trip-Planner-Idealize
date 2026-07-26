"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Budget, DestinationResponse, Hotel, HotelResponse, Place, RoutePlan, Trip } from "@/lib/api/types";

type PlannerState = {
  currentTripId: string | null;
  trip: Trip | null;
  suggestedPlaces: Place[];
  selectedPlaces: Place[];
  destinationSummary: string | null;
  suggestedHotels: Hotel[];
  selectedHotels: Hotel[];
  hotelSummary: string | null;
  routePlan: RoutePlan | null;
  budget: Budget | null;
  stale: { hotels: boolean; route: boolean; budget: boolean };
  setTrip: (trip: Trip | null) => void;
  setDestination: (response: DestinationResponse) => void;
  setSelectedPlaces: (places: Place[]) => void;
  setHotels: (response: HotelResponse) => void;
  setSelectedHotels: (hotels: Hotel[]) => void;
  setRoute: (route: RoutePlan | null) => void;
  setBudget: (budget: Budget | null) => void;
  hydrateTrip: (state: {
    trip: Trip;
    selectedPlaces?: Place[];
    selectedHotels?: Hotel[];
    routePlan?: RoutePlan | null;
    budget?: Budget | null;
  }) => void;
  reset: () => void;
};

const initial = {
  currentTripId: null,
  trip: null,
  suggestedPlaces: [],
  selectedPlaces: [],
  destinationSummary: null,
  suggestedHotels: [],
  selectedHotels: [],
  hotelSummary: null,
  routePlan: null,
  budget: null,
  stale: { hotels: false, route: false, budget: false },
};

export const usePlannerStore = create<PlannerState>()(
  persist(
    (set) => ({
      ...initial,
      setTrip: (trip) => set({ trip, currentTripId: trip?.id ?? null }),
      setDestination: (response) => set({ suggestedPlaces: uniquePlaces(response.suggested_places), destinationSummary: response.summary }),
      setSelectedPlaces: (selectedPlaces) =>
        set((state) => {
          const uniqueSelected = uniquePlaces(selectedPlaces);
          return {
            selectedPlaces: uniqueSelected,
            suggestedPlaces: mergePlaces(state.suggestedPlaces, uniqueSelected),
            stale: { hotels: true, route: true, budget: true },
            suggestedHotels: [],
            selectedHotels: [],
            routePlan: null,
            budget: null,
          };
        }),
      setHotels: (response) => set({ suggestedHotels: response.recommended_hotels, hotelSummary: response.summary, stale: { hotels: false, route: true, budget: true } }),
      setSelectedHotels: (selectedHotels) => set({ selectedHotels: uniqueHotels(selectedHotels), stale: { hotels: false, route: false, budget: true }, budget: null }),
      setRoute: (routePlan) => set({ routePlan, stale: { hotels: false, route: false, budget: true } }),
      setBudget: (budget) => set({ budget, stale: { hotels: false, route: false, budget: false } }),
      hydrateTrip: ({ trip, selectedPlaces = [], selectedHotels = [], routePlan = null, budget = null }) =>
        set({
          ...initial,
          trip,
          currentTripId: trip.id,
          selectedPlaces: uniquePlaces(selectedPlaces),
          suggestedPlaces: uniquePlaces(selectedPlaces),
          selectedHotels: uniqueHotels(selectedHotels),
          suggestedHotels: uniqueHotels(selectedHotels),
          routePlan,
          budget,
          stale: { hotels: false, route: false, budget: false },
        }),
      reset: () => set(initial),
    }),
    { name: "magictrip-planner" },
  ),
);

function placeKey(place: Place) {
  return place.place_key || `${place.name}-${place.latitude ?? ""}-${place.longitude ?? ""}`;
}

function hotelKey(hotel: Hotel) {
  return hotel.hotel_key || `${hotel.name}-${hotel.latitude ?? ""}-${hotel.longitude ?? ""}`;
}

function uniquePlaces(places: Place[]) {
  const map = new Map<string, Place>();
  for (const place of places) map.set(placeKey(place), place);
  return [...map.values()];
}

function mergePlaces(left: Place[], right: Place[]) {
  return uniquePlaces([...left, ...right]);
}

function uniqueHotels(hotels: Hotel[]) {
  const map = new Map<string, Hotel>();
  for (const hotel of hotels) map.set(hotelKey(hotel), hotel);
  return [...map.values()];
}
