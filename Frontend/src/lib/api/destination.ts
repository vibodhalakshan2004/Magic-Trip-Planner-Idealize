import { json, request } from "./client";
import type { DestinationResponse, Place } from "./types";

export const suggestPlaces = (tripId: string, body: { use_saved_preferences?: boolean | null; interests: string[]; trip_style: string; special_notes?: string }) =>
  json<DestinationResponse>(`/destination/trips/${tripId}/suggest-places`, "POST", body);
export const searchPlaces = (tripId: string, query: string) =>
  request<{ query: string; destination?: string; suggestions: Place[] }>(`/destination/trips/${tripId}/place-search?query=${encodeURIComponent(query)}`);
export const selectPlaces = (tripId: string, selected_places: Place[]) =>
  json<{ trip_id: string; selected_places_count: number; selected_places: Place[]; message: string }>(`/destination/trips/${tripId}/select-places`, "POST", { selected_places });
export const getSelectedPlaces = (tripId: string) => request<Place[]>(`/destination/trips/${tripId}/selected-places`);
