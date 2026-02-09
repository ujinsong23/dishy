"use client";

import React, { Suspense, useState, useCallback, useEffect, useMemo, useRef } from "react";
import Image, { type StaticImageData } from "next/image";
import { useSearchParams, useRouter } from "next/navigation";
import { ImageOff, Loader2, ExternalLink, UtensilsCrossed } from "lucide-react";
import { useRestaurantStore } from "../../store/useStore";
import { runNanobanaImage } from "../../process/pipeline";
import { fetchReviews, type FetchedReview } from "./reviews";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import DietaryInsightSection from "./DietaryInsightSection";
import AppBreadcrumb from "../../components/AppBreadcrumb";
import styles from "./Detail.module.css";
import sparklesSvg from "../../assets/sparkles.svg";
import customerPhotoWarningSvg from "../../assets/Customer Photo Warning.svg";
import redMeatIcon from "../../assets/red meat.svg";
import poultryIcon from "../../assets/Poultry.svg";
import fishIcon from "../../assets/Fish.svg";
import shellfishIcon from "../../assets/Shellfish.svg";
import allergenIcon from "../../assets/allergen.svg";
import sizeOptionIcon from "../../assets/size.svg";
import spicinessOptionIcon from "../../assets/spiceness.svg";
import toppingsOptionIcon from "../../assets/toppings.svg";
import proteinsOptionIcon from "../../assets/proteins.svg";
import otherOptionIcon from "../../assets/other options.svg";

function toTitleCase(s: string): string {
  return s.toLowerCase().replace(/(?:^|[\s-])\w/g, (c) => c.toUpperCase());
}

// Helper function to get ingredient dot color class
function getIngredientDotClass(category: string): string {
  const cat = category.toLowerCase();
  if (cat.includes("beef") || cat.includes("meat")) return styles.ingredientDotBeef;
  if (cat.includes("chicken") || cat.includes("poultry")) return styles.ingredientDotChicken;
  if (cat.includes("salmon") || cat.includes("fish")) return styles.ingredientDotSalmon;
  if (cat.includes("crab") || cat.includes("shellfish")) return styles.ingredientDotCrab;
  if (cat.includes("egg")) return styles.ingredientDotEgg;
  if (cat.includes("vegetable") || cat.includes("vegan")) return styles.ingredientDotVegetable;
  if (cat.includes("seafood")) return styles.ingredientDotSeafood;
  if (cat.includes("dairy") || cat.includes("cheese") || cat.includes("milk")) return styles.ingredientDotDairy;
  if (cat.includes("grain") || cat.includes("wheat") || cat.includes("bread")) return styles.ingredientDotGrain;
  return styles.ingredientDotDefault;
}

// Category key -> { icon, alt } for Ingredients section
const INGREDIENT_CATEGORY_ICONS: Record<string, { src: StaticImageData; alt: string }> = {
  red_meat: { src: redMeatIcon, alt: "Beef" },
  poultry: { src: poultryIcon, alt: "Chicken" },
  fish: { src: fishIcon, alt: "Fish" },
  shellfish: { src: shellfishIcon, alt: "Shellfish" },
  allergen_ingredients: { src: allergenIcon, alt: "Allergens" },
};

// Option key -> { icon, label } for Options section (only show keys with non-empty list)
const OPTION_CATEGORY_ICONS: Record<string, { src: StaticImageData; alt: string; label: string }> = {
  size: { src: sizeOptionIcon, alt: "Size", label: "Size" },
  spiciness: { src: spicinessOptionIcon, alt: "Spiciness", label: "Spiciness" },
  toppings: { src: toppingsOptionIcon, alt: "Toppings", label: "Toppings" },
  proteins: { src: proteinsOptionIcon, alt: "Proteins", label: "Proteins" },
  other_option: { src: otherOptionIcon, alt: "Other Options", label: "Other Options" },
};

