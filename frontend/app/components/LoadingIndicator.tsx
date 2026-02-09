"use client";

import React from "react";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import styles from "./LoadingIndicator.module.css";

export default function LoadingIndicator() {
  return (
    <div className={styles.wrapper}>
      <div className={styles.inner}>
        {/* Pulsing rings */}
        <motion.div
          animate={{
            scale: [1, 1.5, 1],
            opacity: [0.3, 0.1, 0.3],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className={styles.pulseRing}
        />
        <motion.div
          animate={{
            scale: [1.2, 1.8, 1.2],
            opacity: [0.2, 0, 0.2],
          }}
          transition={{
            duration: 2.5,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className={styles.pulseRingOuter}
        />

        {/* Lucide spinner + Framer rotation */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: "linear",
          }}
        >
          <Loader2 className={styles.spinnerIcon} aria-hidden />
        </motion.div>
      </div>

      <motion.p
        animate={{ opacity: [1, 0.5, 1] }}
        transition={{ duration: 2, repeat: Infinity }}
        className={styles.message}
      >
        Loading...
      </motion.p>
    </div>
  );
}
