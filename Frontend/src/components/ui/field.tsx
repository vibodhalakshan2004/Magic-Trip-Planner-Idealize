import { cn } from "@/lib/utils/format";

export function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-2 text-sm font-semibold text-[#314f47]">
      <span>{label}</span>
      {children}
      {error ? <span className="text-xs font-semibold text-[#a44535]">{error}</span> : null}
    </label>
  );
}

export const inputClass = cn(
  "min-h-12 w-full rounded-xl border border-[#17453a]/15 bg-white px-3.5 py-2.5 text-sm text-[#173e34] shadow-[0_1px_2px_rgba(18,60,50,.03)] outline-none transition",
  "placeholder:text-[#8ca098] hover:border-[#17453a]/25 focus:border-[#2c7765] focus:ring-4 focus:ring-[#d9ebe1]",
);
