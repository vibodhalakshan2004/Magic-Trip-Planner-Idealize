"use client";

import { Check, Clock, Hotel as HotelIcon, MapPin, Search, Star } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { inputClass } from "@/components/ui/field";
import type { Hotel, Place } from "@/lib/api/types";
import { fallbackImage, money } from "@/lib/utils/format";
import * as destinationApi from "@/lib/api/destination";
import * as hotelApi from "@/lib/api/hotels";

const IMAGE_PROXY_VERSION = "3";

export function SmartImage({ src, alt, kind, fallbackQuery, className = "h-48 w-full object-cover" }: { src?: string | null; alt: string; kind: "place" | "hotel"; fallbackQuery?: string; className?: string }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const imageSrc = useMemo(() => {
    const sourceKey = src ?? `lookup:${alt}`;
    // Hotel names are often ambiguous (for example, "Villa" can match a
    // person's name). Never use the generic Wikimedia search for hotel
    // imagery; show a neutral placeholder unless the hotel provider supplied
    // a property-linked image URL.
    if (failedSrc === sourceKey || (kind === "hotel" && !src)) return fallbackImage(alt, kind);
    const representativeQuery = fallbackQuery?.trim() || (kind === "hotel" ? "Sri Lanka architecture" : "Sri Lanka landscape");
    const sharedParams = `label=${encodeURIComponent(alt)}&fallbackQuery=${encodeURIComponent(representativeQuery)}&v=${IMAGE_PROXY_VERSION}`;
    if (src) return `/api/image?url=${encodeURIComponent(src)}&${sharedParams}`;
    return `/api/image?query=${encodeURIComponent(alt)}&${sharedParams}`;
  }, [alt, failedSrc, fallbackQuery, kind, src]);

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={imageSrc}
      alt={alt}
      loading="lazy"
      referrerPolicy="no-referrer"
      onError={() => setFailedSrc(src ?? `lookup:${alt}`)}
      className={className}
    />
  );
}

export function PlaceSuggestionCard({ place, selected, onToggle }: { place: Place; selected: boolean; onToggle: (place: Place) => void }) {
  const routable = hasMapCoordinates(place);
  return (
    <article className={`overflow-hidden rounded-2xl border bg-white shadow-[0_6px_24px_rgba(18,60,50,.05)] transition ${selected ? "border-[#4f8877] ring-4 ring-[#dbece2]" : "border-[#17453a]/10 hover:-translate-y-0.5 hover:border-[#17453a]/20"}`}>
      <SmartImage src={place.image_url} alt={place.name} kind="place" fallbackQuery={placePhotoFallbackQuery(place)} />
      <div className="grid gap-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-extrabold tracking-[-0.015em] text-[#173e34]">{place.name}</h3>
            <p className="mt-1 text-[11px] font-extrabold uppercase tracking-wider text-[#d56535]">{place.category}</p>
          </div>
          <span className="rounded-full bg-[#fdf0e8] px-2.5 py-1 text-xs font-bold text-[#9a4d2e]"><Star className="mr-1 inline h-3 w-3 fill-[#e17742] text-[#e17742]" />{place.priority_score ?? "Suggested"}</span>
        </div>
        <p className="line-clamp-3 min-h-14 text-sm text-slate-600">{place.short_description || place.reason_for_recommendation || "A Sri Lanka stop worth considering for this route."}</p>
        <div className="grid gap-1 text-xs text-slate-500">
          <span><Clock className="mr-1 inline h-3 w-3" />{place.best_time_to_visit || "Flexible"} · {place.estimated_visit_duration_hours ?? 1} hr</span>
          <span><MapPin className="mr-1 inline h-3 w-3" />{money(place.estimated_cost_lkr_per_person)} per person</span>
          <span className={routable ? "font-semibold text-emerald-700" : "font-semibold text-amber-700"}>
            {routable ? "Map location verified" : "Map location unavailable — add this place through search instead"}
          </span>
          {place.weather_summary ? <span>{place.weather_summary}</span> : null}
          {place.warnings?.length ? <span className="font-semibold text-amber-700">{place.warnings.join(", ")}</span> : null}
        </div>
        <Button className="w-full" type="button" disabled={!routable && !selected} variant={selected ? "secondary" : "primary"} onClick={() => onToggle(place)}>{selected ? <><Check className="h-4 w-4" /> Added to trip</> : routable ? "Add to trip" : "Use place search"}</Button>
      </div>
    </article>
  );
}