function DetailPageContent() {
  const searchParams = useSearchParams();
  const id = searchParams.get("id");
  const placeIdFromUrl = searchParams.get("place_id");
  const router = useRouter();
  const {
    placeId,
    setPlaceId,
    menuData,
    restaurantName,
    nanobananaGenerating,
    nanobananaGeneratingMenuId,
    setNanobananaGenerating,
    setNanobananaGeneratingMenuId,
    updateNanobananaImage,
    markNanobananaNoImage,
    nanobananaReadyMenuId,
    setNanobananaReadyMenuId,
    collageImagesLoaded,
  } = useRestaurantStore();

  const toastShownForMenuIdRef = useRef<string | null>(null);

  // Sync place_id from URL so store has context when navigating from results (e.g. Dishy Picks links)
  useEffect(() => {
    if (placeIdFromUrl) {
      setPlaceId(placeIdFromUrl);
    }
  }, [placeIdFromUrl, setPlaceId]);

  const item = menuData && id ? menuData[id] : null;

  // Detect when collage images were loaded but none found for this specific menu
  const hasNoCollage = collageImagesLoaded && (!item?.collageImages || item.collageImages.length === 0);

  // Show Sonner toast when a nanobanana image is ready
  useEffect(() => {
    const menuId = nanobananaReadyMenuId;
    const readyItem = menuId && menuData?.[menuId];
    if (!menuId || !readyItem) return;
    if (toastShownForMenuIdRef.current === menuId) return;
    toastShownForMenuIdRef.current = menuId;
    const dishName = readyItem.from_menuboard?.name ?? "this dish";
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
  const showGenerateButton = item && !item.dishImage && !item.nanobananaNoImage;

  const handleGenerateNanobanana = useCallback(async () => {
    if (!placeId || !id || !item || item.dishImage || item.nanobananaNoImage || nanobananaGenerating) return;
    setNanobananaGenerating(true);
    setNanobananaGeneratingMenuId(id);
    try {
      const nanoRes = await runNanobanaImage(placeId, id);

      if (nanoRes?.status === "created" && nanoRes?.nanobanana) {
        // Image generated successfully
        updateNanobananaImage(id, nanoRes.nanobanana);
        setDishImageFailed(false);
      } else if (nanoRes?.status === "no_image") {
        // No image could be generated — persist so the button is permanently hidden
        markNanobananaNoImage(id);
      }
    } catch (err: any) {
      // 500 or network error
      console.error("Generate nanobanana image failed:", err);
      toast.error(err?.message || "Image generation failed. Please try again later.", {
        duration: 5000,
      });
    } finally {
      setNanobananaGenerating(false);
      setNanobananaGeneratingMenuId(null);
    }
  }, [
    placeId,
    id,
    item,
    nanobananaGenerating,
    setNanobananaGenerating,
    setNanobananaGeneratingMenuId,
    updateNanobananaImage,
    markNanobananaNoImage,
  ]);

  // Brief skeleton for AI Summary to hint AI-generated content
  const [aiSummaryRevealed, setAiSummaryRevealed] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setAiSummaryRevealed(true), 400);
    return () => clearTimeout(timer);
  }, []);

  const [brokenCollageIndices, setBrokenCollageIndices] = useState<Set<number>>(new Set());
  const [dishImageFailed, setDishImageFailed] = useState(false);
  const [collageFallbackFailed, setCollageFallbackFailed] = useState(false);

  const isShowingCollage = !!(
    item?.collageImages?.[0] &&
    !collageFallbackFailed &&
    !(item?.dishImage && !dishImageFailed)
  );
  const isGeneratingThisDish = id != null && nanobananaGeneratingMenuId === id;

  const [reviews, setReviews] = useState<FetchedReview[] | null>(null);
  const [reviewsLoading, setReviewsLoading] = useState(false);
  const [reviewsError, setReviewsError] = useState<string | null>(null);
  const [reviewsToShow, setReviewsToShow] = useState(5);

  const relevantReviewIds = item?.from_reviews?.relevant_review_ids;
  useEffect(() => {
    const ids = relevantReviewIds as number[] | undefined;
    if (!placeId || !ids?.length) {
      setReviews(null);
      return;
    }
    let cancelled = false;
    setReviewsLoading(true);
    setReviewsError(null);
    fetchReviews(placeId, ids.map(String))
      .then((data) => {
        if (!cancelled) setReviews(data.reviews);
      })
      .catch((err) => {
        if (!cancelled) {
          setReviewsError(err instanceof Error ? err.message : "Failed to load reviews");
          setReviews([]);
        }
      })
      .finally(() => {
        if (!cancelled) setReviewsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [placeId, relevantReviewIds]);

  useEffect(() => {
    setReviewsToShow(5);
  }, [relevantReviewIds]);

  const handleLoadMoreReviews = useCallback(() => {
    setReviewsToShow((n) => n + 5);
  }, []);

  const reviewIdToUrl = useMemo(() => {
    const m: Record<number, string> = {};
    if (!relevantReviewIds || !reviews?.length) return m;
    (relevantReviewIds as number[]).forEach((id, i) => {
      if (reviews[i]?.reviewUrl) m[id] = reviews[i].reviewUrl;
    });
    return m;
  }, [relevantReviewIds, reviews]);

  const handleCollageImageError = useCallback((index: number) => {
    setBrokenCollageIndices((prev) => new Set(prev).add(index));
  }, []);

  if (!item || !item.from_menuboard) {
    return (
      <div className={styles.emptyState}>
        <h2 className={styles.emptyTitle}>Dish not found</h2>
        <p className={styles.emptyMessage}>
          It seems we don&apos;t have the data for this dish yet. Please go back and try again.
        </p>
        <Button variant="default" onClick={() => router.back()}>
          Go Back
        </Button>
      </div>
    );
  }

  const { from_menuboard, from_reviews, dietary_options } = item;

  return (
    <div className={styles.page}>
      <AppBreadcrumb variant="detail" restaurantName={restaurantName} dishName={from_menuboard.name} />
      <div className={styles.wrapper}>
        <div className={styles.twoCol}>
          {/* Left Column: Image + Customer Photos */}
          <div className={styles.leftColumn}>
            {/* Dish Image Section */}
            <div className={styles.section}>
              <div
                className={
                  item.dishImage && !dishImageFailed
                    ? `${styles.imageWrap} ${styles.imageWrapNanobanana}`
                    : isGeneratingThisDish
                      ? `${styles.imageWrap} ${styles.imageWrapGenerating}`
                      : styles.imageWrap
                }
              >
                {item.dishImage && !dishImageFailed ? (
                  <>
                    <Image
                      key="dish"
                      src={item.dishImage}
                      alt={from_menuboard.name}
                      fill
                      sizes="580px"
                      className={styles.image}
                      onError={() => setDishImageFailed(true)}
                      unoptimized
                    />
                    <Image
                      src={sparklesSvg}
                      alt=""
                      width={50}
                      height={50}
                      className={styles.imageSparkle}
                      aria-hidden
                    />
                  </>
                ) : item.collageImages?.[0] && !collageFallbackFailed ? (
                  <Image
                    key="collage-fallback"
                    src={item.collageImages[0]}
                    alt={from_menuboard.name}
                    fill
                    sizes="580px"
                    className={styles.image}
                    onError={() => setCollageFallbackFailed(true)}
                    unoptimized
                  />
                ) : (
                  <div className={styles.noPhotosMessage}>
                    <ImageOff className={styles.imagePlaceholder} aria-hidden />
                    {hasNoCollage && <span>No customer photos found</span>}
                  </div>
                )}
                {isShowingCollage && (
                  <TooltipProvider delayDuration={400}>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className={styles.imageCustomerPhotoBadge}>
                          <Image src={customerPhotoWarningSvg} alt="" width={17} height={17} aria-hidden />
                          <span>Customer Photo</span>
                        </span>
                      </TooltipTrigger>
                      <TooltipContent side="top" style={{ maxWidth: 250 }}>
                        Photo sourced from customer reviews. When limited visuals are available, it may not fully
                        represent the dish.
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                )}
              </div>
              {item.dishImage && !dishImageFailed && (
                <p className={styles.imageCaption}>
                  Generated from recurring patterns in customer reviews and photos using Nano Banana 3.
                </p>
              )}
              {showGenerateButton && (
                <p className={styles.imageCaption}>
                  {hasNoCollage
                    ? "No relevant customer photos available to generate a dish image."
                    : "Click to generate an image reflecting how this dish usually appears in review photos."}
                </p>
              )}
              {showGenerateButton && (
                <button
                  className={styles.generateButton}
                  disabled={nanobananaGenerating || hasNoCollage}
                  onClick={handleGenerateNanobanana}
                >
                  {nanobananaGenerating ? (
                    <>
                      <Loader2 className={styles.generateButtonIconSpin} aria-hidden />
                      Generating…
                    </>
                  ) : (
                    <>
                      <Image
                        src={sparklesSvg}
                        alt=""
                        width={16}
                        height={15}
                        className={styles.generateButtonIcon}
                        aria-hidden
                      />
                      Show Me the Dish
                    </>
                  )}
                </button>
              )}
              {item.nanobananaNoImage && (
                <p className={styles.imageCaption}>Gemini was not able to find this menu from the review photos.</p>
              )}
            </div>

            {/* Customer Photos Section – hidden when no collage images found */}
            {!hasNoCollage && (
              <div className={styles.customerPhotosSection}>
                <h3 className={styles.customerPhotosTitle}>Customer Photos</h3>
                <div className={styles.imageCaption}>
                  Photos sourced from customer reviews. Tap any image to view the review it came from.
                </div>
                <div className={styles.customerPhotosGrid}>
                  {item.collageImages?.map((imgSrc: string, i: number) => {
                    const isBroken = brokenCollageIndices.has(i);
                    const showImage = imgSrc && !isBroken;
                    const reviewUrl = item.collageImageUrls?.[i];
                    const photoContent = showImage ? (
                      <Image
                        src={imgSrc}
                        alt={`Customer photo ${i + 1}`}
                        fill
                        sizes="120px"
                        className={styles.customerPhotoImage}
                        onError={() => handleCollageImageError(i)}
                        unoptimized
                      />
                    ) : (
                      <ImageOff className={styles.customerPhotoPlaceholder} aria-hidden />
                    );
                    return reviewUrl && showImage ? (
                      <a
                        key={i}
                        href={reviewUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.customerPhotoCell}
                        title="View source review"
                      >
                        {photoContent}
                      </a>
                    ) : (
                      <div key={i} className={styles.customerPhotoCell}>
                        {photoContent}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Dish Info */}
          <div className={styles.infoSection}>
            {/* Dish Header */}
            <div className={styles.dishHeader}>
              <h1 className={styles.dishName}>{from_menuboard.name}</h1>
              <p className={styles.dishDescription}>{from_menuboard.description}</p>
            </div>

            {/* AI Summary */}
            {from_reviews?.objective_summary && (
              <div className={styles.aiSummaryBlock}>
                <div className={styles.aiSummaryHeader}>
                  <h2 className={styles.aiSummaryTitle}>AI Summary</h2>
                  <Image
                    src={sparklesSvg}
                    alt=""
                    width={20}
                    height={19}
                    className={styles.aiSummarySparkle}
                    aria-hidden
                  />
                </div>
                <div className={styles.aiSummaryCard}>
                  {!aiSummaryRevealed ? (
                    <div className="flex w-full flex-col gap-2">
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-full" />
                      <Skeleton className="h-4 w-3/4" />
                    </div>
                  ) : (
                    <p className={styles.aiSummaryText}>{from_reviews.objective_summary}</p>
                  )}
                </div>
              </div>
            )}

            {/* Different Notes */}
            {from_reviews?.diff_notes &&
              from_reviews.diff_notes.length > 0 &&
              (() => {
                // Build prefix-sum offsets so source numbering is continuous across all notes
                const diffNotes = from_reviews.diff_notes as any[];
                const noteOffsets: number[] = [];
                let runningTotal = 0;
                for (const note of diffNotes) {
                  noteOffsets.push(runningTotal);
                  runningTotal += Array.isArray(note.evidence_review_ids) ? note.evidence_review_ids.length : 0;
                }
                return (
                  <div className={styles.differentNotesSection}>
                    <h2 className={styles.sectionTitleSmall}>Reviewers Commented</h2>
                    <div className={styles.differentNotesList}>
                      {diffNotes.map((note: any, i: number) => (
                        <div key={i} className={styles.differentNotesCard}>
                          <div className={styles.claimContent}>
                            <p className={styles.claimText}>{note.note}</p>
                            {Array.isArray(note.evidence_review_ids) && note.evidence_review_ids.length > 0 && (
                              <div className={styles.sourceLinksRow}>
                                {note.evidence_review_ids.map((reviewId: number, idx: number) => {
                                  const sourceNum = noteOffsets[i] + idx + 1;
                                  return (
                                    <a
                                      key={reviewId}
                                      href={reviewIdToUrl[reviewId] ?? "#"}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className={`${styles.claimLink} ${styles.differentNotesLink}`}
                                    >
                                      Source Review {sourceNum} <ExternalLink className={styles.claimLinkIcon} />
                                    </a>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}

            {/* Dietary Insight – component in separate file; uses mock when dietary_options empty */}
            {(dietary_options != null || from_reviews != null) && (
              <DietaryInsightSection
                item={item}
                reviewIdToUrl={reviewIdToUrl}
                reviewersCommentedSourceCount={
                  from_reviews?.diff_notes?.reduce(
                    (sum, note) =>
                      sum + (Array.isArray(note.evidence_review_ids) ? note.evidence_review_ids.length : 0),
                    0,
                  ) ?? 0
                }
              />
            )}

            {/* Ingredients */}
            {from_reviews?.ingredients_by_category != null && (
              <div className={styles.ingredientsSection}>
                <h2 className={styles.sectionTitleSmall}>Ingredients</h2>
                <div className={styles.ingredientsList}>
                  {(() => {
                    const entries = Object.entries(from_reviews.ingredients_by_category).filter(
                      (entry): entry is [string, string[]] => Array.isArray(entry[1]) && entry[1].length > 0,
                    );
                    if (entries.length === 0) {
                      return <span className={styles.ingredientsNa}>N/A</span>;
                    }
                    return entries.map(([cat, ings]) => {
                      const iconInfo = INGREDIENT_CATEGORY_ICONS[cat];
                      return (
                        <div key={cat} className={styles.ingredientRow}>
                          {iconInfo ? (
                            <span className={styles.ingredientIcon}>
                              <Image src={iconInfo.src} alt={iconInfo.alt} width={20} height={20} />
                            </span>
                          ) : (
                            <span className={`${styles.ingredientDot} ${getIngredientDotClass(cat)}`}></span>
                          )}
                          <span>{toTitleCase(ings.join(", "))}</span>
                        </div>
                      );
                    });
                  })()}
                </div>
              </div>
            )}

            {/* Options */}
            {from_menuboard.options != null && (
              <div className={styles.optionsSection}>
                <h2 className={styles.sectionTitleSmall}>Options</h2>
                {(() => {
                  const optionsSource = from_menuboard.options;
                  const entries = Object.entries(optionsSource).filter(
                    (entry): entry is [string, string[]] => Array.isArray(entry[1]) && entry[1].length > 0,
                  );
                  if (entries.length === 0) {
                    return <span className={styles.optionsNa}>N/A</span>;
                  }
                  return entries.map(([key, vals]) => {
                    const meta = OPTION_CATEGORY_ICONS[key];
                    const label = meta?.label ?? key.replace(/_/g, " ");
                    return (
                      <div key={key} className={styles.optionGroup}>
                        <span className={styles.optionLabel}>
                          {meta ? (
                            <span className={styles.optionLabelIconWrap}>
                              <Image src={meta.src} alt={meta.alt} width={20} height={20} />
                            </span>
                          ) : (
                            <UtensilsCrossed className={styles.optionLabelIcon} />
                          )}
                          {label}
                        </span>
                        <div className={styles.optionBadges}>
                          {vals.map((val: string, i: number) => (
                            <span key={i} className={styles.optionBadge}>
                              {toTitleCase(val)}
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  });
                })()}
              </div>
            )}
          </div>
        </div>
        <div className={styles.reviewsSection}>
          <h2 className={styles.reviewsTitle}>Customer Reviews</h2>
          {reviewsLoading ? (
            <div className={styles.reviewsLoading}>
              <Loader2 className={styles.reviewsLoadingIcon} aria-hidden />
              <span>Loading reviews…</span>
            </div>
          ) : reviewsError ? (
            <p className={styles.reviewsError}>{reviewsError}</p>
          ) : reviews?.length ? (
            <>
              <div className={styles.reviewsGrid}>
                {reviews.slice(0, reviewsToShow).map((review, i) => (
                  <div key={i} className={styles.reviewCard}>
                    <p className={styles.reviewText}>{review.text}</p>
                    {review.publishedDate && <p className={styles.reviewDate}>{review.publishedDate}</p>}
                  </div>
                ))}
              </div>
              {reviews.length > reviewsToShow && (
                <Button variant="outline" className={styles.loadMoreReviewsButton} onClick={handleLoadMoreReviews}>
                  Load More Reviews
                </Button>
              )}
            </>
          ) : (
            <p className={styles.reviewsNa}>No reviews yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function DetailPage() {
  return (
    <Suspense
      fallback={
        <div className={styles.fallback}>
          <Loader2 className={styles.fallbackIcon} aria-hidden />
        </div>
      }
    >
      <DetailPageContentWithKey />
    </Suspense>
  );
}

function DetailPageContentWithKey() {
  const searchParams = useSearchParams();
  const id = searchParams.get("id");
  return <DetailPageContent key={id} />;
}
