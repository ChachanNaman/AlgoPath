import { useContext } from "react";
import { AuthContext } from "../context/AuthContext.jsx";

export default function useAuth() {
  const ctx = useContext(AuthContext);
  return ctx;
}

// Quick manual test:
// - In a component, call `const { user, isAuthenticated } = useAuth();`