export function HotelSuggestionCard({ hotel, selected, onToggle }: { hotel: Hotel; selected: boolean; onToggle: (hotel: Hotel) => void }) {
  return (
    <article className={`overflow-hidden rounded-2xl border bg-white shadow-[0_6px_24px_rgba(18,60,50,.05)] transition ${selected ? "border-[#4f8877] ring-4 ring-[#dbece2]" : "border-[#17453a]/10 hover:-translate-y-0.5 hover:border-[#17453a]/20"}`}>
      <SmartImage src={hotel.image_url} alt={hotel.name} kind="hotel" />
      <div className="grid gap-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-black text-slate-950">{hotel.name}</h3>
            <p className="text-xs font-bold uppercase tracking-normal text-teal-700">{hotel.hotel_type} · {hotel.area || "Sri Lanka"}</p>
          </div>
          <span className="rounded-full bg-[#fdf0e8] px-2.5 py-1 text-xs font-bold text-[#9a4d2e]"><Star className="mr-1 inline h-3 w-3 fill-[#e17742] text-[#e17742]" />{hotel.rating_estimate ?? hotel.priority_score ?? "Suggested"}</span>
        </div>
        <p className="line-clamp-3 min-h-14 text-sm text-slate-600">{hotel.short_description || hotel.reason_for_recommendation || hotel.distance_summary || "Accommodation close to your selected places."}</p>
        <div className="grid gap-1 text-xs text-slate-500">
          <span><HotelIcon className="mr-1 inline h-3 w-3" />{hotel.nights ?? 1} nights · {hotel.rooms ?? 1} rooms</span>
          <span>{money(hotel.estimated_price_per_night_lkr)} / night · {money(hotel.total_estimated_price_lkr)} total</span>
          {hotel.distance_summary ? <span>{hotel.distance_summary}</span> : null}
          {hotel.amenities?.length ? <span>{hotel.amenities.slice(0, 4).join(", ")}</span> : null}
          {hotel.warnings?.length ? <span className="font-semibold text-amber-700">{hotel.warnings.join(", ")}</span> : null}
        </div>
        <Button className="w-full" type="button" variant={selected ? "secondary" : "primary"} onClick={() => onToggle(hotel)}>{selected ? <><Check className="h-4 w-4" /> Added for this day</> : "Choose this stay"}</Button>
      </div>
    </article>
  );
}

