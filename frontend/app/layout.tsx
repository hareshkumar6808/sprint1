import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "FinSync Intelligence", description: "Simulated multi-agent financial research intelligence" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
