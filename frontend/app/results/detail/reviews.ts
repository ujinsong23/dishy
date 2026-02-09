"use server";

import { getBackendUrl } from "@/lib/backendUrl";

export type FetchedReview = {
  text: string;
  reviewUrl: string;
  publishedDate: string;
};

export async function fetchReviews(placeId: string, ids: string[]): Promise<{ reviews: FetchedReview[] }> {
  if (!ids.length) {
    return { reviews: [] };
  }
  const url = `${getBackendUrl()}/reviews`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ place_id: placeId, ids }),
  });
  if (!res.ok) {
    throw new Error(`Reviews failed: ${res.status}`);
  }
  const data = await res.json();
  const reviews = Array.isArray(data?.reviews) ? data.reviews : [];
  return { reviews };
}
