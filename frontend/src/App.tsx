import { Navigate, Route, Routes } from "react-router-dom";

import { Shell } from "./components/Shell";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Sessions } from "./pages/Sessions";
import { useAuth } from "./auth/AuthContext";

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
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
