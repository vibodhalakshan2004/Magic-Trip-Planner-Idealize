import type { SavedPreferencePrompt } from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  preferencePrompt?: SavedPreferencePrompt;

  constructor(status: number, detail: unknown) {
    const message = typeof detail === "string" ? detail : "Request failed";
    super(message);
    this.status = status;
    this.detail = detail;
    if (status === 409 && detail && typeof detail === "object" && "has_saved_preferences" in detail) {
      this.preferencePrompt = detail as SavedPreferencePrompt;
    }
  }
}

let tokenGetter: (() => string | null) | null = null;
let unauthorizedHandler: (() => void) | null = null;

export function configureApi(getToken: () => string | null, onUnauthorized?: () => void) {
  tokenGetter = getToken;
  unauthorizedHandler = onUnauthorized ?? null;
}

async function parseResponse(response: Response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = tokenGetter?.();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type") && !(init.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  const payload = await parseResponse(response);
  if (!response.ok) {
    const detail = payload && typeof payload === "object" && "detail" in payload ? (payload as { detail: unknown }).detail : payload;
    if (response.status === 401) unauthorizedHandler?.();
    throw new ApiError(response.status, detail);
  }
  return payload as T;
}

export const json = <T>(path: string, method: string, body?: unknown) =>
  request<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
