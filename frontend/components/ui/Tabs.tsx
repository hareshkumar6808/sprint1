"use client";

import { ReactNode, useState } from "react";

export interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
}

export function Tabs({ tabs, defaultTab }: TabsProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);

  const activeContent = tabs.find((tab) => tab.id === activeTab)?.content;

  return (
    <div>
      <div style={{ display: "flex", gap: "1rem", borderBottom: "1px solid var(--border)", marginBottom: "1rem" }}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "0.75rem 1rem",
              border: "none",
              borderBottom: activeTab === tab.id ? "2px solid var(--interactive)" : "2px solid transparent",
              background: "transparent",
              color: activeTab === tab.id ? "var(--interactive)" : "var(--text-secondary)",
              fontWeight: activeTab === tab.id ? 600 : 400,
              cursor: "pointer",
              fontSize: "13px",
              transition: "all 150ms ease",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div>{activeContent}</div>
    </div>
  );
}
