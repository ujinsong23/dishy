"use client";

import { useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import styles from "./AppBreadcrumb.module.css";

type AppBreadcrumbProps =
  | { variant: "change-restaurant" }
  | { variant: "detail"; restaurantName: string; dishName: string };

export default function AppBreadcrumb(props: AppBreadcrumbProps) {
  const router = useRouter();

  return (
    <div className={styles.breadcrumbWrap}>
      <div className={styles.breadcrumb}>
      <Button
        variant="outline"
        size="icon"
        onClick={() => router.back()}
        className={styles.breadcrumbChevron}
        aria-label="Go back"
      >
        <ChevronLeft className={styles.chevronIcon} aria-hidden />
      </Button>
      {props.variant === "change-restaurant" ? (
        <span>Change Restaurant</span>
      ) : (
        <>
          <span className={styles.breadcrumbRestaurant}>{props.restaurantName}</span>
          <span className={styles.breadcrumbSep}>/</span>
          <span className={styles.breadcrumbCurrent}>{props.dishName}</span>
        </>
      )}
      </div>
    </div>
  );
}
