import React, { useContext, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api.js";
import { AuthContext } from "../context/AuthContext.jsx";
import styles from "./LoginPage.module.css";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/api/auth/login", { email, password });
      login(res.data.token, res.data.user);
      navigate("/dashboard");
    } catch (err) {
      setError(err?.response?.data?.message || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.page}>
      <div className={styles.leftPane}>
        <div className={styles.floatCircle1} />
        <div className={styles.floatCircle2} />
        <div className={styles.floatCircle3} />

        <div className={styles.leftCenter}>
          <div className={styles.logo} aria-label="AlgoPath logo">
            <span className={styles.logoAlgo}>Algo</span>
            <span className={styles.logoPath}>Path</span>
          </div>
          <div className={styles.tagline}>Learn Smarter. Not Harder.</div>
        </div>
      </div>

      <div className={styles.rightPane}>
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>Welcome back</h2>

          <form className={styles.form} onSubmit={onSubmit}>
            <label className={styles.label}>
              Email
              <input
                className={styles.input}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                type="email"
                placeholder="you@example.com"
                autoComplete="email"
              />
            </label>

            <label className={styles.label}>
              Password
              <input
                className={styles.input}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                type="password"
                placeholder="Your password"
                autoComplete="current-password"
              />
            </label>

            {error ? <div className={styles.error}>{error}</div> : null}

            <button className={styles.primaryBtn} type="submit" disabled={loading}>
              {loading ? <span className={styles.spinner} /> : "Login"}
            </button>

            <div className={styles.footer}>
              <span>New here?</span>{" "}
              <Link className={styles.link} to="/register">
                Create an account
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Quick manual test:
// 1) Visit `/` (this page)
// 2) Register a user from `/register`
// 3) Login should navigate to `/dashboard`

