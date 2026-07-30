"use client";

import { Share2, Trash2 } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { inputClass } from "@/components/ui/field";
import * as collaborationApi from "@/lib/api/collaboration";
import type { Collaborator } from "@/lib/api/types";

export function ShareTrip({ tripId, onError }: { tripId: string; onError: (error: unknown) => void }) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"viewer" | "editor">("viewer");
  const [people, setPeople] = useState<Collaborator[]>([]);
  const [busy, setBusy] = useState(false);

  async function show() {
    if (open) return setOpen(false);
    setOpen(true);
    try { setPeople(await collaborationApi.list(tripId)); } catch (error) { onError(error); }
  }

  return <section className="rounded-md border border-slate-200 bg-white p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="flex items-center gap-2 font-black text-slate-950"><Share2 className="h-4 w-4" /> Share trip</p><p className="text-sm text-slate-500">Give an existing MagicTripPlanner user view or edit access.</p></div><Button variant="ghost" onClick={() => void show()}>{open ? "Hide" : "Manage"}</Button></div>{open ? <div className="mt-4 grid gap-3"><div className="grid gap-2 sm:grid-cols-[1fr_130px_auto]"><input className={inputClass} type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="traveler@example.com" aria-label="Collaborator email" /><select className={inputClass} value={role} onChange={(event) => setRole(event.target.value as typeof role)} aria-label="Collaborator role"><option value="viewer">Can view</option><option value="editor">Can edit</option></select><Button disabled={busy || !email.includes("@")} onClick={async () => { setBusy(true); try { const person = await collaborationApi.invite(tripId, email.trim(), role); setPeople((items) => [...items.filter((item) => item.id !== person.id), person]); setEmail(""); } catch (error) { onError(error); } finally { setBusy(false); } }}>Add</Button></div>{people.map((person) => <div key={person.id} className="flex items-center justify-between rounded border border-slate-200 p-3 text-sm"><div><p className="font-bold text-slate-900">{person.name}</p><p className="text-xs text-slate-500">{person.email} · {person.role === "editor" ? "Can edit" : "View only"}</p></div><Button variant="ghost" aria-label={`Remove ${person.name}`} onClick={async () => { try { await collaborationApi.remove(tripId, person.id); setPeople((items) => items.filter((item) => item.id !== person.id)); } catch (error) { onError(error); } }}><Trash2 className="h-4 w-4 text-rose-600" /></Button></div>)}</div> : null}</section>;
}
