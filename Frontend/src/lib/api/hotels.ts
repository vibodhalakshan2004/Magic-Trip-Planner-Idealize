import { json, request } from "./client";
import type { DailyHotelResponse, Hotel, HotelResponse } from "./types";

export const suggestHotels = (tripId: string, body: { use_saved_preferences?: boolean | null; hotel_type: string; hotel_preference?: string; rooms: number; max_results: number }) =>
  json<HotelResponse>(`/hotels/trips/${tripId}/suggest-hotels`, "POST", body);
export const searchHotels = (tripId: string, query: string) =>
  request<{ query: string; destination?: string; suggestions: Hotel[] }>(`/hotels/trips/${tripId}/hotel-search?query=${encodeURIComponent(query)}`);
export const selectHotels = (tripId: string, selected_hotels: Hotel[]) =>
  json<{ trip_id: string; selected_hotels_count: number; selected_hotels: Hotel[]; message: string }>(`/hotels/trips/${tripId}/select-hotels`, "POST", { selected_hotels });
export const getSelectedHotels = (tripId: string) => request<Hotel[]>(`/hotels/trips/${tripId}/selected-hotels`);
export const suggestDailyHotels = (tripId: string, dayNumber: number, body: { hotel_type: string; hotel_preference?: string; rooms: number; max_results: number; radius_km: number }) =>
  json<DailyHotelResponse>(`/hotels/trips/${tripId}/days/${dayNumber}/suggest`, "POST", body);
export const selectDailyHotel = (tripId: string, dayNumber: number, hotel: Hotel | null, go_home_without_hotel = false) =>
  json<{ trip_id: string; day_number: number; selected_hotel: Hotel | null; message: string }>(`/hotels/trips/${tripId}/days/${dayNumber}/select`, "POST", { hotel, go_home_without_hotel });
export const getDailyHotelSelections = (tripId: string) => request<Hotel[]>(`/hotels/trips/${tripId}/daily-selections`);
