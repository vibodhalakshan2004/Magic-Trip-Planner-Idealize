"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2, Save } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";

const schema = z.object({
  travel_style: z.string().min(2),
  food_preference: z.string().min(2),
  interests: z.string().min(2),
  preferred_transport: z.string().min(2),
  preferred_hotel_type: z.string().min(2),
  budget_min: z.coerce.number().min(0),
  budget_max: z.coerce.number().min(0),
}).refine((v) => v.budget_max >= v.budget_min, { path: ["budget_max"], message: "Max budget must be greater than or equal to min." });

type PreferenceInput = z.input<typeof schema>;
type PreferenceOutput = z.output<typeof schema>;

export function PreferenceForm({ onSubmit }: { onSubmit: (values: PreferenceOutput) => Promise<void> }) {
  const form = useForm<PreferenceInput, unknown, PreferenceOutput>({
    resolver: zodResolver(schema),
    defaultValues: { travel_style: "balanced", food_preference: "local", interests: "nature, hiking, photography", preferred_transport: "car", preferred_hotel_type: "hotel", budget_min: 50000, budget_max: 150000 },
  });
  return (
    <form className="grid gap-4" onSubmit={form.handleSubmit(onSubmit)}>
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Travel style" error={form.formState.errors.travel_style?.message}><input className={inputClass} {...form.register("travel_style")} /></Field>
        <Field label="Food preference" error={form.formState.errors.food_preference?.message}><input className={inputClass} {...form.register("food_preference")} /></Field>
        <Field label="Interests" error={form.formState.errors.interests?.message}><input className={inputClass} {...form.register("interests")} /></Field>
        <Field label="Preferred transport" error={form.formState.errors.preferred_transport?.message}><select className={inputClass} {...form.register("preferred_transport")}><option>car</option><option>bus</option><option>train</option><option>taxi</option><option>bike</option><option>walking</option><option>mixed</option></select></Field>
        <Field label="Hotel type" error={form.formState.errors.preferred_hotel_type?.message}><select className={inputClass} {...form.register("preferred_hotel_type")}><option>hotel</option><option>guest_house</option><option>villa</option><option>resort</option><option>hostel</option><option>homestay</option><option>apartment</option><option>any</option></select></Field>
        <Field label="Budget min LKR" error={form.formState.errors.budget_min?.message}><input className={inputClass} type="number" {...form.register("budget_min")} /></Field>
        <Field label="Budget max LKR" error={form.formState.errors.budget_max?.message}><input className={inputClass} type="number" {...form.register("budget_max")} /></Field>
      </div>
      <Button disabled={form.formState.isSubmitting} type="submit">{form.formState.isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Save preferences</Button>
    </form>
  );
}
