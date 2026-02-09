"use client";

import React, { Suspense, useState, useMemo, useCallback, useEffect, useRef } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { Search, ChevronDown, ChevronUp, ImageOff } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import AppBreadcrumb from "../components/AppBreadcrumb";
import styles from "./Results.module.css";
import dishyPickLogo from "../assets/dishy pick logo.svg";
import sparklesSvg from "../assets/sparkles.svg";
// import sampleMenus from "../../sample-menus.json"; // Commented out mock data
// import restaurantOverview from "../../sample-restaurant_overview.json"; // Commented out mock data

// Import SVGs
import HalalIcon from "../assets/halal.svg";
import KosherIcon from "../assets/kosher.svg";
import VegetarianIcon from "../assets/vegeterian.svg";
import VeganIcon from "../assets/vegan.svg";
import GlutenFreeIcon from "../assets/gluten free.svg";
import DairyFreeIcon from "../assets/dairy free.svg";
import NutFreeIcon from "../assets/nut free.svg";
import EggFreeIcon from "../assets/egg free.svg";
import redMeatIcon from "../assets/red meat.svg";
import poultryIcon from "../assets/Poultry.svg";
import fishIcon from "../assets/Fish.svg";
import shellfishIcon from "../assets/Shellfish.svg";
import allergenIcon from "../assets/allergen.svg";
import customerPhotoWarningSvg from "../assets/Customer Photo Warning.svg";
import generatingLoaderSvg from "../assets/Generating Loader.svg";

// Ingredient category icons (match detail page)
const INGREDIENT_CATEGORY_ICONS: Record<string, { src: string; alt: string }> = {
  red_meat: { src: redMeatIcon, alt: "Beef" },
  poultry: { src: poultryIcon, alt: "Chicken" },
  fish: { src: fishIcon, alt: "Fish" },
  shellfish: { src: shellfishIcon, alt: "Shellfish" },
  allergen_ingredients: { src: allergenIcon, alt: "Allergens" },
};

function toTitleCase(s: string): string {
  return s.toLowerCase().replace(/(?:^|[\s-])\w/g, (c) => c.toUpperCase());
}

// Shadcn UI Components
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { useRestaurantStore } from "../store/useStore";
import { useSearchParams } from "next/navigation";
import { runCollageImages, runNanobanaImage } from "../process/pipeline";
import { toast } from "sonner";

// Types
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
}

interface MenuItem {
  from_menuboard: MenuFromBoard;
  from_reviews?: any;
  dishImage?: string;
  collageImages?: string[];
}

// Fixed Dietary Options with Color Mapping
const DIETARY_OPTIONS = [
  { value: "vegan", label: "Vegan", color: "#22A72F", iconSrc: VeganIcon },
  { value: "gluten-free", label: "Gluten Free", color: "#C68A22", iconSrc: GlutenFreeIcon }, // Gold
  { value: "vegetarian", label: "Vegetarian", color: "#43802D", iconSrc: VegetarianIcon },
  { value: "dairy-free", label: "Dairy Free", color: "#5E7C98", iconSrc: DairyFreeIcon }, // Blue-ish Grey
  { value: "nut-free", label: "Nut Free", color: "#8B5E3C", iconSrc: NutFreeIcon }, // Brown
  { value: "egg-free", label: "Egg Free", color: "#E6B800", iconSrc: EggFreeIcon }, // Yellow-ish
  { value: "halal", label: "Halal", color: "#22A72F", iconSrc: HalalIcon },
  { value: "kosher", label: "Kosher", color: "#6A73C2", iconSrc: KosherIcon }, // Blue/Purple
];

