"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Send, Star } from "lucide-react";
import { useForm, useWatch } from "react-hook-form";
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
  const form = useForm<z.input<typeof schema>, unknown, ReviewFormValues>({ resolver: zodResolver(schema), defaultValues: { place_name: "", place_type: "attraction", rating: 5, review_text: "", visit_date: new Date().toISOString().slice(0, 10) } });
  const rating = Number(useWatch({ control: form.control, name: "rating" }));
  return (
    <form className="grid gap-5 rounded-2xl border border-[#17453a]/10 bg-white p-5 shadow-[0_8px_30px_rgba(18,60,50,.04)] sm:p-6" onSubmit={form.handleSubmit(async (values) => {
      await onSubmit(values);
      form.reset({ place_name: "", place_type: "attraction", rating: 5, review_text: "", visit_date: new Date().toISOString().slice(0, 10) });
    })}>
      <div>
        <p className="text-xs font-extrabold tracking-[0.12em] text-[#d56535]">NEW NOTE</p>
        <h2 className="mt-1 text-xl font-extrabold tracking-[-0.02em] text-[#173e34]">Remember a place</h2>
        <p className="mt-1 text-sm leading-6 text-[#60766f]">Keep a short note for your future self.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Place name" error={form.formState.errors.place_name?.message}><input className={inputClass} placeholder="e.g. Nine Arches Bridge" {...form.register("place_name")} /></Field>
        <Field label="Place type" error={form.formState.errors.place_type?.message}>
          <select className={inputClass} {...form.register("place_type")}>
            <option value="attraction">Attraction</option>
            <option value="hotel">Hotel</option>
            <option value="restaurant">Restaurant</option>
            <option value="beach">Beach</option>
            <option value="activity">Activity</option>
            <option value="other">Other</option>
          </select>
        </Field>
        <Field label="Visit date" error={form.formState.errors.visit_date?.message}><input className={inputClass} type="date" {...form.register("visit_date")} /></Field>
      </div>
      <Field label="Rating" error={form.formState.errors.rating?.message}>
        <div className="flex gap-1" role="group" aria-label="Rating out of 5">
          {[1, 2, 3, 4, 5].map((value) => (
            <button key={value} type="button" className="inline-flex h-10 w-10 items-center justify-center rounded-lg hover:bg-[#fdf0e8]" aria-label={`${value} star${value === 1 ? "" : "s"}`} onClick={() => form.setValue("rating", value, { shouldValidate: true })}>
              <Star className={`h-5 w-5 ${value <= rating ? "fill-[#e17742] text-[#e17742]" : "text-[#b9c7c1]"}`} />
            </button>
          ))}
        </div>
      </Field>
      <Field label="Your note" error={form.formState.errors.review_text?.message}><textarea className={`${inputClass} min-h-28 resize-y`} placeholder="What made this place worth remembering?" {...form.register("review_text")} /></Field>
      <Button className="w-full sm:w-auto sm:justify-self-end" type="submit" disabled={form.formState.isSubmitting}><Send className="h-4 w-4" /> Save note</Button>
    </form>
  );
}
