"use client";

import { useQuery } from "@tanstack/react-query";
import { MapPin, Star } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiErrorAlert } from "@/components/ApiErrorAlert";
import { AppShell } from "@/components/AppShell";
import { LoadingState } from "@/components/LoadingState";
import { ReviewForm, type ReviewFormValues } from "@/components/ReviewForm";
import * as reviewsApi from "@/lib/api/reviews";
import { useAuthStore } from "@/lib/store/auth-store";

export default function ReviewsPage() {
  const router = useRouter();
  const authenticated = useAuthStore((state) => state.authenticated);
  const user = useAuthStore((state) => state.user);
  const authHydrated = useAuthStore((state) => state.hydrated);
  const [error, setError] = useState<unknown>();
  const reviews = useQuery({
    queryKey: ["reviews", user?.id],
    queryFn: reviewsApi.myReviews,
    enabled: authHydrated && authenticated && !!user?.id,
  });

  useEffect(() => {
    if (authHydrated && !authenticated) router.replace("/login");
  }, [authenticated, authHydrated, router]);

  async function submit(values: ReviewFormValues) {
    setError(undefined);
    try {
      await reviewsApi.createReview(values);
      await reviews.refetch();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <AppShell>
      <div>
        <p className="text-xs font-extrabold tracking-[0.15em] text-[#d56535]">TRAVEL NOTES</p>
        <h1 className="mt-2 font-[family-name:var(--font-display)] text-4xl tracking-[-0.03em] text-[#123c32] sm:text-5xl">Places worth remembering.</h1>
        <p className="mt-2 max-w-2xl text-[#60766f]">A simple record of the stays, views, meals, and moments you’d happily return to.</p>
      </div>
      <div className="mt-8 grid gap-6 lg:grid-cols-[420px_1fr]">
        <div><ReviewForm onSubmit={submit} /><div className="mt-4"><ApiErrorAlert error={error} /></div></div>
        <section className="grid content-start gap-3">
          <ApiErrorAlert error={reviews.error} onRetry={() => reviews.refetch()} />
          {reviews.isPending ? <LoadingState title="Opening your notes" description="Your saved travel memories will appear here." /> : null}
          {reviews.data?.length ? reviews.data.map((review, index) => (
            <article key={`${review.place_name}-${index}`} className="rounded-2xl border border-[#17453a]/10 bg-white p-5 shadow-[0_6px_24px_rgba(18,60,50,.04)]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-lg font-extrabold tracking-[-0.02em] text-[#173e34]">{review.place_name}</p>
                  <p className="mt-1 flex items-center gap-1.5 text-xs font-semibold capitalize text-[#789087]"><MapPin className="h-3.5 w-3.5 text-[#d56535]" />{review.place_type} · {review.visit_date}</p>
                </div>
                <span className="inline-flex items-center gap-1 rounded-full bg-[#fdf0e8] px-2.5 py-1 text-xs font-bold text-[#9a4d2e]"><Star className="h-3.5 w-3.5 fill-[#e17742] text-[#e17742]" />{review.rating}/5</span>
              </div>
              <p className="mt-4 border-t border-[#17453a]/8 pt-4 text-sm leading-6 text-[#526b63]">{review.review_text}</p>
            </article>
          )) : !reviews.isPending ? (
            <div className="rounded-2xl border border-dashed border-[#17453a]/20 bg-white/60 p-8 text-center">
              <MapPin className="mx-auto h-5 w-5 text-[#d56535]" />
              <p className="mt-3 font-extrabold text-[#173e34]">No notes yet</p>
              <p className="mt-1 text-sm text-[#60766f]">Add a place you want to remember.</p>
            </div>
          ) : null}
        </section>
      </div>
    </AppShell>
  );
}
