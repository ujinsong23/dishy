"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import Image from "next/image";
import { useSearchParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Hourglass, AlertCircle } from "lucide-react";
import loadingAnimationGif from "../assets/Loading Animation v2.gif";
import sparklesSvg from "../assets/sparkles.svg";
import dishyPickLogo from "../assets/dishy pick logo.svg";
import { runReviewScraping, runMenuListing, runMatchAndSummarize } from "./pipeline";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import styles from "./Process.module.css";
import detailStyles from "../results/detail/Detail.module.css";

import { useRestaurantStore } from "../store/useStore";
import AppBreadcrumb from "../components/AppBreadcrumb";

/** How many reviews are visible in the viewport at once */
const VISIBLE_COUNT = 3;
/** Interval between each single-review rotation (ms) */
const ROTATE_INTERVAL_MS = 3000;

/** Extracts display text from a review (string | { text: string }) */
function getReviewText(rev: unknown): string {
  if (typeof rev === "string") return rev;
  if (typeof rev === "object" && rev !== null && "text" in rev) return (rev as { text: string }).text;
  return String(rev);
}

/** Extracts & formats date from a review object when available */
function getReviewDate(rev: unknown): string | null {
  if (typeof rev !== "object" || rev === null) return null;
  const d = (rev as Record<string, unknown>).publishedAtDate;
  if (!d) return null;
  try {
    return new Date(d as string).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return null;
  }
}

/**
 * Continuous vertical ticker — always shows VISIBLE_COUNT reviews.
 * Every interval the top card slides out and a new one slides in from the bottom,
 * cycling endlessly through all reviews.
 */
