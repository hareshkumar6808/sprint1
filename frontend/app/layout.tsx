import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "FinSync Intelligence · Multi-Agent Market Research", description: "Transparent multi-agent financial research using simulated market data, local news, filing evidence, and personalized risk context." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body>{children}</body></html>; }
