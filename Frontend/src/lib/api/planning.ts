import { json, request } from "./client";
import type { PlanningJob, TripVersion } from "./types";

export type FullPlanOptions = {
  use_saved_preferences: boolean;
  interests: string[];
  trip_style: "relaxed" | "balanced" | "packed";
  special_notes: string;
  max_places: number;
  hotel_type: string;
  hotel_preference: string;
  rooms: number;
  food_cost_per_person_per_day_lkr: number;
  shopping_other_cost_lkr: number;
};

export const createJob = (tripId: string, body: FullPlanOptions, idempotencyKey: string) =>
  request<PlanningJob>(`/planning/trips/${tripId}/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
    body: JSON.stringify(body),
  });
export const getJob = (jobId: string) => request<PlanningJob>(`/planning/jobs/${jobId}`);
export const cancelJob = (jobId: string) => request<PlanningJob>(`/planning/jobs/${jobId}/cancel`, { method: "POST" });
export const createVersion = (tripId: string, label: string) => json<TripVersion>(`/planning/trips/${tripId}/versions`, "POST", { label });
export const listVersions = (tripId: string) => request<TripVersion[]>(`/planning/trips/${tripId}/versions`);
export const restoreVersion = (tripId: string, versionId: string) => request<TripVersion>(`/planning/trips/${tripId}/versions/${versionId}/restore`, { method: "POST" });

