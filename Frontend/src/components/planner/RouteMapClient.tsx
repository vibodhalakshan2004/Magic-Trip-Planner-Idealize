"use client";

import L from "leaflet";
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import type { Hotel, RouteDay, RouteStop } from "@/lib/api/types";
import { minutes } from "@/lib/utils/format";

/* ── Custom marker icons ──────────────────────────────────────────── */
function makePlaceIcon(color: string, dayNum: number) {
  return L.divIcon({
    className: "",
    html: `
      <div style="
        position:relative;
        display:flex;
        flex-direction:column;
        align-items:center;
      ">
        <div style="
          width:28px;height:28px;border-radius:50% 50% 50% 0;
          background:${color};border:3px solid white;
          box-shadow:0 2px 8px rgba(15,23,42,.4);
          transform:rotate(-45deg);display:flex;align-items:center;justify-content:center;
        ">
          <span style="
            transform:rotate(45deg);font-size:10px;font-weight:800;
            color:white;line-height:1;
          ">${dayNum}</span>
        </div>
      </div>`,
    iconSize: [28, 36],
    iconAnchor: [14, 36],
    popupAnchor: [0, -38],
  });
}

function makeHotelIcon() {
  return L.divIcon({
    className: "",
    html: `
      <div style="
        width:30px;height:30px;border-radius:6px;
        background:#059669;border:3px solid white;
        box-shadow:0 2px 8px rgba(15,23,42,.4);
        display:flex;align-items:center;justify-content:center;
      ">
        <svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'>
          <path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/>
          <polyline points='9 22 9 12 15 12 15 22'/>
        </svg>
      </div>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -18],
  });
}

const dayColors = ["#2563eb", "#dc2626", "#7c3aed", "#ea580c", "#0891b2", "#4f46e5"];
const hotelIconInstance = makeHotelIcon();

function FocusMarker({ stop }: { stop: RouteStop | null }) {
  const map = useMap();
  if (stop?.latitude && stop.longitude) map.flyTo([stop.latitude, stop.longitude], 14, { duration: 0.8 });
  return null;
}

export default function RouteMapClient({
  days,
  hotels,
  activeStop,
  onSelectStop,
}: {
  days: RouteDay[];
  hotels: Hotel[];
  activeStop: RouteStop | null;
  onSelectStop: (stop: RouteStop) => void;
}) {
  const allStops = days.flatMap((day) => (day.stops || []).map((s) => ({ ...s, dayNumber: day.day_number })));
  const validStops = allStops.filter((s) => s.latitude && s.longitude);
  const center: [number, number] =
    validStops[0]?.latitude && validStops[0]?.longitude
      ? [validStops[0].latitude, validStops[0].longitude]
      : [7.8731, 80.7718];

  return (
    <MapContainer center={center} zoom={validStops.length ? 10 : 7} className="h-[520px] w-full rounded-md" scrollWheelZoom>
      <TileLayer
        attribution="&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FocusMarker stop={activeStop} />

      {/* Route polylines per day */}
      {days.map((day, index) => {
        const path =
          day.day_path_coordinates?.length
            ? day.day_path_coordinates
            : day.segments.flatMap((s) => s.path_coordinates || []);
        return path.length ? (
          <Polyline
            key={day.day_number}
            pathOptions={{ color: dayColors[index % dayColors.length], weight: 5, opacity: 0.85 }}
            positions={path.map((p) => [p.latitude, p.longitude])}
          />
        ) : null;
      })}

      {/* Place markers with day number & rich popup */}
      {validStops.map((stop, index) => {
        const dayIdx = (stop.dayNumber ?? 1) - 1;
        const color = dayColors[dayIdx % dayColors.length];
        const isActive = activeStop?.name === stop.name;
        const icon = makePlaceIcon(isActive ? "#f59e0b" : color, stop.dayNumber ?? 1);
        return (
          <Marker
            key={`place-${stop.name}-${index}`}
            position={[stop.latitude!, stop.longitude!]}
            icon={icon}
            eventHandlers={{ click: () => onSelectStop(stop) }}
          >
            <Popup maxWidth={260} className="route-popup">
              <div className="min-w-[220px] p-1">
                <p className="text-sm font-black text-slate-900">{stop.name}</p>
                <p className="mt-0.5 text-xs font-semibold text-blue-600">
                  📍 Day {stop.dayNumber} — {stop.category || "Attraction"}
                </p>
                <div className="mt-2 grid gap-1 text-xs text-slate-600">
                  {stop.arrival_time && (
                    <p>🕐 Arrive: <b>{stop.arrival_time}</b></p>
                  )}
                  {(stop.start_time || stop.arrival_time) && stop.end_time && (
                    <p>🕕 Depart: <b>{stop.end_time}</b></p>
                  )}
                  {stop.visit_duration_hours && (
                    <p>⏱ Stay: <b>{stop.visit_duration_hours}h</b></p>
                  )}
                  {stop.travel_time_from_previous_minutes && (
                    <p>🚗 Travel from prev: <b>{minutes(stop.travel_time_from_previous_minutes)}</b></p>
                  )}
                  {stop.travel_distance_from_previous_km && (
                    <p>📏 Distance: <b>{stop.travel_distance_from_previous_km} km</b></p>
                  )}
                  {stop.best_time_to_visit && (
                    <p>🌤 Best time: <b>{stop.best_time_to_visit}</b></p>
                  )}
                </div>
              </div>
            </Popup>
          </Marker>
        );
      })}

      {/* Hotel markers */}
      {hotels
        .filter((h) => h.latitude && h.longitude)
        .map((hotel) => (
          <Marker
            key={hotel.hotel_key || hotel.name}
            position={[hotel.latitude!, hotel.longitude!]}
            icon={hotelIconInstance}
          >
            <Popup maxWidth={240}>
              <div className="min-w-[200px] p-1">
                <p className="text-sm font-black text-slate-900">{hotel.name}</p>
                <p className="mt-0.5 text-xs font-semibold text-emerald-600">🏨 Hotel / Stay</p>
                <div className="mt-2 grid gap-1 text-xs text-slate-600">
                  {hotel.hotel_type && <p>🏷 Type: <b>{hotel.hotel_type}</b></p>}
                  {hotel.check_in_date && <p>📅 Check-in: <b>{hotel.check_in_date}</b></p>}
                  {hotel.check_out_date && <p>📅 Check-out: <b>{hotel.check_out_date}</b></p>}
                  {hotel.nights && <p>🌙 Nights: <b>{hotel.nights}</b></p>}
                  {hotel.estimated_price_per_night_lkr ? (
                    <p>💰 Per night: <b>LKR {hotel.estimated_price_per_night_lkr.toLocaleString()}</b></p>
                  ) : null}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

      {/* Map legend */}
      <div className="leaflet-bottom leaflet-left">
        <div className="m-3 rounded-lg bg-white/95 px-3 py-2.5 shadow-md backdrop-blur text-xs font-semibold text-slate-700 space-y-1.5">
          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-2">Legend</p>
          {days.map((day, i) => (
            <p key={day.day_number} className="flex items-center gap-2">
              <span
                className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[9px] font-black text-white"
                style={{ background: dayColors[i % dayColors.length] }}
              >
                {day.day_number}
              </span>
              Day {day.day_number} places
            </p>
          ))}
          <p className="flex items-center gap-2 border-t border-slate-100 pt-1.5 mt-1.5">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded bg-emerald-600">
              <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
            </span>
            Hotel / Stay
          </p>
        </div>
      </div>
    </MapContainer>
  );
}
