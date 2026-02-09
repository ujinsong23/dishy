"use server";

import { getBackendUrl } from "@/lib/backendUrl";

export async function getResults(placeId: string | null) {
  if (!placeId) return null;
  try {
    const response = await fetch(`${getBackendUrl()}/results?place_id=${placeId}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch results: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    console.error("Results fetch error:", error);
    throw error;
  }
}
