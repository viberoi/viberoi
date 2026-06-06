import { Link, NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  ListTree,
  LogOut,
  Settings as SettingsIcon,
  Target,
  User as UserIcon,
  Zap,
} from "lucide-react";

import { useAuth } from "../auth/AuthContext";

const myActivityItem = {
  to: "/my-activity",
  label: "My activity",
  Icon: UserIcon,
};
const orgWideItems = [
  { to: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { to: "/sessions", label: "Sessions", Icon: ListTree },
  { to: "/sprints", label: "Sprints", Icon: Target },
];
const settingsItem = {
  to: "/settings",
  label: "Settings",
  Icon: SettingsIcon,
};

export function Shell() {
  const { user, logout } = useAuth();
  // Developers see only "My activity" + Settings. OrgAdmin + TeamLead see
  // everything (their own page first, then org-wide).
  const canSeeOrg = user?.role === "OrgAdmin" || user?.role === "TeamLead";
  const navItems = canSeeOrg
    ? [myActivityItem, ...orgWideItems, settingsItem]
    : [myActivityItem, settingsItem];
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 border-r border-white/5 bg-viberoi-card p-4 flex flex-col gap-1">
        <Link to="/dashboard" className="flex items-center gap-2 mb-6 px-2">
          <div className="w-8 h-8 rounded-md bg-viberoi-accent/10 border border-viberoi-accent/30 flex items-center justify-center">
            <Zap size={16} className="text-viberoi-accent" />
          </div>
          <span className="font-ui font-bold tracking-tight text-viberoi-text">
            VibeROI
          </span>
        </Link>
        <nav className="flex-1 flex flex-col gap-1">
          {navItems.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                [
                  "flex items-center gap-2 px-3 py-2 rounded-md text-sm",
                  isActive
                    ? "bg-viberoi-accent/10 text-viberoi-accent"
                    : "text-viberoi-sub hover:text-viberoi-text hover:bg-white/5",
                ].join(" ")
              }
            >
              <Icon size={16} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-white/5 pt-3 mt-3 text-xs text-viberoi-sub">
          <div className="px-2 mb-2 truncate" title={user?.email}>
            {user?.email}
            <div className="text-[10px] uppercase tracking-wider opacity-60">
              {user?.role}
            </div>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-2 px-3 py-2 w-full text-left rounded-md hover:bg-white/5 hover:text-viberoi-text"
          >
            <LogOut size={14} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
