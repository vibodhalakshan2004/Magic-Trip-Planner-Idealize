export function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export const lkr = new Intl.NumberFormat("en-LK", {
  style: "currency",
  currency: "LKR",
  maximumFractionDigits: 0,
});

export function money(value?: number | null) {
  return lkr.format(value ?? 0);
}

export function minutes(value?: number | null) {
  const total = value ?? 0;
  if (total < 60) return `${Math.round(total)} min`;
  const h = Math.floor(total / 60);
  const m = Math.round(total % 60);
  return m ? `${h} hr ${m} min` : `${h} hr`;
}

export function dayLabel(day?: number, date?: string, time?: string) {
  const formatted = date
    ? new Intl.DateTimeFormat("en-LK", { year: "numeric", month: "short", day: "2-digit" }).format(new Date(`${date}T00:00:00`))
    : "Date pending";
  return `Day ${day ?? 1} · ${formatted}${time ? ` · ${time}` : ""}`;
}

export function dateTime(value?: string | null) {
  if (!value) return "Not available";
  return new Intl.DateTimeFormat("en-LK", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function fallbackImage(label: string, kind: "place" | "hotel" | "empty" = "place") {
  const colors = kind === "hotel" ? ["#0f766e", "#f8fafc"] : kind === "empty" ? ["#334155", "#f8fafc"] : ["#1d4ed8", "#f8fafc"];
  const text = escapeSvgText(label || "MagicTripPlanner");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 520"><defs><pattern id="p" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M0 40H80M40 0V80" stroke="${colors[1]}" stroke-opacity=".18" stroke-width="2"/></pattern></defs><rect width="800" height="520" fill="${colors[0]}"/><rect width="800" height="520" fill="url(#p)"/><path d="M120 360C220 240 300 310 390 210s190-60 290 80v160H120z" fill="${colors[1]}" opacity=".22"/><circle cx="610" cy="120" r="46" fill="${colors[1]}" opacity=".3"/><text x="56" y="88" fill="${colors[1]}" font-family="Arial" font-size="42" font-weight="700">${text}</text></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function escapeSvgText(value: string) {
  return value.replace(/[<>&'\"]/g, (character) => ({
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    "'": "&apos;",
    "\"": "&quot;",
  })[character] ?? character);
}
