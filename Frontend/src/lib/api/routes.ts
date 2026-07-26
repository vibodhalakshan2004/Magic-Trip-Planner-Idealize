import { json, request } from "./client";
import type { ManualRouteStop, RoutePlan } from "./types";

export const generateRoute = (tripId: string, body: { day_start_time: string; return_to_hotel?: boolean; return_to_start_location?: boolean; include_hotels?: boolean; manual_schedule?: ManualRouteStop[] }) =>
  json<RoutePlan>(`/routes/trips/${tripId}/generate`, "POST", body);
export const getLatestRoute = (tripId: string) => request<RoutePlan>(`/routes/trips/${tripId}/latest`);
export const confirmRoute = (tripId: string) => json<RoutePlan>(`/routes/trips/${tripId}/confirm`, "POST", {});
