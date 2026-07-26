"use client";

import Image from "next/image";
import type { SavedPreferencePrompt } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { money } from "@/lib/utils/format";

export function SavedPreferenceDecisionModal({ prompt, onChoose, onClose }: { prompt: SavedPreferencePrompt | null; onChoose: (useSaved: boolean) => void; onClose: () => void }) {
  if (!prompt) return null;
  const pref = prompt.saved_preferences;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4">
      <div className="w-full max-w-lg rounded-md bg-white p-6 shadow-xl">
        <div className="flex items-center gap-3">
          <Image src="/logo.png" alt="MagicTripPlanner logo" width={44} height={44} className="rounded-md" />
          <div>
            <h2 className="text-xl font-black text-slate-950">Use saved preferences?</h2>
            <p className="text-sm text-slate-500">{prompt.message}</p>
          </div>
        </div>
        {pref ? (
          <div className="mt-5 grid gap-2 rounded-md bg-slate-50 p-4 text-sm text-slate-700">
            <p><b>Style:</b> {pref.travel_style} · <b>Food:</b> {pref.food_preference}</p>
            <p><b>Transport:</b> {pref.preferred_transport} · <b>Hotel:</b> {pref.preferred_hotel_type}</p>
            <p><b>Interests:</b> {pref.interests?.join(", ") || "Not set"}</p>
            <p><b>Budget:</b> {money(pref.budget_min)} - {money(pref.budget_max)}</p>
          </div>
        ) : null}
        <div className="mt-6 flex flex-col gap-2 sm:flex-row">
          <Button onClick={() => onChoose(true)}>Use saved preferences</Button>
          <Button variant="secondary" onClick={() => onChoose(false)}>Use fresh inputs</Button>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
        </div>
      </div>
    </div>
  );
}
