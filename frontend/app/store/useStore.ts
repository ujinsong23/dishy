import { create } from "zustand";
import { getBackendUrl } from "@/lib/backendUrl";

interface IngredientInfo {
  fish: string[];
  shellfish: string[];
  red_meat: string[];
  poultry: string[];
  allergen_ingredients: string[];
}

interface MenuFromBoard {
  name: string;
  description: string;
  price: number | string;
  ingredients_by_category: IngredientInfo;
  dietary_labels: string[];
  nicknames: string[];
  options?: any;
}

interface MenuFromReviews {
  id: string;
  relevant_review_ids: number[];
  objective_summary: string;
  appearance: string;
  ingredients_by_category: IngredientInfo;
  dietary_claims: Array<{ claim: string; status: string; evidence_review_ids: number[] }>;
  diff_notes: Array<{ note: string; evidence_review_ids: number[] }>;
}

/** Per-claim: tag drives status pill + card; evidences has review quotes and Source Review links. Skip when value is null. */
export type DietaryOptionValue = {
  tag: "verified" | "warning" | "info" | "not_verified";
  evidences: Array<{ review_id: number; quote: string }>;
} | null;

interface MenuItem {
  from_menuboard: MenuFromBoard;
  from_reviews?: MenuFromReviews;
  /** Key = claim (e.g. "vegan"). Value = { tag, evidence } or null (skip). */
  dietary_options?: Record<string, DietaryOptionValue>;
  dishImage?: string; // AI Generated (nanobanana)
  /** True when nanobanana confirmed it cannot produce an image for this menu (404 no_image). */
  nanobananaNoImage?: boolean;
  collageImages?: string[]; // Array of real customer photos (0-9 per menu)
  collageImageUrls?: string[]; // Matching source review URLs for each collage image
}

interface RestaurantState {
  placeId: string | null;
  restaurantName: string;
  reviewCount: number;
  /** From review_scraping response (image_count). */
  imageCount: number;
  menuData: Record<string, MenuItem> | null;
  progress: number;
  phase: "scraping" | "analysis" | "results-preview" | "summarizing" | "images" | "finalize";
  error: string | null;
  scrapingData: any | null;
  restaurantOverview: { summary_html: string; glossary: Record<string, string> } | null;
  nanobananaGenerating: boolean;
  /** Menu id for which nanobanana image is currently being generated (for thumbnail badge). */
  nanobananaGeneratingMenuId: string | null;
  /** Menu id that just got nanobanana image (for "image ready" banner); clear when dismissed. */
  nanobananaReadyMenuId: string | null;
  /** Place id for which we have already started (or completed) collage + nanobanana image generation; prevents re-running when navigating back to results. */
  imageGenerationStartedForPlaceId: string | null;
  /** Whether collage images have finished loading (success or error). */
  collageImagesLoaded: boolean;

  setPlaceId: (id: string) => void;
  setImageGenerationStartedForPlaceId: (id: string | null) => void;
  setCollageImagesLoaded: (v: boolean) => void;
  setNanobananaGenerating: (v: boolean) => void;
  setNanobananaGeneratingMenuId: (id: string | null) => void;
  setNanobananaReadyMenuId: (id: string | null) => void;
  setRestaurantInfo: (name: string, count: number, imageCount?: number) => void;
  setMenuData: (data: Record<string, MenuItem>) => void;
  setRestaurantOverview: (data: { summary_html: string; glossary: Record<string, string> }) => void;
  updateCollageImages: (collages: Record<string, string[]>, srcReviewUrls?: Record<string, string[]>) => void;
  updateNanobananaImage: (menuId: string, nanobanana: string) => void;
  markNanobananaNoImage: (menuId: string) => void;
  setProgress: (p: number) => void;
  setPhase: (phase: RestaurantState["phase"]) => void;
  setError: (error: string | null) => void;
  setScrapingData: (data: any) => void;
  reset: () => void;
}

