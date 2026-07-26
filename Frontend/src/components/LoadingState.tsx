import Image from "next/image";

export function LoadingState({ title = "Planning with a little magic", description = "We are coordinating routes, places, stays, and budget details." }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-4">
        <Image src="/logo.png" alt="MagicTripPlanner logo" width={48} height={48} className="h-12 w-12 animate-pulse rounded-md object-contain" />
        <div>
          <p className="font-bold text-slate-950">{title}</p>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
      </div>
      <div className="mt-5 grid gap-3">
        <div className="h-3 animate-pulse rounded bg-slate-100" />
        <div className="h-3 w-5/6 animate-pulse rounded bg-slate-100" />
        <div className="h-3 w-2/3 animate-pulse rounded bg-slate-100" />
      </div>
    </div>
  );
}
