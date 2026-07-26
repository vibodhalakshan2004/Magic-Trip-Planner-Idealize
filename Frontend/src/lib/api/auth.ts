import { json, request } from "./client";
import type { TokenResponse, User } from "./types";

export const register = (body: { name: string; email: string; password: string }) =>
  json<{ message: string; user_id: string }>("/auth/register", "POST", body);

export async function login(email: string, password: string) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form,
  });
}

export const me = (token?: string) =>
  token ? request<User>("/auth/me", { headers: { Authorization: `Bearer ${token}` } }) : request<User>("/auth/me");
