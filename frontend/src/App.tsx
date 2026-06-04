import { Navigate, Route, Routes } from "react-router-dom";

import { Shell } from "./components/Shell";
import { useAuth } from "./auth/AuthContext";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Sessions } from "./pages/Sessions";
import { SessionDetail } from "./pages/SessionDetail";
import { Sprints } from "./pages/Sprints";
import { SprintDetail } from "./pages/SprintDetail";
import { TicketDetail } from "./pages/TicketDetail";
import { Settings } from "./pages/Settings";
import { Profile } from "./pages/settings/Profile";
import { Integrations } from "./pages/settings/Integrations";
import { Notifications } from "./pages/settings/Notifications";

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Shell />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/sessions/:id" element={<SessionDetail />} />
        <Route path="/sprints" element={<Sprints />} />
        <Route path="/sprints/:id" element={<SprintDetail />} />
        <Route path="/tickets/:id" element={<TicketDetail />} />
        <Route path="/settings" element={<Settings />}>
          <Route index element={<Navigate to="/settings/profile" replace />} />
          <Route path="profile" element={<Profile />} />
          <Route path="integrations" element={<Integrations />} />
          <Route path="notifications" element={<Notifications />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
