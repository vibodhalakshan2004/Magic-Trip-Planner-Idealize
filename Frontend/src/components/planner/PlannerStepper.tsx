import { CheckCircle2, Circle, Lock } from "lucide-react";
import { cn } from "@/lib/utils/format";

export type PlannerStep = { id: string; label: string; reason?: string; complete?: boolean; disabled?: boolean };

export function PlannerStepper({ steps, active, onSelect }: { steps: readonly PlannerStep[]; active: string; onSelect: (id: string) => void }) {
  return (
    <aside className="rounded-md border border-slate-200 bg-white p-3 shadow-sm lg:sticky lg:top-24">
      <div className="flex gap-2 overflow-x-auto lg:grid">
        {steps.map((step) => {
          const isActive = step.id === active;
          return (
            <button
              key={step.id}
              type="button"
              disabled={step.disabled}
              onClick={() => onSelect(step.id)}
              title={step.reason}
              className={cn(
                "flex min-w-48 items-center gap-3 rounded-md px-3 py-3 text-left text-sm transition",
                isActive ? "bg-emerald-50 text-emerald-900 ring-1 ring-emerald-200" : "text-slate-700 hover:bg-slate-50",
                step.disabled && "cursor-not-allowed opacity-55",
              )}
            >
              {step.disabled ? <Lock className="h-4 w-4" /> : step.complete ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <Circle className="h-4 w-4" />}
              <span>
                <span className="block font-bold">{step.label}</span>
                {step.reason ? <span className="block text-xs text-slate-500">{step.reason}</span> : null}
              </span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
