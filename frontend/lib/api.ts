const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
export async function getHealth(): Promise<{ ok: boolean; version?: string }> {
  try {
    const response = await fetch(`${API_URL.replace(/\/api\/v1$/, "")}/health`, { cache: "no-store" });
    if (!response.ok) return { ok: false };
    const data: { status: string; version: string } = await response.json();
    return { ok: data.status === "healthy", version: data.version };
  } catch { return { ok: false }; }
}
