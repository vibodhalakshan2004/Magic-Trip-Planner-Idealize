"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import type { Hotel, RouteDay, RouteStop } from "@/lib/api/types";

const ClientMap = dynamic(() => import("./RouteMapClient"), { ssr: false, loading: () => <div className="grid h-[460px] place-items-center rounded-md bg-slate-100 text-sm font-semibold text-slate-500">Loading OpenStreetMap...</div> });

export function RouteMap({ days, hotels, activeStop, onSelectStop }: { days: RouteDay[]; hotels: Hotel[]; activeStop: RouteStop | null; onSelectStop: (stop: RouteStop) => void }) {
  const [ready] = useState(true);
  if (!ready) return null;
  return <ClientMap days={days} hotels={hotels} activeStop={activeStop} onSelectStop={onSelectStop} />;
}