export function PlaceSearchCombobox({ tripId, onAdd }: { tripId: string; onAdd: (place: Place) => void }) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Place[]>([]);
  useEffect(() => {
    if (query.trim().length < 2) return;
    const timer = window.setTimeout(() => destinationApi.searchPlaces(tripId, query).then((r) => setItems(r.suggestions)).catch(() => setItems([])), 350);
    return () => window.clearTimeout(timer);
  }, [query, tripId]);
  const visibleItems = query.trim().length >= 2 ? uniqueBy(items.filter(hasMapCoordinates), (place) => `${place.place_key || ""}|${place.name}|${place.latitude ?? ""}|${place.longitude ?? ""}`) : [];
  return (
    <div className="rounded-2xl border border-[#17453a]/10 bg-[#f9faf7] p-4">
      <label className="relative block">
        <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
        <input className={`${inputClass} pl-9`} placeholder="Search custom places, 2+ characters" value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>
      <div className="mt-3 grid gap-2">
        {visibleItems.map((place, index) => (
          <button key={`${place.place_key || "place"}-${place.name}-${place.latitude ?? "x"}-${place.longitude ?? "y"}-${index}`} className="rounded-md border border-slate-200 p-3 text-left hover:bg-slate-50" type="button" onClick={() => onAdd(place)}>
            <b>{place.display_name || place.name}</b>
            <span className="block text-sm text-slate-500">{place.short_description || place.category}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function HotelSearchCombobox({ tripId, onAdd }: { tripId: string; onAdd: (hotel: Hotel) => void }) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Hotel[]>([]);
  useEffect(() => {
    if (query.trim().length < 2) return;
    const timer = window.setTimeout(() => hotelApi.searchHotels(tripId, query).then((r) => setItems(r.suggestions)).catch(() => setItems([])), 350);
    return () => window.clearTimeout(timer);
  }, [query, tripId]);
  const visibleItems = query.trim().length >= 2 ? uniqueBy(items, (hotel) => `${hotel.hotel_key || ""}|${hotel.name}|${hotel.latitude ?? ""}|${hotel.longitude ?? ""}`) : [];
  return (
    <div className="rounded-2xl border border-[#17453a]/10 bg-[#f9faf7] p-4">
      <label className="relative block">
        <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
        <input className={`${inputClass} pl-9`} placeholder="Search custom hotels, 2+ characters" value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>
      <div className="mt-3 grid gap-2">
        {visibleItems.map((hotel, index) => (
          <button key={`${hotel.hotel_key || "hotel"}-${hotel.name}-${hotel.latitude ?? "x"}-${hotel.longitude ?? "y"}-${index}`} className="rounded-md border border-slate-200 p-3 text-left hover:bg-slate-50" type="button" onClick={() => onAdd(hotel)}>
            <b>{hotel.name}</b>
            <span className="block text-sm text-slate-500">{hotel.short_description || hotel.area || hotel.hotel_type}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function uniqueBy<T>(items: T[], keyFor: (item: T) => string) {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = keyFor(item);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function hasMapCoordinates(place: Place) {
  return Number.isFinite(place.latitude) && Number.isFinite(place.longitude);
}

function placePhotoFallbackQuery(place: Place) {
  const text = `${place.name} ${place.category} ${place.short_description || ""}`.toLowerCase();
  const themes: Array<[RegExp, string]> = [
    [/\btea\b|plantation|estate/, "tea estate Sri Lanka"],
    [/beach|coast|bay|ocean|sea\b/, "beach Sri Lanka"],
    [/waterfall|\bfalls\b/, "waterfall Sri Lanka"],
    [/temple|vihara|kovil|mosque|church|shrine|buddha/, "temple Sri Lanka"],
    [/fort|heritage|historical|colonial/, "heritage site Sri Lanka"],
    [/sanctuary|forest|jungle|national park|wildlife/, "nature reserve Sri Lanka"],
    [/garden|botanical/, "botanical garden Sri Lanka"],
    [/lake|lagoon|river|reservoir/, "lake Sri Lanka"],
    [/mountain|hill|peak|viewpoint|rock/, "mountain landscape Sri Lanka"],
    [/museum|gallery/, "museum Sri Lanka"],
    [/lighthouse/, "lighthouse Sri Lanka"],
    [/market|shopping|bazaar/, "market Sri Lanka"],
    [/food|restaurant|cuisine/, "Sri Lankan cuisine"],
    [/culture|cultural/, "culture Sri Lanka"],
    [/adventure|hiking|surfing/, "outdoor travel Sri Lanka"],
  ];

  return themes.find(([pattern]) => pattern.test(text))?.[1] || "landscape Sri Lanka";
}

export function SelectedPlacesPanel({ places, onRemove }: { places: Place[]; onRemove: (key: string) => void }) {
  return <SelectedPanel title="Selected places" empty="Select at least one place to unlock hotels." items={places.map((p) => ({ key: p.place_key, label: p.name, detail: p.category }))} onRemove={onRemove} />;
}

export function SelectedHotelsPanel({ hotels, onRemove }: { hotels: Hotel[]; onRemove: (key: string) => void }) {
  return <SelectedPanel title="Selected hotels" empty="Select at least one hotel to unlock budget calculation." items={hotels.map((h) => ({ key: h.hotel_key, label: h.name, detail: h.hotel_type }))} onRemove={onRemove} />;
}

function SelectedPanel({ title, empty, items, onRemove }: { title: string; empty: string; items: { key: string; label: string; detail?: string }[]; onRemove: (key: string) => void }) {
  return (
    <div className="rounded-2xl border border-[#17453a]/10 bg-[#f9faf7] p-4">
      <h3 className="font-extrabold text-[#173e34]">{title}</h3>
      {!items.length ? <p className="mt-2 text-sm text-slate-500">{empty}</p> : null}
      <div className="mt-3 grid gap-2">
        {items.map((item) => (
          <div key={item.key} className="flex items-center justify-between gap-3 rounded-xl bg-white px-3 py-2.5">
            <span className="text-sm"><b>{item.label}</b><span className="block text-xs text-slate-500">{item.detail}</span></span>
            <button className="text-xs font-bold text-rose-600" type="button" onClick={() => onRemove(item.key)}>Remove</button>
          </div>
        ))}
      </div>
    </div>
  );
}
