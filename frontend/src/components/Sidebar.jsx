import React, { useContext, useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { AuthContext } from "../context/AuthContext.jsx";
import api from "../services/api.js";
import styles from "./Sidebar.module.css";

function Icon({ children }) {
  return <span className={styles.icon}>{children}</span>;
}

function makeNavIcon(pathD) {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d={pathD} />
    </svg>
  );
}

export default function Sidebar() {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const location = useLocation();
  const userId = user?.email;

  const [dueCount, setDueCount] = useState(0);

  useEffect(() => {
    let mounted = true;
    async function loadDue() {
      if (!userId) return;
      try {
        const res = await api.get(`/api/quiz/due-reviews/${encodeURIComponent(userId)}`);
        if (!mounted) return;
        setDueCount(Number(res.data?.due_count || 0));
      } catch {
        // ignore
      }
    }
    loadDue();
    return () => {
      mounted = false;
    };
  }, [userId]);

  const initials = (user?.name || "U")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join("");

  const items = [
    { to: "/dashboard", label: "Home", icon: makeNavIcon("M3 12l9-9 9 9v9a2 2 0 0 1-2 2h-4v-7H9v7H5a2 2 0 0 1-2-2z") },
    { to: "/dashboard/playlist", label: "Playlist", icon: makeNavIcon("M8 5v14l11-7z") },
    { to: "/dashboard/playlist", label: "Quiz", icon: makeNavIcon("M5 4h10l4 4v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z") },
    { to: "/dashboard/quiz/review", label: "Review Queue", icon: makeNavIcon("M12 6V3L8 7l4 4V8c2.8 0 5 2.2 5 5a5 5 0 0 1-9.8 1H5.1A7 7 0 0 0 19 13c0-3.9-3.1-7-7-7z") },
    { to: "/dashboard/weak-topics", label: "Weak Topics", icon: makeNavIcon("M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3z") },
    { to: "/dashboard/knowledge-graph", label: "Knowledge Map", icon: makeNavIcon("M12 2l4 4-4 4-4-4 4-4zm-7 12l4 4-4 4-4-4 4-4zm14 0l4 4-4 4-4-4 4-4z") },
    { to: "/dashboard/timeline", label: "Timeline", icon: makeNavIcon("M12 8v4l3 3") },
    { to: "/dashboard/progress", label: "Progress", icon: makeNavIcon("M4 19h16M4 4h16v15H4z") },
    { to: "/dashboard/tutor", label: "AI Tutor", icon: makeNavIcon("M12 2l2 6 6 2-6 2-2 6-2-6-6-2 6-2z") },
    { to: "/dashboard/leaderboard", label: "Leaderboard", icon: makeNavIcon("M16 11l-4-4-4 4M12 7v10") },
  ];

  const onLogout = () => {
    logout();
    // Sidebar is only visible while authenticated, but keep it safe.
    if (location.pathname !== "/") navigate("/");
  };

  return (
    <>
      <aside className={styles.sidebar}>
        <div className={styles.top}>
          <div className={styles.logo}>
            <span className={styles.logoAlgo}>Algo</span>
            <span className={styles.logoPath}>Path</span>
          </div>
        </div>

        <nav className={styles.nav}>
          {items.map((item) => (
            <NavLink
              key={`${item.label}-${item.to}`}
              to={item.to}
              className={({ isActive }) => (isActive ? styles.navItemActive : styles.navItem)}
            >
              <Icon>{item.icon}</Icon>
              <span className={styles.label}>{item.label}</span>
              {item.label === "Review Queue" && dueCount > 0 ? <span className={styles.badge}>{dueCount}</span> : null}
            </NavLink>
          ))}
        </nav>

        <div className={styles.bottom}>
          <div className={styles.avatar}>{initials}</div>
          <div className={styles.userBlock}>
            <div className={styles.userName}>{user?.name || "User"}</div>
            <button className={styles.logoutBtn} type="button" onClick={onLogout}>
              Logout
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

// Quick manual test:
// - Login, then check sidebar links render and active item highlights.

