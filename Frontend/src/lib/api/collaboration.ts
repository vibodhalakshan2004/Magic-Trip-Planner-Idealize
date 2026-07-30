import { json, request } from "./client";
import type { Collaborator } from "./types";

export const list = (tripId: string) => request<Collaborator[]>(`/collaboration/trips/${tripId}`);
export const invite = (tripId: string, email: string, role: "viewer" | "editor") =>
  json<Collaborator>(`/collaboration/trips/${tripId}`, "POST", { email, role });
export const remove = (tripId: string, collaborationId: string) =>
  request<void>(`/collaboration/trips/${tripId}/${collaborationId}`, { method: "DELETE" });

