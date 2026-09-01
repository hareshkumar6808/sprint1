"use client";

import { ReactNode } from "react";

export interface Column<T> {
  key: keyof T | string;
  header: string;
  align?: "left" | "center" | "right";
  render?: (value: unknown, row: T) => ReactNode;
  width?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField?: keyof T | string;
  onRowClick?: (row: T) => void;
  isLoading?: boolean;
  emptyMessage?: string;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  keyField = "id",
  onRowClick,
  isLoading,
  emptyMessage = "No data available",
}: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
        Loading...
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
        {emptyMessage}
      </div>
    );
  }

  return (
    <table>
      <thead>
        <tr>
          {columns.map((col) => (
            <th
              key={String(col.key)}
              style={{
                textAlign: col.align || "left",
                width: col.width,
              }}
            >
              {col.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row) => (
          <tr
            key={String(row[keyField as keyof T])}
            onClick={() => onRowClick?.(row)}
            style={{ cursor: onRowClick ? "pointer" : "auto" }}
          >
            {columns.map((col) => (
              <td
                key={String(col.key)}
                style={{
                  textAlign: col.align || "left",
                  fontVariantNumeric: col.align === "right" ? "tabular-nums" : "normal",
                }}
              >
                {col.render
                  ? col.render(row[col.key as keyof T], row)
                  : String(row[col.key as keyof T] ?? "")}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
