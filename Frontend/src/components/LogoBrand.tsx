import Image from "next/image";
import Link from "next/link";

export function LogoBrand({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-3">
      <Image src="/logo.png" alt="MagicTripPlanner logo" width={44} height={44} className="h-11 w-11 rounded-md object-contain" priority />
      {!compact ? (
        <div className="leading-tight">
          <p className="text-base font-black tracking-normal text-slate-950">MagicTripPlanner</p>
          <p className="text-xs font-medium text-slate-500">Sri Lanka itinerary studio</p>
        </div>
      ) : null}
    </Link>
  );
}
