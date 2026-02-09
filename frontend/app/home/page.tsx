"use client";

import { Suspense } from "react";
import Image from "next/image";
import { useSearchParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, X } from "lucide-react";
import SearchBox from "./SearchBox";
import styles from "./Home.module.css";
import howWorks1 from "../assets/how_works_1.svg";
import howWorks2 from "../assets/how_works_2.svg";
import howWorks3 from "../assets/how_works_3.svg";

function HomeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const errorMessage = searchParams.get("error");

  const dismissError = () => {
    // Remove the error param from the URL without a full reload
    router.replace("/", { scroll: false });
  };

  return (
    <main className={styles.main}>
      <motion.div
        className={styles.container}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      >
        <AnimatePresence>
          {errorMessage && (
            <motion.div
              className={styles.errorBanner}
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              role="alert"
            >
              <AlertCircle className={styles.errorBannerIcon} aria-hidden />
              <span className={styles.errorBannerText}>{errorMessage}</span>
              <button className={styles.errorBannerDismiss} onClick={dismissError} aria-label="Dismiss error">
                <X className={styles.errorBannerDismissIcon} aria-hidden />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <div className={styles.content}>
          <h1 className={styles.title}>
            Stop scrolling reviews. Start <em>seeing</em> dishes.
          </h1>
          <p className={styles.subtitle}>
            Discover a quick snapshot of dishes, built from real customer reviews and photos
          </p>
        </div>

        <div className={styles.searchArea}>
          <SearchBox />
        </div>

        <section className={styles.howItWorks}>
          <h2 className={styles.howItWorksTitle}>How Dishy Works</h2>
          <div className={styles.howItWorksRow}>
            <div className={styles.howItWorksCol}>
              <Image
                src={howWorks1}
                alt=""
                width={400}
                className={styles.howItWorksImage}
                sizes="(max-width: 640px) 100vw, 33vw"
              />
            </div>
            <div className={styles.howItWorksCol}>
              <Image
                src={howWorks2}
                alt=""
                width={400}
                className={styles.howItWorksImage}
                sizes="(max-width: 640px) 100vw, 33vw"
              />
            </div>
            <div className={styles.howItWorksCol}>
              <Image
                src={howWorks3}
                alt=""
                width={400}
                className={styles.howItWorksImage}
                sizes="(max-width: 640px) 100vw, 33vw"
              />
            </div>
          </div>
        </section>
      </motion.div>
    </main>
  );
}

export default function Home() {
  return (
    <Suspense>
      <HomeContent />
    </Suspense>
  );
}
