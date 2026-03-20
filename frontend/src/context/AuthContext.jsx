import React, { createContext, useCallback, useEffect, useMemo, useState } from "react";

export const AuthContext = createContext(null);

const TOKEN_KEY = "algopath_token";
const USER_KEY = "algopath_user";

function decodeJwtExp(token) {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    return payload?.exp ? Number(payload.exp) : null;
  } catch {
    return null;
  }
}

export default function AuthContextProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  });

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const login = useCallback((nextToken, nextUser) => {
    localStorage.setItem(TOKEN_KEY, nextToken);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser || null));
    setToken(nextToken);
    setUser(nextUser || null);
  }, []);

  useEffect(() => {
    if (!token) return;
    const exp = decodeJwtExp(token);
    if (!exp) return;
    const nowSec = Math.floor(Date.now() / 1000);
    if (nowSec >= exp) logout();
  }, [token, logout]);

  const value = useMemo(
    () => ({
      user,
      token,
      login,
      logout,
      isAuthenticated: Boolean(token),
    }),
    [user, token, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

