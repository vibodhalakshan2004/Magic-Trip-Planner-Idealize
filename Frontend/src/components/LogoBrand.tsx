import Image from "next/image";
import Link from "next/link";

export function LogoBrand({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2.5 rounded-lg focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#d5e8dc]">
      <Image src="/logo.png" alt="" width={42} height={42} className="h-10 w-10 rounded-xl object-contain" priority />
      {!compact ? (
        <div className="leading-tight">
          <p className="text-[15px] font-extrabold tracking-[-0.02em] text-[#123c32]">Magic Trip Planner</p>
          <p className="text-[11px] font-semibold tracking-wide text-[#789087]">MADE FOR SRI LANKA</p>
        </div>
      ) : null}
    </Link>
  );
}
