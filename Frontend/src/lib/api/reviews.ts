import { json, request } from "./client";
import type { Review } from "./types";

export const createReview = (body: Review) => json<{ message: string; review_id: string }>("/reviews/", "POST", body);
export const myReviews = () => request<Review[]>("/reviews/my");
export const placeReviews = (placeName: string) => request<Review[]>(`/reviews/place/${encodeURIComponent(placeName)}`);
