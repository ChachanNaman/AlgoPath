import React, { useContext } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar.jsx";
import { AuthContext } from "./context/AuthContext.jsx";

import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
//ddd
import DashboardHome from "./pages/DashboardHome.jsx";
import PlaylistPage from "./pages/PlaylistPage.jsx";
import QuizPage from "./pages/QuizPage.jsx";
import WeakTopicsPage from "./pages/WeakTopicsPage.jsx";
import TimelinePage from "./pages/TimelinePage.jsx";
import ProgressPage from "./pages/ProgressPage.jsx";
import AITutorPage from "./pages/AITutorPage.jsx";
import LeaderboardPage from "./pages/LeaderboardPage.jsx";

function DashboardLayout({ children }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main
        style={{
          marginLeft: 240,
          padding: 32,
          flex: 1,
          overflowY: "auto",
          maxWidth: 1200,
        }}
      >
        {children}
      </main>
    </div>
  );
}

function Protected({ children }) {
  const { isAuthenticated } = useContext(AuthContext);
  if (!isAuthenticated) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route
        path="/dashboard"
        element={
          <Protected>
            <DashboardLayout>
              <DashboardHome />
            </DashboardLayout>
          </Protected>
        }
      />
      <Route
        path="/dashboard/playlist"
        element={
          <Protected>
            <DashboardLayout>
              <PlaylistPage />
            </DashboardLayout>
          </Protected>
        }
      />
      <Route
        path="/dashboard/quiz/:video_id"
        element={
          <Protected>
            <DashboardLayout>
              <QuizPage />
            </DashboardLayout>
          </Protected>
        }
      />
      <Route
        path="/dashboard/weak-topics"
        element={
          <Protected>
            <DashboardLayout>
              <WeakTopicsPage />
            </DashboardLayout>
          </Protected>
        }
      />
      <Route
        path="/dashboard/timeline"
        element={
          <Protected>
            <DashboardLayout>
              <TimelinePage />
            </DashboardLayout>
          </Protected>
        }
      />
      <Route
        path="/dashboard/progress"
        element={
          <Protected>
            <DashboardLayout>
              <ProgressPage />
            </DashboardLayout>
          </Protected>
        }
      />
      <Route
        path="/dashboard/tutor"
        element={
          <Protected>
            <DashboardLayout>
              <AITutorPage />
            </DashboardLayout>
          </Protected>
        }
      />
      <Route
        path="/dashboard/leaderboard"
        element={
          <Protected>
            <DashboardLayout>
              <LeaderboardPage />
            </DashboardLayout>
          </Protected>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

// Quick manual test:
// - Login -> should land on `/dashboard` with Sidebar visible.
// - Directly open `/dashboard` while logged out -> should redirect to `/`.

