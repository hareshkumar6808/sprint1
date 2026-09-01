"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, BarChart3, TrendingUp, Briefcase, Eye, Newspaper, Brain, Zap, Clock } from "lucide-react";

const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "markets", label: "Markets", icon: TrendingUp },
  { id: "portfolio", label: "Portfolio", icon: Briefcase },
  { id: "watchlist", label: "Watchlist", icon: Eye },
  { id: "news", label: "News", icon: Newspaper },
  { id: "intelligence", label: "Intelligence", icon: Brain },
  { id: "decision-lab", label: "Decision Lab", icon: Zap },
  { id: "history", label: "History", icon: Clock },
];

interface AppSidebarProps {
  currentPage?: string;
  onNavigate?: (pageId: string) => void;
}

const PAGE_ROUTES: Record<string, string> = {
  overview: "/",
  markets: "/markets",
  portfolio: "/portfolio",
  watchlist: "/",
  news: "/news",
  intelligence: "/intelligence",
  "decision-lab": "/decision-lab",
  history: "/history",
};

export function AppSidebar({ onNavigate }: AppSidebarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  const isActive = (pageId: string) => {
    const route = PAGE_ROUTES[pageId];
    if (route === "/") return pathname === "/";
    return pathname.startsWith(route);
  };

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        className="btn-icon fixed top-1 left-1 z-50 lg:hidden"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle menu"
      >
        {isOpen ? <X size={18} /> : <Menu size={18} />}
      </button>

      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-20 z-40 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`sidebar ${isOpen ? "open" : ""}`}
        style={{
          position: "relative",
          left: isOpen ? 0 : "auto",
        }}
      >
        {/* Logo Area (optional - can be removed if in topbar) */}
        {/* <div style={{ padding: "1rem", borderBottom: "1px solid var(--border)" }} /> */}

        {/* Navigation */}
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const route = PAGE_ROUTES[item.id];
            return (
              <li key={item.id}>
                <Link
                  href={route}
                  className={isActive(item.id) ? "active" : ""}
                  onClick={() => {
                    onNavigate?.(item.id);
                    setIsOpen(false);
                  }}
                >
                  <Icon size={17} />
                  <span>{item.label}</span>
                </Link>
              </li>
            );
          })}
        </nav>

        {/* Footer */}
      </aside>
    </>
  );
}
