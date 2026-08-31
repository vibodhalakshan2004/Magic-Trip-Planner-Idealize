import { json, request, requestBlob } from "./client";
import type { GoogleAuthConfig, TokenResponse, User } from "./types";

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

export const googleAuthConfig = () => request<GoogleAuthConfig>("/auth/google/config");
export const loginWithGoogle = (credential: string, csrfToken: string) =>
  json<TokenResponse>("/auth/google", "POST", { credential, csrf_token: csrfToken });

export const me = () => request<User>("/auth/me");
export const logout = () => request<{ message: string }>("/auth/logout", { method: "POST" });
export const updateProfile = (body: { name?: string; email?: string }) => json<User>("/auth/me", "PATCH", body);
export const updatePassword = (body: { current_password: string; new_password: string }) =>
  json<{ message: string }>("/auth/me/password", "PUT", body);
export const uploadProfilePicture = (picture: File) => {
  const form = new FormData();
  form.set("picture", picture);
  return request<User>("/auth/me/profile-picture", { method: "PUT", body: form });
};
export const deleteProfilePicture = () => request<User>("/auth/me/profile-picture", { method: "DELETE" });
export const profilePicture = (version: string) => requestBlob(`/auth/me/profile-picture?v=${encodeURIComponent(version)}`);
