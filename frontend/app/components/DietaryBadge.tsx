"use client";

import React from "react";
import Image from "next/image";
import { cn } from "@/lib/utils";
import styles from "./DietaryBadge.module.css";

import veganIcon from "../assets/vegan.svg";
import glutenFreeIcon from "../assets/gluten free.svg";
import dairyFreeIcon from "../assets/dairy free.svg";
import nutFreeIcon from "../assets/nut free.svg";
import eggFreeIcon from "../assets/egg free.svg";
import vegetarianIcon from "../assets/vegeterian.svg";
import halalIcon from "../assets/halal.svg";
import kosherIcon from "../assets/kosher.svg";

export const DIETARY_OPTIONS = [
  "vegan",
  "gluten-free",
  "dairy-free",
  "nut-free",
  "egg-free",
  "vegetarian",
  "halal",
  "kosher",
] as const;

export type DietaryOption = (typeof DIETARY_OPTIONS)[number];

const DIETARY_ICONS: Record<string, string> = {
  vegan: veganIcon,
  "gluten-free": glutenFreeIcon,
  "dairy-free": dairyFreeIcon,
  "nut-free": nutFreeIcon,
  "egg-free": eggFreeIcon,
  vegetarian: vegetarianIcon,
  halal: halalIcon,
  kosher: kosherIcon,
};

function formatLabel(key: string): string {
  return key
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

interface DietaryBadgeProps {
  /** One of the eight dietary options (e.g. "vegan", "gluten-free") */
  label: string;
  /** Optional variant for Dietary Insight status (badge color matches status) */
  variant?: "verified" | "warning" | "info" | "default";
  className?: string;
}

export default function DietaryBadge({ label, variant = "default", className }: DietaryBadgeProps) {
  const normalizedKey = label.toLowerCase().replace(/\s+/g, "-");
  const iconSrc = DIETARY_ICONS[normalizedKey];
  const displayLabel = formatLabel(normalizedKey);
  const variantClass =
    variant === "verified"
      ? styles.badgeVerified
      : variant === "warning"
        ? styles.badgeWarning
        : variant === "info"
          ? styles.badgeInfo
          : undefined;

  return (
    <span className={cn(styles.badge, variantClass, className)}>
      {iconSrc ? (
        <Image src={iconSrc} alt="" width={12} height={12} className={styles.icon} aria-hidden />
      ) : null}
      <span>{displayLabel}</span>
    </span>
  );
}
