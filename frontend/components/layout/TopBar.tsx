"use client";

import { Search, Settings, Moon, Sun } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

interface TopBarProps {
  onSearch?: (query: string) => void;
  isDarkMode?: boolean;
  onThemeToggle?: () => void;
}

export function TopBar({ onSearch, isDarkMode = false, onThemeToggle }: TopBarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);
    onSearch?.(query);
  };

  return (
    <header className="topbar">
      {/* Logo & Brand */}
      <Link href="/" className="brand" aria-label="FinSync Home">
        <div className="brand-mark">F</div>
        <div>
          <strong>FinSync</strong>
          <small>Intelligence</small>
        </div>
      </Link>

      {/* Global Search */}
      <div className="global-search">
        <Search size={16} style={{ position: "absolute", left: "12px", color: "var(--text-muted)" }} />
        <input
          type="text"
          placeholder="Search stocks, indices, sectors..."
          value={searchQuery}
          onChange={handleSearchChange}
          style={{ paddingLeft: "32px" }}
        />
        <div style={{ position: "absolute", right: "12px", fontSize: "11px", color: "var(--text-muted)" }}>
          /
        </div>
      </div>

      {/* Right Section */}
      <div className="header-badges">
        <span className="badge">Market Status: Open</span>
        <button className="btn-icon" onClick={onThemeToggle} aria-label="Toggle theme">
          {isDarkMode ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <button className="btn-icon" aria-label="Settings">
          <Settings size={16} />
        </button>
      </div>
    </header>
  );
}
