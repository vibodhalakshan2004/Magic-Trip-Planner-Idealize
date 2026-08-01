import type { SavedPreferencePrompt } from "./types";

const CONFIGURED_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function apiBaseUrl() {
  if (typeof window === "undefined") return CONFIGURED_API_BASE_URL;

  const configured = new URL(CONFIGURED_API_BASE_URL);
  const loopbackHosts = new Set(["localhost", "127.0.0.1", "::1"]);

  if (loopbackHosts.has(configured.hostname) && loopbackHosts.has(window.location.hostname)) {
    configured.hostname = window.location.hostname;
  }

  return configured.origin;
}

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

let unauthorizedHandler: (() => void) | null = null;

export function configureApi(onUnauthorized?: () => void) {
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
  if (init.body && !headers.has("Content-Type") && !(init.body instanceof URLSearchParams)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${apiBaseUrl()}${path}`, { ...init, headers, credentials: "include" });
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
