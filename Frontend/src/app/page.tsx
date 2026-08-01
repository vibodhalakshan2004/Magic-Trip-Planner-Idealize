import {
  ArrowRight,
  CalendarDays,
  Check,
  Clock3,
  Hotel,
  MapPin,
  Navigation,
  Route,
  Sparkles,
  WalletCards,
} from "lucide-react";
import Link from "next/link";
import { AppShell } from "@/components/AppShell";

const steps = [
  {
    number: "01",
    title: "Set the shape of your trip",
    copy: "Tell us where you’re starting, where you want to go, your dates, budget, and pace.",
  },
  {
    number: "02",
    title: "Choose what feels right",
    copy: "Compare thoughtful place and stay suggestions, then keep only the ones that suit you.",
  },
  {
    number: "03",
    title: "Leave with a usable plan",
    copy: "Get a day-by-day route, practical timings, hotel stops, and a clear LKR estimate.",
  },
] as const;

export default function Home() {
  return (
    <AppShell>
      <section className="relative overflow-hidden rounded-[28px] bg-[#123c32] px-5 py-10 text-white sm:px-10 sm:py-14 lg:px-14 lg:py-16">
        <div className="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-[#e17742]/20 blur-3xl" />
        <div className="absolute -bottom-24 left-1/3 h-64 w-64 rounded-full bg-[#84ad9a]/15 blur-3xl" />
        <div className="relative grid items-center gap-12 lg:grid-cols-[.92fr_1.08fr]">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/8 px-3 py-1.5 text-xs font-bold tracking-wide text-[#dceae2]">
              <Sparkles className="h-3.5 w-3.5 text-[#f4a16f]" /> YOUR SRI LANKA TRIP, SORTED
            </p>
            <h1 className="mt-6 max-w-2xl font-[family-name:var(--font-display)] text-5xl leading-[1.02] tracking-[-0.035em] text-white sm:text-6xl lg:text-7xl">
              Less planning.
              <br />
              More going.
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-[#cbdcd4] sm:text-lg">
              Build a Sri Lanka itinerary that works in the real world—with places you’ll love, sensible routes, stays for each day, and costs in LKR.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/planner/new" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#e17742] px-5 text-sm font-bold text-white shadow-[0_12px_30px_rgba(6,25,20,.22)] transition hover:-translate-y-0.5 hover:bg-[#ce6836]">
                Plan my trip <ArrowRight className="h-4 w-4" />
              </Link>
              <Link href="/dashboard" className="inline-flex min-h-12 items-center justify-center rounded-xl border border-white/20 bg-white/8 px-5 text-sm font-bold text-white transition hover:bg-white/14">
                See my saved trips
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-xs font-semibold text-[#adc5ba]">
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#f4a16f]" /> Built around your budget</span>
              <span className="inline-flex items-center gap-1.5"><Check className="h-3.5 w-3.5 text-[#f4a16f]" /> Easy to change as you go</span>
            </div>
          </div>

          <TripPreview />
        </div>
      </section>

      <section className="grid gap-8 py-14 lg:grid-cols-[.75fr_1.25fr] lg:py-20">
        <div>
          <p className="text-xs font-extrabold tracking-[0.16em] text-[#d56535]">HOW IT WORKS</p>
          <h2 className="mt-3 max-w-md font-[family-name:var(--font-display)] text-4xl leading-tight tracking-[-0.025em] text-[#123c32] sm:text-5xl">
            A clear route from idea to itinerary.
          </h2>
        </div>
        <div className="grid gap-px overflow-hidden rounded-2xl border border-[#17453a]/10 bg-[#17453a]/10 md:grid-cols-3">
          {steps.map((step) => (
            <article key={step.number} className="bg-[#fffefa] p-6 lg:p-7">
              <span className="font-mono text-xs font-bold text-[#d56535]">{step.number}</span>
              <h3 className="mt-8 text-lg font-extrabold tracking-[-0.02em] text-[#173e34]">{step.title}</h3>
              <p className="mt-3 text-sm leading-6 text-[#60766f]">{step.copy}</p>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}

function TripPreview() {
  return (
    <div className="relative mx-auto w-full max-w-[620px] lg:ml-auto">
      <div className="rounded-[24px] border border-white/15 bg-[#f8f7f2] p-4 text-[#173e34] shadow-[0_28px_70px_rgba(4,22,17,.28)] sm:p-5">
        <div className="flex items-center justify-between gap-4 border-b border-[#17453a]/10 pb-4">
          <div>
            <p className="text-xs font-bold text-[#789087]">6-DAY ROAD TRIP</p>
            <h2 className="mt-1 text-lg font-extrabold tracking-[-0.02em]">Colombo → Ella</h2>
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#e6efe9] text-[#17453a]">
            <Navigation className="h-4 w-4" />
          </div>
        </div>
        <div className="grid gap-4 pt-4 sm:grid-cols-[1.15fr_.85fr]">
          <div className="rounded-2xl bg-[#e7eee8] p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold text-[#365b50]">DAY 3 · HILL COUNTRY</span>
              <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-bold text-[#537068]">3 stops</span>
            </div>
            <div className="relative mt-5 grid gap-4 pl-7 before:absolute before:bottom-4 before:left-[7px] before:top-3 before:w-px before:bg-[#9cb6aa]">
              <PreviewStop time="08:30" title="Nine Arches Bridge" />
              <PreviewStop time="11:15" title="Little Adam’s Peak" active />
              <PreviewStop time="14:00" title="Ella town & lunch" />
            </div>
            <div className="mt-5 flex gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-white px-2.5 py-2 text-xs font-bold"><Route className="h-3.5 w-3.5 text-[#d56535]" /> 18 km</span>
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-white px-2.5 py-2 text-xs font-bold"><Clock3 className="h-3.5 w-3.5 text-[#d56535]" /> 7h 30m</span>
            </div>
          </div>
          <div className="grid gap-3">
            <PreviewStat icon={<Hotel />} label="Tonight" value="Ella Gap Hotel" />
            <PreviewStat icon={<WalletCards />} label="Estimated total" value="LKR 148,500" />
            <PreviewStat icon={<CalendarDays />} label="Travel dates" value="12–17 August" />
          </div>
        </div>
      </div>
      <div className="absolute -bottom-5 -left-3 hidden items-center gap-3 rounded-2xl bg-white px-4 py-3 text-[#173e34] shadow-[0_14px_32px_rgba(5,27,21,.2)] sm:flex">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#fce8dc] text-[#d56535]"><MapPin className="h-4 w-4" /></span>
        <span><b className="block text-sm">Route ready</b><span className="text-xs text-[#789087]">All stops fit your pace</span></span>
      </div>
    </div>
  );
}

function PreviewStop({ time, title, active = false }: { time: string; title: string; active?: boolean }) {
  return (
    <div className="relative">
      <span className={`absolute -left-7 top-1 h-[15px] w-[15px] rounded-full border-[3px] ${active ? "border-[#d56535] bg-[#fbe2d5]" : "border-[#5f8b7b] bg-white"}`} />
      <p className="text-[11px] font-bold text-[#789087]">{time}</p>
      <p className="text-sm font-extrabold">{title}</p>
    </div>
  );
}

function PreviewStat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-[#17453a]/10 bg-white p-3.5">
      <span className="text-[#d56535] [&_svg]:h-4 [&_svg]:w-4">{icon}</span>
      <p className="mt-3 text-[11px] font-bold text-[#789087]">{label}</p>
      <p className="mt-0.5 text-sm font-extrabold tracking-[-0.01em]">{value}</p>
    </div>
  );
}
