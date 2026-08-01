import Image from "next/image";

export function LoadingState({ title = "Putting your plan together", description = "We’re coordinating routes, places, stays, and budget details." }) {
  return (
    <div className="rounded-2xl border border-[#17453a]/10 bg-white p-6 shadow-[0_8px_30px_rgba(18,60,50,.04)]" role="status" aria-live="polite">
      <div className="flex items-center gap-4">
        <Image src="/logo.png" alt="" width={48} height={48} className="h-12 w-12 animate-pulse rounded-xl object-contain" />
        <div>
          <p className="font-extrabold text-[#173e34]">{title}</p>
          <p className="mt-0.5 text-sm text-[#60766f]">{description}</p>
        </div>
      </div>
      <div className="mt-5 grid gap-3">
        <div className="h-2.5 animate-pulse rounded-full bg-[#e8eee9]" />
        <div className="h-2.5 w-5/6 animate-pulse rounded-full bg-[#e8eee9]" />
        <div className="h-2.5 w-2/3 animate-pulse rounded-full bg-[#e8eee9]" />
      </div>
    </div>
  );
}
