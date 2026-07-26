import { json, request } from "./client";
import type { Trip, TripToolkit, TripToolkitInput } from "./types";

export type TripInput = Omit<Trip, "id">;
export const createTrip = (body: TripInput) => json<Trip>("/trips/", "POST", body);
export const listTrips = () => request<Trip[]>("/trips/");
export const getTrip = (id: string) => request<Trip>(`/trips/${id}`);
export const deleteTrip = (id: string) => request<{ message: string }>(`/trips/${id}`, { method: "DELETE" });
export const getTripToolkit = (id: string) => request<TripToolkit>(`/trips/${id}/toolkit`);
export const updateTripToolkit = (id: string, body: TripToolkitInput) => json<TripToolkit>(`/trips/${id}/toolkit`, "PUT", body);
