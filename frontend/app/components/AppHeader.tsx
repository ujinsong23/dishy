import Image from "next/image";
import dishyTitleLogo from "../assets/dishy title logo.svg";
import styles from "./AppHeader.module.css";

export default function AppHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.headerInner}>
        <div className={styles.headerBrand}>
          <Image
            src={dishyTitleLogo}
            alt=""
            width={24}
            height={24}
            className={styles.headerLogo}
            priority
            aria-hidden
          />
          <span className={styles.headerTitle}>Dishy</span>
        </div>
      </div>
    </header>
  );
}
