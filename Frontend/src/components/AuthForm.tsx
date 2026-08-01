"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Check, Eye, EyeOff, Loader2, MapPin } from "lucide-react";
import Link from "next/link";
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
    <main className="grid min-h-screen place-items-center bg-[#f8f7f2] px-4 py-6 sm:px-6">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-[28px] border border-[#17453a]/10 bg-white shadow-[0_24px_80px_rgba(18,60,50,.12)] lg:grid-cols-[.88fr_1.12fr]">
        <aside className="relative hidden overflow-hidden bg-[#123c32] p-10 text-white lg:flex lg:flex-col lg:justify-between">
          <div className="absolute -right-20 top-10 h-64 w-64 rounded-full bg-[#e17742]/20 blur-3xl" />
          <div className="relative">
            <Link href="/" className="inline-flex items-center gap-2 text-sm font-bold text-[#dceae2]">
              <MapPin className="h-4 w-4 text-[#f4a16f]" /> Made for exploring Sri Lanka
            </Link>
            <h2 className="mt-16 font-[family-name:var(--font-display)] text-5xl leading-[1.05] tracking-[-0.03em]">
              A better trip starts with a calmer plan.
            </h2>
            <p className="mt-5 max-w-sm text-sm leading-7 text-[#c2d4cc]">Keep every place, stay, route, and cost in one clear itinerary you can revisit anytime.</p>
          </div>
          <ul className="relative mt-12 grid gap-3 text-sm font-semibold text-[#dceae2]">
            <li className="flex items-center gap-3"><Check className="h-4 w-4 text-[#f4a16f]" /> Day-by-day routes and timings</li>
            <li className="flex items-center gap-3"><Check className="h-4 w-4 text-[#f4a16f]" /> Stays matched to each travel day</li>
            <li className="flex items-center gap-3"><Check className="h-4 w-4 text-[#f4a16f]" /> Practical cost estimates in LKR</li>
          </ul>
        </aside>

        <section className="p-6 sm:p-10 lg:p-12">
          <LogoBrand />
          <form onSubmit={submit} className="mt-10">
            <p className="text-xs font-extrabold tracking-[0.14em] text-[#d56535]">{mode === "login" ? "WELCOME BACK" : "START PLANNING"}</p>
            <h1 className="mt-2 font-[family-name:var(--font-display)] text-4xl tracking-[-0.03em] text-[#123c32]">
              {mode === "login" ? "Your trips are waiting." : "Create your account."}
            </h1>
            <p className="mt-3 text-sm leading-6 text-[#60766f]">
              {mode === "login" ? "Sign in to continue planning where you left off." : "Save your itineraries and return to them from any device."}
            </p>
            <div className="mt-8 grid gap-5">
              {mode === "register" ? (
                <Field label="Your name">
                  <input className={inputClass} value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" placeholder="How should we greet you?" />
                </Field>
              ) : null}
              <Field label="Email address">
                <input className={inputClass} type="email" value={email} onChange={(event) => setEmail(event.target.value)} onKeyDown={submitOnEnter} autoComplete="email" placeholder="you@example.com" required />
              </Field>
              <Field label="Password">
                <div className="relative">
                  <input className={`${inputClass} pr-12`} type={showPassword ? "text" : "password"} value={password} onChange={(event) => setPassword(event.target.value)} onKeyDown={submitOnEnter} autoComplete={mode === "login" ? "current-password" : "new-password"} placeholder="Enter your password" required />
                  <button
                    type="button"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    className="absolute right-2 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-lg text-[#60766f] hover:bg-[#edf1ec]"
                    onClick={() => setShowPassword((value) => !value)}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </Field>
              <ApiErrorAlert error={error} />
              <Button className="w-full" disabled={busy} type="submit">
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {mode === "login" ? "Sign in to my trips" : "Create account"}
              </Button>
            </div>
          </form>
          <p className="mt-6 text-center text-sm text-[#60766f]">
            {mode === "login" ? "New to Magic Trip Planner? " : "Already have an account? "}
            <Link className="font-bold text-[#bf572e] hover:text-[#943e20]" href={mode === "login" ? "/register" : "/login"}>
              {mode === "login" ? "Create an account" : "Sign in"}
            </Link>
          </p>
        </section>
      </div>
    </main>
  );
}
