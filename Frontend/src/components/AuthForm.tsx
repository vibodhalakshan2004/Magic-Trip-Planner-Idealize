"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { FormEvent, KeyboardEvent, useState } from "react";
import { ApiErrorAlert } from "@/components/ApiErrorAlert";
import { LogoBrand } from "@/components/LogoBrand";
import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";
import * as authApi from "@/lib/api/auth";
import { useAuthStore } from "@/lib/store/auth-store";
import { usePlannerStore } from "@/lib/store/planner-store";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const queryClient = useQueryClient();
  const setSession = useAuthStore((state) => state.setSession);
  const resetPlanner = usePlannerStore((state) => state.reset);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>();

  async function submit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    await submitCredentials();
  }

  async function submitCredentials() {
    if (busy) return;
    setError(undefined);

    if (!email.includes("@")) {
      setError(new Error("Enter a valid email address."));
      return;
    }

    if (!password) {
      setError(new Error("Enter your password."));
      return;
    }

    setBusy(true);
    try {
      if (mode === "register") {
        await authApi.register({ name: name.trim() || "Traveler", email: email.trim(), password });
      }

      await authApi.login(email.trim(), password);
      resetPlanner();
      queryClient.clear();
      const user = await authApi.me();
      setSession(user);
      window.location.href = "/dashboard";
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  function submitOnEnter(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    event.preventDefault();
    void submitCredentials();
  }

  return (
    <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-md place-items-center px-4">
      <form onSubmit={submit} className="w-full rounded-md border border-slate-200 bg-white p-6 shadow-sm">
        <LogoBrand />
        <h1 className="mt-8 text-2xl font-black text-slate-950">{mode === "login" ? "Welcome back" : "Create your planner account"}</h1>
        <p className="mt-2 text-sm text-slate-500">Plan Sri Lanka trips with smart places, stays, routes, and LKR budget clarity.</p>
        <div className="mt-6 grid gap-4">
          {mode === "register" ? (
            <Field label="Name">
              <input className={inputClass} value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" />
            </Field>
          ) : null}
          <Field label="Email">
            <input className={inputClass} type="email" value={email} onChange={(event) => setEmail(event.target.value)} onKeyDown={submitOnEnter} autoComplete="email" required />
          </Field>
          <Field label="Password">
            <div className="relative">
              <input className={`${inputClass} pr-12`} type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} onKeyDown={submitOnEnter} autoComplete={mode === "login" ? "current-password" : "new-password"} required />
              <button
                type="button"
                aria-label={showPassword ? "Hide password" : "Show password"}
                className="absolute right-2 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded text-slate-500 hover:bg-slate-100"
                onClick={() => setShowPassword((value) => !value)}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </Field>
          <ApiErrorAlert error={error} />
          <Button disabled={busy} type="button" onClick={() => void submitCredentials()}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}{mode === "login" ? "Log in" : "Register and continue"}</Button>
        </div>
      </form>
    </div>
  );
}
