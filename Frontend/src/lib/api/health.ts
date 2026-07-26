import { request } from "./client";
import type { Health } from "./types";

export const health = () => request<Health>("/health");
