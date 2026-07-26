import { ArrowRight, Bot, Map, WalletCards } from "lucide-react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";

export default function Home() {
  return (
    <AppShell>
      <section className="grid min-h-[calc(100vh-8rem)] items-center gap-10 py-8 lg:grid-cols-[1.05fr_.95fr]">
        <div>
          <p className="text-sm font-black uppercase tracking-normal text-emerald-700">Sri Lanka travel orchestration</p>
          <h1 className="mt-4 max-w-3xl text-4xl font-black tracking-normal text-slate-950 sm:text-6xl">Plan a complete Sri Lanka trip from first idea to final budget.</h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
            MagicTripPlanner brings destination ideas, hotel choices, route maps, turn-by-turn days, and LKR cost planning into one guided workflow.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href="/planner/new" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-emerald-600 px-5 py-3 text-sm font-bold text-white hover:bg-emerald-700">
              Start planning <ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/dashboard" className="inline-flex min-h-11 items-center justify-center rounded-md border border-slate-200 bg-white px-5 py-3 text-sm font-bold text-slate-900 hover:bg-slate-50">
              View dashboard
            </Link>
          </div>
        </div>
        <div className="rounded-md border border-slate-200 bg-white p-5 shadow-sm">
          <div className="aspect-[4/3] rounded-md bg-[linear-gradient(135deg,#ecfeff,#f8fafc_45%,#ecfdf5)] p-5">
            <div className="grid h-full grid-rows-[auto_1fr_auto]">
              <div className="flex items-center justify-between">
                <span className="rounded bg-white px-3 py-1 text-sm font-black text-slate-800 shadow-sm">Colombo to Ella</span>
                <Bot className="h-6 w-6 text-emerald-700" />
              </div>
              <div className="relative my-8">
                <div className="absolute left-[18%] top-[20%] h-4 w-4 rounded-full bg-emerald-600 ring-4 ring-white" />
                <div className="absolute left-[45%] top-[54%] h-4 w-4 rounded-full bg-blue-600 ring-4 ring-white" />
                <div className="absolute left-[74%] top-[28%] h-4 w-4 rounded-full bg-rose-600 ring-4 ring-white" />
                <svg className="h-full w-full" viewBox="0 0 500 260" role="img" aria-label="Route preview">
                  <path d="M70 65 C160 155 210 185 275 142 S390 20 440 78" fill="none" stroke="#059669" strokeWidth="8" strokeLinecap="round" strokeDasharray="18 12" />
                </svg>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <Feature icon={<Map />} label="Route days" />
                <Feature icon={<WalletCards />} label="LKR budget" />
                <Feature icon={<Bot />} label="AI picks" />
              </div>
            </div>
          </div>
        </div>
      </section>
    </AppShell>
  );
}

function Feature({ icon, label }: { icon: React.ReactNode; label: string }) {
  return <div className="rounded-md bg-white p-3 text-center text-sm font-bold text-slate-700 shadow-sm [&_svg]:mx-auto [&_svg]:mb-2 [&_svg]:h-5 [&_svg]:w-5 [&_svg]:text-emerald-700">{icon}{label}</div>;
}
