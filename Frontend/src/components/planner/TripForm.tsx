"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Compass, MapPinned } from "lucide-react";
import { useForm } from "react-hook-form";
import { useWatch } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";

const schema = z
  .object({
    start_location: z.string().min(2, "Start location must be at least 2 characters."),
    destination: z.string().min(2, "Destination must be at least 2 characters."),
    start_date: z.string().min(1, "Start date is required."),
    end_date: z.string().min(1, "End date is required."),
    budget_min: z.coerce.number().min(1000, "Budget min must be at least LKR 1,000."),
    budget_max: z.coerce.number().min(1000, "Budget max must be at least LKR 1,000."),
    travelers: z.coerce
      .number()
      .min(1, "At least 1 traveler required.")
      .max(20, "Maximum 20 travelers allowed."),
    transport_type: z.string().min(2, "Select a transport type."),
  })
  .refine((v) => v.start_date >= todayIso(), {
    path: ["start_date"],
    message: "Start date cannot be in the past.",
  })
  .refine((v) => v.end_date >= todayIso(), {
    path: ["end_date"],
    message: "End date cannot be in the past.",
  })
  .refine((v) => v.end_date >= v.start_date, {
    path: ["end_date"],
    message: "End date must be same day or after start date.",
  })
  .refine((v) => v.budget_max >= v.budget_min, {
    path: ["budget_max"],
    message: "Max budget must be greater than or equal to min budget.",
  });

export type TripFormValues = z.output<typeof schema>;

export function TripForm({ onSubmit }: { onSubmit: (values: TripFormValues) => Promise<void> }) {
  const form = useForm<z.input<typeof schema>, unknown, TripFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      start_location: "",
      destination: "",
      start_date: "",
      end_date: "",
      budget_min: undefined as unknown as number,
      budget_max: undefined as unknown as number,
      travelers: undefined as unknown as number,
      transport_type: "car",
    },
  });
  const startDate = useWatch({ control: form.control, name: "start_date" });

  return (
    <form className="grid gap-6" onSubmit={form.handleSubmit(onSubmit)}>
      <div className="rounded-2xl border border-[#cbded2] bg-[#eef4ef] p-4 sm:p-5">
        <p className="text-sm font-extrabold text-[#173e34]"><Compass className="mr-1.5 inline h-4 w-4 text-[#d56535]" />Need a quick start?</p>
        <p className="mt-1 text-xs leading-5 text-[#60766f]">Choose an example to fill the form, then adjust anything you like.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className="rounded-xl border border-[#17453a]/15 bg-white px-3 py-2.5 text-xs font-bold text-[#31574c] transition hover:border-[#17453a]/30 hover:bg-[#f9fbf8]" onClick={() => applyTemplate("highlands")}>3-day hill country</button>
          <button type="button" className="rounded-xl border border-[#17453a]/15 bg-white px-3 py-2.5 text-xs font-bold text-[#31574c] transition hover:border-[#17453a]/30 hover:bg-[#f9fbf8]" onClick={() => applyTemplate("culture")}>4-day cultural trip</button>
          <button type="button" className="rounded-xl border border-[#17453a]/15 bg-white px-3 py-2.5 text-xs font-bold text-[#31574c] transition hover:border-[#17453a]/30 hover:bg-[#f9fbf8]" onClick={() => applyTemplate("beach")}>Relaxed beach break</button>
        </div>
      </div>
      <div>
        <p className="mb-4 text-xs font-extrabold tracking-[0.12em] text-[#789087]">ROUTE & DATES</p>
        <div className="grid gap-4 md:grid-cols-2">
        <Field label="Start location" error={form.formState.errors.start_location?.message}>
          <input className={inputClass} placeholder="e.g. Colombo" {...form.register("start_location")} />
        </Field>
        <Field label="Destination" error={form.formState.errors.destination?.message}>
          <input className={inputClass} placeholder="e.g. Ella" {...form.register("destination")} />
        </Field>
        <Field label="Start date" error={form.formState.errors.start_date?.message}>
          <input
            className={inputClass}
            type="date"
            min={todayIso()}
            {...form.register("start_date")}
          />
        </Field>
        <Field label="End date" error={form.formState.errors.end_date?.message}>
          <input
            className={inputClass}
            type="date"
            min={startDate || todayIso()}
            {...form.register("end_date")}
          />
        </Field>
        </div>
      </div>
      <div>
        <p className="mb-4 text-xs font-extrabold tracking-[0.12em] text-[#789087]">BUDGET & TRAVEL STYLE</p>
        <div className="grid gap-4 md:grid-cols-2">
        <Field label="Budget min LKR" error={form.formState.errors.budget_min?.message}>
          <input
            className={inputClass}
            type="number"
            min={1000}
            step={1000}
            placeholder="50000"
            {...form.register("budget_min")}
          />
        </Field>
        <Field label="Budget max LKR" error={form.formState.errors.budget_max?.message}>
          <input
            className={inputClass}
            type="number"
            min={1000}
            step={1000}
            placeholder="150000"
            {...form.register("budget_max")}
          />
        </Field>
        <Field label="Travelers (1–20)" error={form.formState.errors.travelers?.message}>
          <input
            className={inputClass}
            type="number"
            min={1}
            max={20}
            placeholder="2"
            {...form.register("travelers")}
          />
        </Field>
        <Field label="Transport" error={form.formState.errors.transport_type?.message}>
          <select className={inputClass} {...form.register("transport_type")}>
            <option value="car">Car</option>
            <option value="bus">Bus</option>
            <option value="train">Train</option>
            <option value="taxi">Taxi</option>
            <option value="bike">Bike</option>
            <option value="walking">Walking</option>
            <option value="mixed">Mixed</option>
          </select>
        </Field>
        </div>
      </div>
      <Button className="w-full sm:w-auto sm:justify-self-end" disabled={form.formState.isSubmitting} type="submit">
        <MapPinned className="h-4 w-4" /> Create my trip
      </Button>
    </form>
  );

  function applyTemplate(kind: "highlands" | "culture" | "beach") {
    const start = addDaysIso(7);
    const templates = {
      highlands: { start_location: "Colombo", destination: "Ella", days: 3, budget_min: 60000, budget_max: 180000, travelers: 2, transport_type: "car" },
      culture: { start_location: "Colombo", destination: "Sigiriya", days: 4, budget_min: 80000, budget_max: 240000, travelers: 2, transport_type: "car" },
      beach: { start_location: "Colombo", destination: "Mirissa", days: 3, budget_min: 50000, budget_max: 160000, travelers: 2, transport_type: "mixed" },
    } as const;
    const template = templates[kind];
    form.reset({
      start_location: template.start_location,
      destination: template.destination,
      start_date: start,
      end_date: addDaysIso(6 + template.days),
      budget_min: template.budget_min,
      budget_max: template.budget_max,
      travelers: template.travelers,
      transport_type: template.transport_type,
    });
  }
}

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function addDaysIso(days: number) {
  const value = new Date();
  value.setDate(value.getDate() + days);
  return value.toISOString().slice(0, 10);
}
