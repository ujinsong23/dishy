"use client";

import React from "react";
import Image from "next/image";
import { CheckCircle2, ExternalLink } from "lucide-react";
import DietaryBadge from "../../components/DietaryBadge";
import type { DietaryOptionValue } from "../../store/useStore";
import styles from "./Detail.module.css";
import reportedByCustomerSvg from "../../assets/reported by customer.svg";
import mixedSignalSvg from "../../assets/mixed signal.svg";
import mentionedInMenuSvg from "../../assets/mentioned in menu.svg";

function toTitleCase(s: string): string {
  return s.toLowerCase().replace(/(?:^|[\s-])\w/g, (c) => c.toUpperCase());
}

export interface DietaryInsightSectionProps {
  item: {
    from_menuboard: unknown;
    from_reviews?: { diff_notes?: Array<{ evidence_review_ids?: number[] }> };
    dietary_options?: Record<string, DietaryOptionValue>;
  } | null;
  reviewIdToUrl: Record<number, string>;
  /** Number of source review links in Reviewers Commented so Dietary continues numbering after */
  reviewersCommentedSourceCount: number;
}

export default function DietaryInsightSection({
  item,
  reviewIdToUrl,
  reviewersCommentedSourceCount,
}: DietaryInsightSectionProps) {
  const dietary_options = item?.dietary_options;
  const source = dietary_options ?? {};
  const entries = Object.entries(source).filter(
    (entry): entry is [string, NonNullable<(typeof source)[string]>] => entry[1] != null,
  );
  let dietarySourceOffset = 0;

  if (entries.length === 0) {
    return (
      <div className={styles.dietaryClaimSection}>
        <h2 className={styles.sectionTitleSmall}>Dietary Insight</h2>
        <p className={styles.dietaryInsightSubtitle}>
          Inferred from menu details and customer reviews. We recommend checking the original review to verify the
          dietary option is accurate and relevant to this dish.
        </p>
        <p className={styles.dietaryClaimNa}>N/A</p>
      </div>
    );
  }

  return (
    <div className={styles.dietaryClaimSection}>
      <h2 className={styles.sectionTitleSmall}>Dietary Insight</h2>
      <p className={styles.dietaryInsightSubtitle}>
        Inferred from menu details and customer reviews. We recommend checking the original review to verify the dietary
        option is accurate and relevant to this dish.
      </p>
      <div className={styles.claimsList}>
        {entries.map(([claimKey, data]) => {
          if (!data) return null;
          const tag = data.tag;
          const evidence = data.evidences ?? [];
          const statusLabel =
            tag === "verified"
              ? "Review Verified"
              : tag === "warning"
                ? "Mixed Signal"
                : tag === "info"
                  ? "Reported by Customer"
                  : tag === "not_verified"
                    ? "Mentioned in Menu"
                    : "";
          const cardSourceStart = dietarySourceOffset;
          dietarySourceOffset += evidence.length;
          const pillClass =
            tag === "verified"
              ? `${styles.claimStatusPill} ${styles.claimStatusPillVerified}`
              : tag === "warning"
                ? `${styles.claimStatusPill} ${styles.claimStatusPillWarning}`
                : tag === "info"
                  ? `${styles.claimStatusPill} ${styles.claimStatusPillInfo}`
                  : `${styles.claimStatusPill} ${styles.claimStatusPillMentioned}`;
          const badgeVariant = tag === "not_verified" ? "info" : (tag as "verified" | "warning" | "info");
          return (
            <div key={claimKey} className={styles.claimBadgeCardPair}>
              <div
                className={tag === "warning" ? `${styles.claimCard} ${styles.claimCardConflicting}` : styles.claimCard}
              >
                <div className={styles.claimCardHeader}>
                  <DietaryBadge label={toTitleCase(claimKey)} variant={badgeVariant} />
                  {statusLabel && (
                    <span className={pillClass}>
                      {tag === "verified" && <CheckCircle2 className={styles.claimStatusPillIcon} aria-hidden />}
                      {tag === "warning" && (
                        <Image
                          src={mixedSignalSvg}
                          alt=""
                          width={16}
                          height={16}
                          className={styles.claimStatusPillIcon}
                          aria-hidden
                        />
                      )}
                      {tag === "info" && (
                        <Image
                          src={reportedByCustomerSvg}
                          alt=""
                          width={16}
                          height={16}
                          className={styles.claimStatusPillIcon}
                          aria-hidden
                        />
                      )}
                      {tag === "not_verified" && (
                        <Image
                          src={mentionedInMenuSvg}
                          alt=""
                          width={16}
                          height={16}
                          className={styles.claimStatusPillIcon}
                          aria-hidden
                        />
                      )}
                      {statusLabel}
                    </span>
                  )}
                </div>
                <div className={styles.claimCardContent}>
                  <div className={styles.claimContent}>
                    {evidence.length > 0 ? (
                      <>
                        {evidence.map((e, idx) => {
                          const sourceNum = reviewersCommentedSourceCount + cardSourceStart + idx + 1;
                          return (
                            <div key={idx} className={styles.claimEvidenceBlock}>
                              <p className={styles.claimText}>
                                <em>&ldquo;{e.quote}&rdquo;</em>
                              </p>
                              <div className={styles.sourceLinksRow}>
                                <a
                                  href={reviewIdToUrl[e.review_id] ?? "#"}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className={`${styles.claimLink} ${styles.differentNotesLink}`}
                                >
                                  Source Review {sourceNum} <ExternalLink className={styles.claimLinkIcon} />
                                </a>
                              </div>
                            </div>
                          );
                        })}
                      </>
                    ) : (
                      <></>
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
