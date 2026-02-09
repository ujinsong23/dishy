"use server";

import { getBackendUrl } from "@/lib/backendUrl";

export async function searchRestaurants(query: string) {
  if (!query) return { result: [] };

  const backendUrl = getBackendUrl();
  try {
    const response = await fetch(`${backendUrl}/search_restaurants?query=${encodeURIComponent(query)}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch restaurants: ${response.statusText}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    return { result: [], error: "Failed to search for restaurants" };
  }
}