export const useRestaurantStore = create<RestaurantState>((set) => ({
  placeId: null,
  restaurantName: "Restaurant",
  reviewCount: 0,
  imageCount: 0,
  menuData: null,
  progress: 2,
  phase: "scraping",
  error: null,
  scrapingData: null,
  restaurantOverview: null,
  nanobananaGenerating: false,
  nanobananaGeneratingMenuId: null,
  nanobananaReadyMenuId: null,
  imageGenerationStartedForPlaceId: null,
  collageImagesLoaded: false,

  setPlaceId: (id) =>
    set((state) => ({
      placeId: id,
      // When switching to a different place, allow image generation to run again for the new place
      imageGenerationStartedForPlaceId:
        state.placeId === id ? state.imageGenerationStartedForPlaceId : null,
      collageImagesLoaded: state.placeId === id ? state.collageImagesLoaded : false,
    })),
  setImageGenerationStartedForPlaceId: (id) => set({ imageGenerationStartedForPlaceId: id }),
  setCollageImagesLoaded: (v) => set({ collageImagesLoaded: v }),
  setNanobananaGenerating: (v) => set({ nanobananaGenerating: v }),
  setNanobananaGeneratingMenuId: (id) => set({ nanobananaGeneratingMenuId: id }),
  setNanobananaReadyMenuId: (id) => set({ nanobananaReadyMenuId: id }),
  setRestaurantInfo: (name, count, imageCount) =>
    set((s) => ({
      restaurantName: name,
      reviewCount: count,
      ...(imageCount !== undefined && imageCount !== null ? { imageCount } : {}),
    })),
  setMenuData: (data) => set({ menuData: data }),
  setRestaurantOverview: (data) => set({ restaurantOverview: data }),
  updateCollageImages: (collages, srcReviewUrls) =>
    set((state) => {
      if (!state.menuData || !state.placeId) return state;
      const newMenuData = { ...state.menuData };
      const backendUrl = getBackendUrl();

      // Map collage images per menu_id
      Object.entries(collages).forEach(([menuId, filenames]) => {
        if (newMenuData[menuId]) {
          newMenuData[menuId] = {
            ...newMenuData[menuId],
            collageImages: filenames.map((f) => `${backendUrl}/data/${state.placeId}/collage/${menuId}/${f}`),
            ...(srcReviewUrls?.[menuId] ? { collageImageUrls: srcReviewUrls[menuId] } : {}),
          };
        }
      });

      return { menuData: newMenuData, collageImagesLoaded: true };
    }),
  updateNanobananaImage: (menuId, nanobanana) =>
    set((state) => {
      if (!state.menuData || !state.placeId || !menuId || !nanobanana) return state;
      const newMenuData = { ...state.menuData };
      const backendUrl = getBackendUrl();

      if (newMenuData[menuId]) {
        newMenuData[menuId] = {
          ...newMenuData[menuId],
          dishImage: `${backendUrl}/data/${state.placeId}/nanobanana/${nanobanana}`,
        };
      }

      return { menuData: newMenuData, nanobananaReadyMenuId: menuId };
    }),
  markNanobananaNoImage: (menuId) =>
    set((state) => {
      if (!state.menuData || !menuId) return state;
      const newMenuData = { ...state.menuData };
      if (newMenuData[menuId]) {
        newMenuData[menuId] = { ...newMenuData[menuId], nanobananaNoImage: true };
      }
      return { menuData: newMenuData };
    }),
  setProgress: (p) => set({ progress: p }),
  setPhase: (phase) => set({ phase }),
  setError: (error) => set({ error }),
  setScrapingData: (data) => set({ scrapingData: data }),
  reset: () =>
    set({
      placeId: null,
      restaurantName: "Restaurant",
      reviewCount: 0,
      imageCount: 0,
      menuData: null,
      progress: 2,
      phase: "scraping",
      error: null,
      scrapingData: null,
      restaurantOverview: null,
      nanobananaGenerating: false,
      nanobananaGeneratingMenuId: null,
      nanobananaReadyMenuId: null,
      imageGenerationStartedForPlaceId: null,
      collageImagesLoaded: false,
    }),
}));
