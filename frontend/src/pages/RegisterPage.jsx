import React, { useContext, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api.js";
import { AuthContext } from "../context/AuthContext.jsx";
import styles from "./RegisterPage.module.css";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const res = await api.post("/api/auth/register", {
        name,
        email,
        password,
      });
      login(res.data.token, res.data.user);
      navigate("/dashboard");
    } catch (err) {
      setError(err?.response?.data?.message || "Registration failed. Please try again.");
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
          <h2 className={styles.cardTitle}>Create your account</h2>

          <form className={styles.form} onSubmit={onSubmit}>
            <label className={styles.label}>
              Name
              <input
                className={styles.input}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                autoComplete="name"
              />
            </label>

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
                placeholder="Create a password"
                autoComplete="new-password"
              />
            </label>

            <label className={styles.label}>
              Confirm Password
              <input
                className={styles.input}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                type="password"
                placeholder="Confirm your password"
                autoComplete="new-password"
              />
            </label>

            {error ? <div className={styles.error}>{error}</div> : null}

            <button className={styles.primaryBtn} type="submit" disabled={loading}>
              {loading ? <span className={styles.spinner} /> : "Register"}
            </button>

            <div className={styles.footer}>
              <span>Already have an account?</span>{" "}
              <Link className={styles.link} to="/">
                Login
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Quick manual test:
// - Fill name/email/password/confirm on `/register`
// - Should create account + navigate to `/dashboard`

