"use client";

import { ReactNode } from "react";
import { usePathname } from "next/navigation";

const USERNAME = "Cathy";

const MENU = [
  { label: "Dashboard", href: "/", icon: "home" },
  { label: "Job Market Insight", href: "/insight", icon: "chart" },
  { label: "Master CV", href: "/cv", icon: "file" },
  { label: "Interview Practice", href: "/interview", icon: "chat" },
  { label: "Improvement Tips", href: "/tips", icon: "bulb" },
  { label: "Weekly Achievements", href: "/achievements", icon: "book" },
] as const;

function Icon({ name }: { name: string }) {
  const common = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  if (name === "home") {
    return (
      <svg {...common}>
        <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z" />
      </svg>
    );
  }
  if (name === "chart") {
    return (
      <svg {...common}>
        <path d="M4 19V10M10 19V5M16 19v-7M2 19h20" />
      </svg>
    );
  }
  if (name === "chat") {
    return (
      <svg {...common}>
        <path d="M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v6A2.5 2.5 0 0 1 16.5 15H12l-4 3.5V15H7.5A2.5 2.5 0 0 1 5 12.5z" />
      </svg>
    );
  }
  if (name === "bulb") {
    return (
      <svg {...common}>
        <path d="M9 18h6M9.5 21h5" />
        <path d="M8 14.5a5 5 0 1 1 8 0c-.7.8-1.2 1.6-1.4 2.5h-5.2c-.2-.9-.7-1.7-1.4-2.5z" />
      </svg>
    );
  }
  if (name === "spark") {
    return (
      <svg {...common}>
        <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.5 2.5M15.9 15.9l2.5 2.5M18.4 5.6l-2.5 2.5M8.1 15.9l-2.5 2.5" />
      </svg>
    );
  }
  if (name === "file") {
    return (
      <svg {...common}>
        <path d="M7 3.5h6.5L19 9v11.5a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1v-16a1 1 0 0 1 1-1z" />
        <path d="M13.5 3.5V9H19" />
      </svg>
    );
  }
  if (name === "book") {
    return (
      <svg {...common}>
        <path d="M5 5.5A2.5 2.5 0 0 1 7.5 3H20v16H7.5A2.5 2.5 0 0 0 5 21.5z" />
        <path d="M5 5.5A2.5 2.5 0 0 1 7.5 8H20" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4" />
    </svg>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="logo" aria-hidden="true">
            <Icon name="spark" />
          </span>
          <div>
            <div className="brand-name">
              Career<span>Assist</span>
            </div>
            <div className="brand-tag">Job Search · AI · Career Growth</div>
          </div>
        </div>
        <nav className="menu">
          {MENU.map((item) => {
            const active = pathname === item.href;
            return (
              <a key={item.label} className={active ? "menu-link active" : "menu-link"} href={item.href}>
                <Icon name={item.icon} />
                {item.label}
              </a>
            );
          })}
          <a
            className={pathname === "/settings" ? "menu-link settings active" : "menu-link settings"}
            href="/settings"
          >
            <Icon name="settings" />
            Settings
          </a>
        </nav>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <p>Welcome back, {USERNAME}</p>
          <div className="topbar-end">
            <nav className="account-links" aria-label="Account">
              <a className={pathname === "/register" ? "active" : undefined} href="/register">
                Register
              </a>
              <span aria-hidden="true">|</span>
              <a className={pathname === "/login" ? "active" : undefined} href="/login">
                Login
              </a>
            </nav>
            <span className="avatar" aria-label={`${USERNAME} avatar placeholder`}>
              {USERNAME.slice(0, 1)}
            </span>
          </div>
        </header>
        <div className="workspace-body">{children}</div>
      </div>
    </div>
  );
}
