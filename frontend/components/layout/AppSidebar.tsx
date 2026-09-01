"use client";

import { useState } from "react";
import { Menu, X, BarChart3, TrendingUp, Briefcase, Eye, Newspaper, Brain, Zap, Clock, Settings, User } from "lucide-react";

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

const FOOTER_ITEMS = [
  { id: "settings", label: "Settings", icon: Settings },
  { id: "profile", label: "Profile", icon: User },
];

interface AppSidebarProps {
  currentPage?: string;
  onNavigate?: (pageId: string) => void;
}

export function AppSidebar({ currentPage = "overview", onNavigate }: AppSidebarProps) {
  const [isOpen, setIsOpen] = useState(false);

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
            return (
              <li key={item.id}>
                <a
                  href={`#${item.id}`}
                  className={currentPage === item.id ? "active" : ""}
                  onClick={(e) => {
                    e.preventDefault();
                    onNavigate?.(item.id);
                    setIsOpen(false);
                  }}
                >
                  <Icon size={17} />
                  <span>{item.label}</span>
                </a>
              </li>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="sidebar-footer">
          <nav className="sidebar-nav">
            {FOOTER_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <li key={item.id}>
                  <a
                    href={`#${item.id}`}
                    onClick={(e) => {
                      e.preventDefault();
                      onNavigate?.(item.id);
                      setIsOpen(false);
                    }}
                  >
                    <Icon size={17} />
                    <span>{item.label}</span>
                  </a>
                </li>
              );
            })}
          </nav>
        </div>
      </aside>
    </>
  );
}
