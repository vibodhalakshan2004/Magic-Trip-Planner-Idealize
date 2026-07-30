"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiErrorAlert } from "@/components/ApiErrorAlert";
import { AppShell } from "@/components/AppShell";
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
      <h1 className="text-3xl font-black text-slate-950">My Reviews</h1>
      <p className="mt-2 text-slate-500">Capture favorite stays, viewpoints, food stops, and cultural visits.</p>
      <div className="mt-6 grid gap-6 lg:grid-cols-[420px_1fr]">
        <div><ReviewForm onSubmit={submit} /><ApiErrorAlert error={error} /></div>
        <section className="grid content-start gap-3">
          <ApiErrorAlert error={reviews.error} onRetry={() => reviews.refetch()} />
          {reviews.data?.length ? reviews.data.map((review, index) => (
            <article key={`${review.place_name}-${index}`} className="rounded-md border border-slate-200 bg-white p-4">
              <p className="font-black text-slate-950">{review.place_name}</p>
              <p className="text-sm text-slate-500">{review.place_type} · {review.rating}/5 · {review.visit_date}</p>
              <p className="mt-2 text-sm text-slate-700">{review.review_text}</p>
            </article>
          )) : <p className="rounded-md bg-white p-6 text-sm text-slate-500">No reviews yet. Add your first place note.</p>}
        </section>
      </div>
    </AppShell>
  );
}
