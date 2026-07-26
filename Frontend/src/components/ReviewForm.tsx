"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Star } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Field, inputClass } from "@/components/ui/field";

const schema = z.object({
  place_name: z.string().min(2),
  place_type: z.string().min(2),
  rating: z.coerce.number().min(1).max(5),
  review_text: z.string().min(3),
  visit_date: z.string().min(1),
});

export type ReviewFormValues = z.output<typeof schema>;

export function ReviewForm({ onSubmit }: { onSubmit: (values: ReviewFormValues) => Promise<void> }) {
  const form = useForm<z.input<typeof schema>, unknown, ReviewFormValues>({ resolver: zodResolver(schema), defaultValues: { place_name: "", place_type: "attraction", rating: 5, review_text: "", visit_date: "2026-07-01" } });
  return (
    <form className="grid gap-4 rounded-md border border-slate-200 bg-white p-4" onSubmit={form.handleSubmit(onSubmit)}>
      <h2 className="text-xl font-black text-slate-950">Add a review</h2>
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Place name" error={form.formState.errors.place_name?.message}><input className={inputClass} {...form.register("place_name")} /></Field>
        <Field label="Place type" error={form.formState.errors.place_type?.message}><input className={inputClass} {...form.register("place_type")} /></Field>
        <Field label="Rating" error={form.formState.errors.rating?.message}><input className={inputClass} type="number" min={1} max={5} {...form.register("rating")} /></Field>
        <Field label="Visit date" error={form.formState.errors.visit_date?.message}><input className={inputClass} type="date" {...form.register("visit_date")} /></Field>
      </div>
      <Field label="Review" error={form.formState.errors.review_text?.message}><textarea className={`${inputClass} min-h-28`} {...form.register("review_text")} /></Field>
      <Button type="submit" disabled={form.formState.isSubmitting}><Star className="h-4 w-4" /> Save review</Button>
    </form>
  );
}
