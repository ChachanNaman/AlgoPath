import React from "react";
import styles from "./Navbar.module.css";

export default function Navbar({ title = "" }) {
  return (
    <header className={styles.nav}>
      <h1 className={styles.title}>{title}</h1>
    </header>
  );
}

// Quick manual test:
// - Import Navbar somewhere and ensure it renders without errors.

