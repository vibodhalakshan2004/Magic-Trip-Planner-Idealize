import { Check, ChevronRight, Lock } from "lucide-react";
import { cn } from "@/lib/utils/format";

export type PlannerStep = { id: string; label: string; reason?: string; complete?: boolean; disabled?: boolean };

export function PlannerStepper({ steps, active, onSelect }: { steps: readonly PlannerStep[]; active: string; onSelect: (id: string) => void }) {
  const completed = steps.filter((step) => step.complete).length;
  const currentIndex = Math.max(steps.findIndex((step) => step.id === active), 0);

  return (
    <aside className="min-w-0 max-w-full lg:sticky lg:top-24 lg:self-start">
      <div className="mb-3 flex items-end justify-between px-1">
        <div>
          <p className="text-xs font-extrabold tracking-[0.13em] text-[#789087]">TRIP PROGRESS</p>
          <p className="mt-1 text-sm font-bold text-[#173e34]">Step {currentIndex + 1} of {steps.length}</p>
        </div>
        <span className="text-xs font-bold text-[#60766f]">{completed} complete</span>
      </div>
      <div className="mb-4 h-1.5 overflow-hidden rounded-full bg-[#dfe7e1]">
        <div className="h-full rounded-full bg-[#d56535] transition-all" style={{ width: `${Math.max(((currentIndex + 1) / steps.length) * 100, 4)}%` }} />
      </div>
      <div className="flex w-full max-w-full gap-2 overflow-x-auto pb-2 lg:grid lg:overflow-visible lg:rounded-2xl lg:border lg:border-[#17453a]/10 lg:bg-white lg:p-2 lg:shadow-[0_8px_30px_rgba(18,60,50,.04)]">
        {steps.map((step, index) => {
          const isActive = step.id === active;
          return (
            <button
              key={step.id}
              type="button"
              disabled={step.disabled}
              onClick={() => onSelect(step.id)}
              title={step.reason}
              aria-current={isActive ? "step" : undefined}
              className={cn(
                "group flex min-w-52 items-center gap-3 rounded-xl border border-[#17453a]/10 bg-white px-3 py-3 text-left text-sm transition lg:min-w-0 lg:border-transparent",
                isActive ? "border-[#b8d0c3] bg-[#e7efe9] text-[#123c32] lg:border-[#cfe0d6]" : "text-[#526b63] hover:bg-[#f4f6f2]",
                step.disabled && "cursor-not-allowed opacity-50",
              )}
            >
              <span className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-extrabold",
                step.complete ? "bg-[#17453a] text-white" : isActive ? "bg-[#d56535] text-white" : "bg-[#edf1ec] text-[#60766f]",
              )}>
                {step.disabled ? <Lock className="h-3.5 w-3.5" /> : step.complete ? <Check className="h-4 w-4" /> : index + 1}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-bold">{step.label}</span>
                {step.reason ? <span className="mt-0.5 block truncate text-[11px] text-[#789087]">{step.reason}</span> : null}
              </span>
              {!step.disabled ? <ChevronRight className="hidden h-4 w-4 shrink-0 text-[#9cafA7] lg:block" /> : null}
            </button>
          );
        })}
      </div>
    </aside>
  );
}
