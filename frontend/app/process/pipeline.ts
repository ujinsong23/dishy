"use server";

import { getBackendUrl } from "@/lib/backendUrl";

export async function runReviewScraping(placeId: string, restaurantName?: string) {
  const extra = restaurantName != null && restaurantName !== "" ? { restaurant_name: restaurantName } : undefined;
  return invokeBackendApi(`${getBackendUrl()}/review_scraping`, placeId, extra);
}

export async function runMenuListing(placeId: string) {
  return invokeBackendApi(`${getBackendUrl()}/menu_listing_main`, placeId);
}

export async function runMatchAndSummarize(placeId: string) {
  return invokeBackendApi(`${getBackendUrl()}/match_and_summarize_top_20`, placeId);
}

export async function runCollageImages(placeId: string) {
  return invokeBackendApi(`${getBackendUrl()}/collage_images`, placeId);
}

export async function runNanobanaImage(placeId: string, menuId: string) {
  if (!placeId || !menuId) {
    throw new Error("Invalid Place ID or Menu ID");
  }
  try {
    const response = await fetch(`${getBackendUrl()}/nanobanana_image`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ place_id: placeId, menu_id: menuId }),
    });

    // Parse JSON body for all known status codes (200, 404, 500)
    let data: any;
    try {
      data = await response.json();
    } catch {
      throw new Error("Invalid JSON response from nanobanana_image");
    }

    // 200 — "created": image generated successfully
    if (response.ok) {
      return data;
    }

    // 404 — "no_image": generation ran but produced no image (not a hard error)
    if (response.status === 404 && data?.status === "no_image") {
      return data;
    }

    // 500 or any other failure
    throw new Error(data?.message || data?.error || `API call failed: nanobanana_image (Status: ${response.status})`);
  } catch (error) {
    console.error("Error in API call to nanobanana_image:", error);
    throw error;
  }
}

async function invokeBackendApi(url: string, placeId: string, extraBody?: Record<string, string>) {
  if (!placeId) {
    throw new Error("Invalid Place ID");
  }

  try {
    const body = extraBody ? { place_id: placeId, ...extraBody } : { place_id: placeId };
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      let errorMsg = `API call failed: ${url.split("/").pop()} (Status: ${response.status})`;
      let errorCode: string | undefined;
      try {
        const errorData = await response.json();
        errorMsg = errorData.message || errorData.error || errorMsg;
        errorCode = errorData.error;
      } catch (p) {
        // If it's not JSON, just use the status text or default message
        const text = await response.text().catch(() => "");
        if (text.includes("<!doctype") || text.includes("<html")) {
          errorMsg = `Backend Error: The server returned an HTML error page. (Status: ${response.status})`;
        } else if (text) {
          errorMsg = text.slice(0, 100);
        }
      }
      const err = new Error(errorMsg);
      (err as any).code = errorCode;
      throw err;
    }

    const text = await response.text();
    try {
      return JSON.parse(text);
    } catch (e) {
      throw new Error(`Invalid JSON response from ${url.split("/").pop()}`);
    }
  } catch (error) {
    console.error(`Error in API call to ${url}:`, error);
    throw error;
  }
}
