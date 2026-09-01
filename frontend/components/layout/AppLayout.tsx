"use client";

import { ReactNode } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { MarketBar } from "@/components/layout/MarketBar";
import { AppSidebar } from "@/components/layout/AppSidebar";
import { WatchlistPanel } from "@/components/layout/WatchlistPanel";
import type { MarketQuote } from "@/types/analysis";

interface AppLayoutProps {
  children: ReactNode;
  currentPage?: string;
  watchlistItems?: MarketQuote[];
  onNavigate?: (pageId: string) => void;
  onSearch?: (query: string) => void;
}

export function AppLayout({
  children,
  currentPage = "overview",
  watchlistItems = [],
  onNavigate,
  onSearch,
}: AppLayoutProps) {
  return (
    <div className="app-shell">
      <TopBar onSearch={onSearch} />
      <MarketBar />
      <div className="main-layout">
        <AppSidebar currentPage={currentPage} onNavigate={onNavigate} />
        <main className="main-content">{children}</main>
        <WatchlistPanel items={watchlistItems} />
      </div>
    </div>
  );
}