function ReviewCarousel({ reviews }: { reviews: unknown[] }) {
  const total = reviews.length;
  // `offset` is the index of the first visible review; advances by 1 each tick
  const [offset, setOffset] = useState(0);

  const advance = useCallback(() => {
    setOffset((o) => (o + 1) % total);
  }, [total]);

  useEffect(() => {
    if (total <= VISIBLE_COUNT) return;
    const id = setInterval(advance, ROTATE_INTERVAL_MS);
    return () => clearInterval(id);
  }, [advance, total]);

  // Build the visible window, wrapping around if necessary
  const visible: { rev: unknown; idx: number }[] = [];
  for (let i = 0; i < Math.min(VISIBLE_COUNT, total); i++) {
    const idx = (offset + i) % total;
    visible.push({ rev: reviews[idx], idx });
  }

  return (
    <motion.div
      className={styles.reviewArea}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
    >
      <div className={styles.tickerViewport}>
        <AnimatePresence initial={false}>
          {visible.map(({ rev, idx }, i) => {
            const text = getReviewText(rev);
            const formattedDate = getReviewDate(rev);
            return (
              <motion.div
                key={idx}
                layout
                className={styles.carouselCard}
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -40 }}
                transition={{ duration: 0.45, ease: "easeInOut" }}
              >
                <motion.div
                  animate={{ y: [0, -8, 0] }}
                  transition={{
                    duration: 2.5,
                    repeat: Infinity,
                    repeatType: "reverse",
                    ease: "easeInOut",
                    delay: i * 0.2,
                  }}
                >
                  <div className={`${detailStyles.reviewCard} ${styles.loadingReviewCard}`}>
                    <p className={detailStyles.reviewText}>{text}</p>
                    {formattedDate && <p className={detailStyles.reviewDate}>{formattedDate}</p>}
                  </div>
                  <div className={styles.shimmerOverlay} />
                </motion.div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// Guard so pipeline runs only once per placeId (avoids duplicate calls from React Strict Mode in dev)
let pipelineStartedForPlaceId: string | null = null;

function ProcessPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const placeIdFromUrl = searchParams.get("id");
  const initialReviews = searchParams.get("reviews");
  const initialName = searchParams.get("name");

  const {
    placeId,
    setPlaceId,
    setRestaurantInfo,
    menuData,
    setMenuData,
    progress,
    setProgress,
    phase,
    setPhase,
    error,
    setError,
    scrapingData,
    setScrapingData,
    setRestaurantOverview,
  } = useRestaurantStore();

  useEffect(() => {
    if (!placeIdFromUrl) return;

    // Sync URL params to store if not already set
    if (placeIdFromUrl !== placeId) {
      setPlaceId(placeIdFromUrl);
      if (initialName || initialReviews) {
        const nameToSet = initialName ? decodeURIComponent(initialName) : "Restaurant";
        setRestaurantInfo(nameToSet, initialReviews ? parseInt(initialReviews) : 0);
        setScrapingData({
          count: initialReviews ? parseInt(initialReviews) : 0,
          restaurantName: initialName || undefined,
          messages: ["Looking for dish mentions, descriptions, and photos..."],
          reviews: [],
        });
      }
    }
  }, [placeIdFromUrl, initialName, initialReviews, placeId, setPlaceId, setRestaurantInfo, setScrapingData]);

  // Dynamic progress effect (trickle)
  useEffect(() => {
    if (progress >= 95) return;

    const interval = setInterval(() => {
      setProgress(Math.min(progress + Math.random() * 0.5, 95));
    }, 500);

    return () => clearInterval(interval);
  }, [progress, setProgress]);

  useEffect(() => {
    if (!placeIdFromUrl || (menuData && phase !== "scraping" && phase !== "analysis")) return;
    // Reset guard when user navigated to a different place (so same place can re-run if they come back)
    if (pipelineStartedForPlaceId !== null && pipelineStartedForPlaceId !== placeIdFromUrl) {
      pipelineStartedForPlaceId = null;
    }
    if (pipelineStartedForPlaceId === placeIdFromUrl) return;
    pipelineStartedForPlaceId = placeIdFromUrl;

    const processPipeline = async () => {
      try {
        // Step 1: Review Scraping
        const nameFromUrl = initialName ? decodeURIComponent(initialName) : "";
        const scrapingRes = await runReviewScraping(placeIdFromUrl, nameFromUrl || undefined);

        // Prefer backend restaurant_name; fall back to name from URL (search) when backend doesn't return it
        const restaurantNameToUse = scrapingRes.restaurant_name || nameFromUrl || "Restaurant";
        // Keep user_ratings_total from search (initialReviews) when available; else use backend review_count
        const reviewCountToUse = initialReviews ? parseInt(initialReviews, 10) : (scrapingRes.review_count ?? 0);

        setPhase("analysis");
        setScrapingData({
          restaurantName: restaurantNameToUse,
          reviews: scrapingRes.review_examples || [],
          count: reviewCountToUse,
          messages: ["Looking for dish mentions, descriptions, and photos..."],
        });
        const imageCountFromScraping = (scrapingRes as { image_count?: number }).image_count ?? 0;
        setRestaurantInfo(restaurantNameToUse, reviewCountToUse, imageCountFromScraping);
        setProgress(30);

        // Step 2: Menu Listing
        // Response shape per menu item: { from_menuboard, from_reviews, dietary_options }
        const menuRes = await runMenuListing(placeIdFromUrl);
        setMenuData(menuRes.menus);
        setProgress(50);

        // Step 3: Match & Summarize (Wait for this before showing results)
        // Same shape: { from_menuboard, from_reviews, dietary_options } per item
        const summaryRes = await runMatchAndSummarize(placeIdFromUrl);
        if (summaryRes.menus) {
          setMenuData(summaryRes.menus); // Upgrade menu data with summaries
        }

        // Save Restaurant Overview from API (summary_html & glossary)
        const overview = summaryRes.restaurant_overview;
        if (overview && (overview.summary_html != null || overview.glossary != null)) {
          setRestaurantOverview({
            summary_html: overview.summary_html ?? "",
            glossary: overview.glossary ?? {},
          });
        }

        setProgress(100);
        setPhase("results-preview");

        // Store already has restaurantName, reviewCount, imageCount, menuData — results page uses them.
        // Persist to sessionStorage so results page can rehydrate on refresh (no URL params).
        const meta = {
          restaurantName: restaurantNameToUse,
          reviewCount: reviewCountToUse,
          imageCount: (scrapingRes as { image_count?: number }).image_count ?? 0,
        };
        try {
          sessionStorage.setItem(`restaurant_meta_${placeIdFromUrl}`, JSON.stringify(meta));
        } catch (e) {
          // ignore quota / private mode
        }
        router.replace(`/results?place_id=${encodeURIComponent(placeIdFromUrl)}`);
      } catch (err: any) {
        console.error("Pipeline error:", err);
        // If the error is "Insufficient reviews", redirect back to home with the message
        if (err.code === "Insufficient reviews" || err.message?.includes("Expected at least")) {
          const msg = err.message || "This restaurant doesn't have enough reviews to analyze.";
          router.replace(`/?error=${encodeURIComponent(msg)}`);
          return;
        }
        setError(err.message || "An unexpected error occurred during processing.");
      }
    };

    processPipeline();
  }, [placeIdFromUrl]);

  if (error) {
    return (
      <main className={styles.main}>
        <div className={styles.contentWrapper}>
          <div className={styles.errorHeader}>
            <AlertCircle className={styles.errorHeaderIcon} aria-hidden />
            <span className={styles.errorTitle}>Processing Error</span>
          </div>
          <p className={styles.errorMessage}>{error}</p>
          <Button onClick={() => window.location.reload()} variant="default" size="default">
            Try Again
          </Button>
        </div>
      </main>
    );
  }

  const getSuccessScrapedMessage = (count: number) =>
    count > 500
      ? `Successfully scraped the most relevant 500 out of ${count} reviews`
      : `Successfully scraped ${count} reviews`;

  const getTitle = () => {
    switch (phase) {
      case "scraping":
        return "Collecting customer reviews...";
      case "analysis":
        return "Analyzing customer reviews...";
      default:
        return "Finalizing results...";
    }
  };

  const getStatusMessages = () => {
    if (phase === "analysis") {
      return ["Understanding what people are talking about...", "This may take up to 5 mintues"];
    }
    const count = scrapingData?.count ?? 0;
    const rest = scrapingData?.messages ?? [];
    return [getSuccessScrapedMessage(count), ...rest];
  };

  return (
    <main className={styles.mainProgress}>
      <AppBreadcrumb variant="change-restaurant" />
      <motion.div
        className={styles.contentWrapper}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className={styles.progressSection}>
          <div className={styles.progressSectionLeft}>
            <Image src={dishyPickLogo} alt="" width={48} height={48} className={styles.progressIcon} aria-hidden />
          </div>
          <div className={styles.progressSectionRight}>
            <div className={styles.titleRow}>
              <h1 className={styles.title}>{getTitle()}</h1>
              <Image src={sparklesSvg} alt="" width={20} height={20} className={styles.titleSparkle} aria-hidden />
            </div>
            <div className={styles.progressWrap}>
              <Progress value={progress} className={styles.progressBar} />
            </div>
            <p className={styles.subtitle}>
              {phase === "analysis"
                ? "This may take a moment. We're interpreting photos and information of dishes clearly."
                : "This may take a moment. We're gathering what customers actually wrote and shared."}
            </p>
          </div>
        </div>

        <>
          <div className={styles.statusArea}>
            <AnimatePresence mode="wait">
              <motion.div
                key={phase + (scrapingData ? "data" : "nodata")}
                className={styles.statusMessageContainer}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4 }}
              >
                {getStatusMessages().map((msg: string, idx: number) => (
                  <span
                    key={idx}
                    className={idx === 0 && phase !== "analysis" ? styles.successMessage : styles.nextStepMessage}
                  >
                    {msg}
                  </span>
                ))}
              </motion.div>
            </AnimatePresence>
          </div>

          {phase === "analysis" && scrapingData?.reviews && scrapingData.reviews.length > 0 ? (
            <ReviewCarousel reviews={scrapingData.reviews} />
          ) : (
            <div className={styles.centerGraphic}>
              <Image
                src={loadingAnimationGif}
                alt=""
                width={600}
                height={431}
                className={styles.loadingAnimationGif}
                unoptimized
                aria-hidden
              />
            </div>
          )}
        </>
      </motion.div>
    </main>
  );
}

export default function ProcessPage() {
  return (
    <Suspense
      fallback={
        <main className={styles.main}>
          <div className={styles.contentWrapper}>
            <h1 className={styles.title}>Initializing...</h1>
            <Progress value={5} className={styles.progressBar} />
            <div className={styles.fallbackSpinner}>
              <Hourglass className={styles.fallbackSpinnerIcon} aria-hidden />
            </div>
          </div>
        </main>
      }
    >
      <ProcessPageContent />
    </Suspense>
  );
}
