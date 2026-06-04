import { NavLink, Outlet } from "react-router-dom";
import { Title } from "@tremor/react";

const subNav = [
  { to: "/settings/profile", label: "Profile" },
  { to: "/settings/team", label: "Team" },
  { to: "/settings/integrations", label: "Integrations" },
  { to: "/settings/notifications", label: "Notifications" },
];

export function Settings() {
  return (
    <div>
      <Title className="font-ui">Settings</Title>

      <div className="mt-6 flex items-center gap-1 border-b border-white/5">
        {subNav.map((s) => (
          <NavLink
            key={s.to}
            to={s.to}
            className={({ isActive }) =>
              [
                "px-4 py-2 text-sm border-b-2 -mb-px",
                isActive
                  ? "border-viberoi-accent text-viberoi-accent"
                  : "border-transparent text-viberoi-sub hover:text-viberoi-text",
              ].join(" ")
            }
          >
            {s.label}
          </NavLink>
        ))}
      </div>

      <div className="mt-6">
        <Outlet />
      </div>
    </div>
  );
}