function ResultsPageContent() {
  const router = useRouter();
  const {
    menuData,
    restaurantName,
    reviewCount,
    imageCount: imageCountFromStore,
    setPlaceId,
    setRestaurantInfo,
    restaurantOverview,
    nanobananaGeneratingMenuId,
    nanobananaReadyMenuId,
    setNanobananaReadyMenuId,
    imageGenerationStartedForPlaceId,
    setImageGenerationStartedForPlaceId,
    updateCollageImages,
    updateNanobananaImage,
    markNanobananaNoImage,
    setNanobananaGeneratingMenuId,
    setNanobananaGenerating,
    collageImagesLoaded,
    setCollageImagesLoaded,
  } = useRestaurantStore();
  const searchParams = useSearchParams();
  const placeId = searchParams.get("place_id") ?? searchParams.get("id");
  const toastShownForMenuIdRef = useRef<string | null>(null);
  const imageGenerationStartedForPlaceIdRef = useRef<string | null>(null);

  // Fallback if data is missing (e.g., refresh), use mock or empty.
  // Ideally we might trigger a fetch, but for now we rely on the store being populated.
  // If we assume the user navigated from Process page, store is full.
  const menuItems = menuData || {};

  // Fallback structure for overview if missing from store (e.g. during dev refresh without process)
  const validOverview = restaurantOverview || {
    summary_html: "<p>Not able to load restaurant summary</p>",
    glossary: {},
  };

  // Sync Place ID from URL. Restaurant name, reviewCount, imageCount: from store (set by process) or sessionStorage on refresh (no URL params).
  useEffect(() => {
    if (placeId) {
      setPlaceId(placeId);
    }
    if (!placeId || typeof sessionStorage === "undefined") return;
    try {
      const raw = sessionStorage.getItem(`restaurant_meta_${placeId}`);
      if (raw) {
        const meta = JSON.parse(raw) as {
          restaurantName?: string;
          reviewCount?: number;
          imageCount?: number;
        };
        const name = meta.restaurantName ?? restaurantName;
        const reviews = meta.reviewCount ?? reviewCount;
        const images = meta.imageCount ?? imageCountFromStore;
        if (meta.restaurantName != null || meta.reviewCount != null || meta.imageCount != null) {
          setRestaurantInfo(name, reviews, images);
        }
      }
    } catch {
      // ignore
    }
  }, [placeId, restaurantName, reviewCount, imageCountFromStore, setPlaceId, setRestaurantInfo]);

  // Image generation (collage + nanobanana for first 3) — only one round per placeId (persists across detail ↔ results navigation)
  useEffect(() => {
    if (!placeId || !menuData || typeof menuData !== "object") return;
    // Ref guard: avoid double-run in React Strict Mode (setState is async, ref is sync)
    if (imageGenerationStartedForPlaceIdRef.current === placeId) return;
    if (imageGenerationStartedForPlaceId === placeId) return;
    imageGenerationStartedForPlaceIdRef.current = placeId;
    setImageGenerationStartedForPlaceId(placeId);

    const runImageGeneration = async () => {
      // 1. Collage images
      try {
        const collageRes = await runCollageImages(placeId);
        if (collageRes.collage) {
          updateCollageImages(collageRes.collage, collageRes.src_review_urls);
        }
      } catch (bgError) {
        console.error("Collage image generation error:", bgError);
      } finally {
        setCollageImagesLoaded(true);
      }

      // 2. Nanobanana "Show Me the Dish" for first 3 menus — pick top 3 by relevant_review_ids length (descending)
      const menuIds = Object.entries(menuItems)
        .sort(([, a], [, b]) => {
          const aLen =
            (a as { from_reviews?: { relevant_review_ids?: unknown[] } }).from_reviews?.relevant_review_ids?.length ??
            0;
          const bLen =
            (b as { from_reviews?: { relevant_review_ids?: unknown[] } }).from_reviews?.relevant_review_ids?.length ??
            0;
          return bLen - aLen;
        })
        .slice(0, 3)
        .map(([key]) => key);
      if (menuIds.length > 0) {
        setNanobananaGenerating(true);
        for (const menuId of menuIds) {
          try {
            setNanobananaGeneratingMenuId(menuId);
            const nanoRes = await runNanobanaImage(placeId, menuId);
            if (nanoRes?.status === "created" && nanoRes?.nanobanana) {
              updateNanobananaImage(menuId, nanoRes.nanobanana);
            } else if (nanoRes?.status === "no_image") {
              markNanobananaNoImage(menuId);
            }
          } catch (err) {
            console.error(`Nanobanana image failed for menu ${menuId}:`, err);
          } finally {
            setNanobananaGeneratingMenuId(null);
          }
        }
        setNanobananaGenerating(false);
      }
    };

    runImageGeneration();
  }, [
    placeId,
    menuData,
    imageGenerationStartedForPlaceId,
    setImageGenerationStartedForPlaceId,
    updateCollageImages,
    updateNanobananaImage,
    markNanobananaNoImage,
    setNanobananaGeneratingMenuId,
    setNanobananaGenerating,
    setCollageImagesLoaded,
    menuItems,
  ]);

  // Image count from store (set by process from review_scraping response image_count)
  const imageCount = imageCountFromStore;

  // summary_html with <b class="menuId"> converted to links to detail page (include place_id so detail page has context)
  const summaryHtmlWithLinks = useMemo(() => {
    const html = validOverview.summary_html ?? "";
    const base = placeId ? `/results/detail?place_id=${encodeURIComponent(placeId)}&` : "/results/detail?";
    return html.replace(/<b\s+class="([^"]+)">([\s\S]*?)<\/b>/gi, (_, menuId, content) => {
      const href = `${base}id=${encodeURIComponent(menuId)}`;
      return `<a href="${href}" class="${styles.dishyPickLink}">${content}</a>`;
    });
  }, [validOverview.summary_html, placeId]);

  // Brief skeleton for Dishy Picks to hint AI-generated content
  const [dishyPicksRevealed, setDishyPicksRevealed] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setDishyPicksRevealed(true), 400);
    return () => clearTimeout(timer);
  }, []);

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDietary, setSelectedDietary] = useState<string[]>([]);
  const [failedImageIds, setFailedImageIds] = useState<Set<string>>(new Set());
  const [isGlossaryOpen, setIsGlossaryOpen] = useState(false);

  const handleImageError = useCallback((itemId: string) => {
    setFailedImageIds((prev) => new Set(prev).add(itemId));
  }, []);

  const toggleDietary = (value: string) => {
    setSelectedDietary((prev) => (prev.includes(value) ? prev.filter((d) => d !== value) : [...prev, value]));
  };

  const menuEntries = useMemo(() => {
    if (!menuItems) return [];
    return Object.entries(menuItems).map(([id, item]) => {
      const hasNoImage = !item.dishImage && (!item.collageImages || item.collageImages.length === 0);
      return {
        id,
        ...item.from_menuboard,
        hasNoImage,
        // Prefer nanobanana (dishImage), then collage [0], then sample (only if we have something)
        thumbnailImage: hasNoImage
          ? null
          : item.dishImage ||
            (item.collageImages && item.collageImages.length > 0 ? item.collageImages[0] : `/sample-collage/${id}.png`),
      };
    }); // Preserve original order from the menus API response
  }, [menuItems]);

  const filteredItems = useMemo(() => {
    return menuEntries
      .filter((item) => {
        const matchesSearch =
          item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          item.description.toLowerCase().includes(searchQuery.toLowerCase());

        // Check Dietary
        const rawItem = menuItems[item.id] as any;
        const itemDietaryOptions = rawItem.dietary_options || {};

        const matchesDietary =
          selectedDietary.length === 0 ||
          selectedDietary.every((d) => {
            const option = itemDietaryOptions[d];
            return option !== null;
          });

        return matchesSearch && matchesDietary;
      })
      .sort((a, b) => {
        const aReviews = (menuItems[a.id] as any)?.from_reviews?.relevant_review_ids?.length ?? 0;
        const bReviews = (menuItems[b.id] as any)?.from_reviews?.relevant_review_ids?.length ?? 0;
        return bReviews - aReviews;
      });
  }, [menuEntries, searchQuery, selectedDietary, menuItems]);

  // Split filtered items into reviewed (has from_reviews with content) and menu-only (no reviews)
  const { reviewedItems, menuOnlyItems } = useMemo(() => {
    const reviewed: typeof filteredItems = [];
    const menuOnly: typeof filteredItems = [];
    for (const item of filteredItems) {
      const rawItem = menuItems[item.id] as any;
      const fromReviews = rawItem?.from_reviews;
      const hasReviews = fromReviews && typeof fromReviews === "object" && Object.keys(fromReviews).length > 0;
      if (hasReviews) {
        reviewed.push(item);
      } else {
        menuOnly.push(item);
      }
    }
    return { reviewedItems: reviewed, menuOnlyItems: menuOnly };
  }, [filteredItems, menuItems]);

  const glossaryItems = Object.entries(validOverview.glossary || {});

  // Show Sonner toast when a nanobanana image is ready — guard so it only fires once per menuId (avoids duplicate from Strict Mode)
  useEffect(() => {
    const menuId = nanobananaReadyMenuId;
    const item = menuId && menuData?.[menuId];
    if (!menuId || !item) return;
    if (toastShownForMenuIdRef.current === menuId) return;
    toastShownForMenuIdRef.current = menuId;
    const dishName = item.from_menuboard?.name ?? "this dish";
    const detailHref = placeId
      ? `/results/detail?place_id=${encodeURIComponent(placeId)}&id=${encodeURIComponent(menuId)}`
      : `/results/detail?id=${encodeURIComponent(menuId)}`;
    toast.success(
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <span>
          Image for{" "}
          <span
            role="link"
            tabIndex={0}
            style={{ color: "#2563EB", textDecoration: "underline", fontWeight: 600, cursor: "pointer" }}
            onClick={() => router.push(detailHref)}
            onKeyDown={(e) => {
              if (e.key === "Enter") router.push(detailHref);
            }}
          >
            {dishName}
          </span>{" "}
          is ready
        </span>
        <span style={{ color: "#737373", fontSize: "13px" }}>
          Based on recurring patterns in customer photos referencing this dish using Nano Banana 3.
        </span>
      </div>,
    );
    setNanobananaReadyMenuId(null);
  }, [nanobananaReadyMenuId, menuData, placeId, setNanobananaReadyMenuId, router]);

  const getBuiltFromMessage = () => {
    const cappedCount = reviewCount > 500 ? 500 : reviewCount;
    return `Built from ${cappedCount} relevant comments and ${imageCount} images, selected from total ${reviewCount} reviews.`;
  };

  return (
    <>
      <AppBreadcrumb variant="change-restaurant" />
      <TooltipProvider delayDuration={400}>
        <div className={styles.wrapper}>
          <div className={styles.viewHeader}>
            <h1 className={styles.viewTitle}>
              How people <em>experience</em> the menu at {restaurantName}
            </h1>
            <p className={styles.viewSubtitle}>
              {getBuiltFromMessage()}
              <br />
              Click any dish to see the clear summary, ingredients, and direct review sources.
            </p>
          </div>

          {/* Dishy Picks Section */}
          <div className={styles.dishyPicksSection}>
            <div className={styles.dishyHeaderRow}>
              <Image src={dishyPickLogo} alt="" width={48} height={48} className={styles.dishyIcon} aria-hidden />
              <div className={styles.dishyTitleBlock}>
                <span className={styles.dishyTitle}>
                  Dishy Picks
                  <Image src={sparklesSvg} alt="" width={20} height={19} aria-hidden />
                </span>
                {!dishyPicksRevealed ? (
                  <div className="flex w-full flex-col gap-2 py-1">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                  </div>
                ) : (
                  <div
                    className={styles.dishyContent}
                    dangerouslySetInnerHTML={{ __html: summaryHtmlWithLinks }}
                    onClick={(e) => {
                      const target = e.target as HTMLElement;
                      const anchor = target.closest("a");
                      if (anchor && anchor.href && anchor.href.includes("/results/detail")) {
                        e.preventDefault();
                        const url = new URL(anchor.href);
                        router.push(url.pathname + url.search);
                      }
                    }}
                  />
                )}

                {glossaryItems.length > 0 && (
                  <>
                    <button className={styles.glossaryTrigger} onClick={() => setIsGlossaryOpen(!isGlossaryOpen)}>
                      Menu Glossary
                      {isGlossaryOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>

                    <AnimatePresence>
                      {isGlossaryOpen && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className={styles.glossaryContent}
                        >
                          {glossaryItems.map(([term, def]) => (
                            <div key={term} className={styles.glossaryItem}>
                              <span className={styles.glossaryTerm}>{term}: </span>
                              <span className={styles.glossaryDef}>
                                {typeof def === "string" && def.length > 0
                                  ? def.charAt(0).toUpperCase() + def.slice(1)
                                  : def}
                              </span>
                            </div>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className={styles.viewHeader} style={{ textAlign: "left", marginBottom: "1rem" }}>
            <h2 className={styles.viewTitle} style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>
              Top <em>mentioned</em> Dishes
            </h2>
            <p className={styles.viewSubtitle} style={{ margin: 0, fontSize: "0.875rem" }}>
              Ranked by how often each dish is mentioned in reviews.
            </p>
          </div>

          <div className={styles.filtersRow}>
            <div className={styles.searchWrap}>
              <div className={styles.searchInputWrap}>
                <Search className={styles.searchIcon} aria-hidden />
                <Input
                  placeholder="Search..."
                  className={styles.searchInput}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            <div className={styles.dietaryGroup}>
              <span className={styles.dietaryLabel}>
                Dietary Options{" "}
                <span style={{ color: "#737373", fontSize: "14px", fontWeight: "normal", marginLeft: "12px" }}>
                  Options are sourced from the restaurant&#39;s menu and customer reviews. Availability may vary.
                </span>
              </span>
              <div className={styles.dietaryOptionsWrap}>
                {DIETARY_OPTIONS.map((option) => {
                  const isSelected = selectedDietary.includes(option.value);
                  return (
                    <button
                      key={option.value}
                      onClick={() => toggleDietary(option.value)}
                      className={styles.dietaryBadge}
                      data-selected={isSelected}
                      style={{
                        color: isSelected ? "white" : "black",
                      }}
                    >
                      <div style={{ position: "relative", width: 16, height: 16 }}>
                        <Image src={option.iconSrc} alt={option.label} fill style={{ objectFit: "contain" }} />
                      </div>
                      <span>{option.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className={styles.resultsGrid}>
            {reviewedItems.map((item, idx) => {
              const rawItem = menuItems[item.id] as any;
              const dietOptions = rawItem.dietary_options || {};
              const activeDietTags = DIETARY_OPTIONS.filter((opt) => dietOptions[opt.value] !== null);

              const isNanobanana = !!rawItem.dishImage;
              const isCollageLoading = item.hasNoImage && !collageImagesLoaded;
              return (
                <Link
                  key={item.id}
                  href={
                    placeId
                      ? `/results/detail?place_id=${encodeURIComponent(placeId)}&id=${encodeURIComponent(item.id)}`
                      : `/results/detail?id=${encodeURIComponent(item.id)}`
                  }
                  className={styles.cardLink}
                >
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: idx * 0.05 }}>
                    <div
                      className={
                        isCollageLoading
                          ? `${styles.cardImageWrap} ${styles.cardImageWrapLoading}`
                          : item.hasNoImage || failedImageIds.has(item.id)
                            ? `${styles.cardImageWrap} ${styles.cardImageWrapEmpty}`
                            : isNanobanana
                              ? `${styles.cardImageWrap} ${styles.cardImageWrapNanobanana}`
                              : nanobananaGeneratingMenuId === item.id
                                ? `${styles.cardImageWrap} ${styles.cardImageWrapGenerating}`
                                : styles.cardImageWrap
                      }
                    >
                      {isCollageLoading && (
                        <div className={styles.cardImageLoading}>
                          <Image
                            src={generatingLoaderSvg}
                            alt=""
                            width={24}
                            height={24}
                            className={styles.cardGeneratingSpinner}
                            aria-hidden
                          />
                          <span>Loading photo…</span>
                        </div>
                      )}
                      {!isCollageLoading && (item.hasNoImage || failedImageIds.has(item.id)) && collageImagesLoaded && (
                        <div className={styles.cardNoPhotos}>
                          <ImageOff className={styles.cardNoPhotosIcon} aria-hidden />
                          <span>No photos found</span>
                        </div>
                      )}
                      {!isCollageLoading && !(item.hasNoImage || failedImageIds.has(item.id)) && (
                        <>
                          <Image
                            src={item.thumbnailImage!}
                            alt={item.name}
                            fill
                            sizes="(min-width: 1280px) 25vw, (min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                            className={styles.cardImage}
                            onError={() => handleImageError(item.id)}
                            unoptimized
                          />
                          {isNanobanana && (
                            <Image
                              src={sparklesSvg}
                              alt=""
                              width={30}
                              height={30}
                              className={styles.cardImageSparkle}
                              aria-hidden
                            />
                          )}
                          {!isNanobanana && nanobananaGeneratingMenuId !== item.id && (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className={styles.cardCustomerPhotoBadge}>
                                  <Image src={customerPhotoWarningSvg} alt="" width={16} height={16} aria-hidden />
                                  <span>Customer Photo</span>
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="top" style={{ maxWidth: 250 }}>
                                Photo sourced from customer reviews. When limited visuals are available, it may not
                                fully represent the dish.
                              </TooltipContent>
                            </Tooltip>
                          )}
                          {nanobananaGeneratingMenuId === item.id && (
                            <span className={styles.cardGeneratingBadge}>
                              <Image
                                src={generatingLoaderSvg}
                                alt=""
                                width={16}
                                height={16}
                                className={styles.cardGeneratingSpinner}
                                aria-hidden
                              />
                              <span>Generating</span>
                            </span>
                          )}
                        </>
                      )}
                    </div>
                    <div className={styles.cardBody}>
                      <div className={styles.cardHeaderRow}>
                        <div className={styles.cardTitleWrap}>
                          <h3 className={styles.cardTitle}>
                            {idx + 1}. {item.name}
                          </h3>
                          {item.ingredients_by_category && (
                            <div className={styles.cardIngredientIcons}>
                              {Object.entries(item.ingredients_by_category)
                                .filter(([, arr]) => Array.isArray(arr) && arr.length > 0)
                                .map(([cat, ings]) => {
                                  const iconInfo = INGREDIENT_CATEGORY_ICONS[cat];
                                  if (!iconInfo) return null;
                                  const tooltip = toTitleCase(ings.join(", "));
                                  return (
                                    <Tooltip key={cat}>
                                      <TooltipTrigger asChild>
                                        <span className={styles.cardIngredientIcon} aria-label={tooltip}>
                                          <Image src={iconInfo.src} alt={iconInfo.alt} width={16} height={16} />
                                        </span>
                                      </TooltipTrigger>
                                      <TooltipContent side="top" className="max-w-[260px] text-center">
                                        {tooltip}
                                      </TooltipContent>
                                    </Tooltip>
                                  );
                                })}
                            </div>
                          )}
                        </div>
                        <span className={styles.cardPrice}>${item.price}</span>
                      </div>
                      <p className={styles.cardDesc}>{item.description}</p>

                      {activeDietTags.length > 0 && (
                        <div className={styles.cardBadges}>
                          {activeDietTags.map((tag) => (
                            <span
                              key={tag.value}
                              className={styles.miniDietaryBadge}
                              style={{ borderColor: "#E5E5E5", color: "#444" }}
                            >
                              <div style={{ position: "relative", width: 12, height: 12 }}>
                                <Image src={tag.iconSrc} alt={tag.label} fill style={{ objectFit: "contain" }} />
                              </div>
                              <span style={{ marginLeft: 4 }}>{tag.label}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </motion.div>
                </Link>
              );
            })}
          </div>

          {/* More dishes from the Menu – items with no review data */}
          {menuOnlyItems.length > 0 && (
            <div className={styles.moreDishesSection}>
              <h2 className={styles.moreDishesTitle}>
                <em>More dishes</em> from the Menu
              </h2>
              <div className={styles.moreDishesGrid}>
                {menuOnlyItems.map((item) => {
                  const rawItem = menuItems[item.id] as any;
                  const dietOptions = rawItem.dietary_options || {};
                  const activeDietTags = DIETARY_OPTIONS.filter((opt) => dietOptions[opt.value] !== null);

                  return (
                    <div key={item.id} className={styles.moreDishesItem}>
                      <div className={styles.moreDishesRow}>
                        <div className={styles.moreDishesInfo}>
                          <div className={styles.moreDishesNameRow}>
                            <h3 className={styles.moreDishesName}>{item.name}</h3>
                            {item.ingredients_by_category && (
                              <div className={styles.cardIngredientIcons}>
                                {Object.entries(item.ingredients_by_category)
                                  .filter(([, arr]) => Array.isArray(arr) && arr.length > 0)
                                  .map(([cat, ings]) => {
                                    const iconInfo = INGREDIENT_CATEGORY_ICONS[cat];
                                    if (!iconInfo) return null;
                                    const tooltip = toTitleCase(ings.join(", "));
                                    return (
                                      <Tooltip key={cat}>
                                        <TooltipTrigger asChild>
                                          <span className={styles.cardIngredientIcon} aria-label={tooltip}>
                                            <Image src={iconInfo.src} alt={iconInfo.alt} width={16} height={16} />
                                          </span>
                                        </TooltipTrigger>
                                        <TooltipContent side="top" className="max-w-[260px] text-center">
                                          {tooltip}
                                        </TooltipContent>
                                      </Tooltip>
                                    );
                                  })}
                              </div>
                            )}
                          </div>
                          <p className={styles.moreDishesDesc}>{item.description}</p>
                          {activeDietTags.length > 0 && (
                            <div className={styles.cardBadges}>
                              {activeDietTags.map((tag) => (
                                <span
                                  key={tag.value}
                                  className={styles.miniDietaryBadge}
                                  style={{ borderColor: "#E5E5E5", color: "#444" }}
                                >
                                  <div style={{ position: "relative", width: 12, height: 12 }}>
                                    <Image src={tag.iconSrc} alt={tag.label} fill style={{ objectFit: "contain" }} />
                                  </div>
                                  <span style={{ marginLeft: 4 }}>{tag.label}</span>
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <span className={styles.moreDishesPrice}>${item.price}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </TooltipProvider>
    </>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<div style={{ padding: "2rem", textAlign: "center" }}>Loading...</div>}>
      <ResultsPageContent />
    </Suspense>
  );
}
