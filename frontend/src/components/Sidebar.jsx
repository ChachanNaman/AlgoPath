import React, { useContext } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { AuthContext } from "../context/AuthContext.jsx";
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
    { to: "/dashboard/weak-topics", label: "Weak Topics", icon: makeNavIcon("M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3z") },
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
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? styles.navItemActive : styles.navItem)}
            >
              <Icon>{item.icon}</Icon>
              <span className={styles.label}>{item.label}</span>
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

