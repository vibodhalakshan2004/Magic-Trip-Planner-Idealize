import { json, request } from "./client";
import type { Budget } from "./types";

export const calculateBudget = (tripId: string, body: { food_cost_per_person_per_day_lkr: number; shopping_other_cost_lkr: number }) =>
  json<Budget>(`/budget/trips/${tripId}/calculate`, "POST", body);
export const getLatestBudget = (tripId: string) => request<Budget>(`/budget/trips/${tripId}/latest`);
