"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8891";
const POLL_INTERVAL_MS = 5000;
const REQUEST_TIMEOUT_MS = 3000;

type Health = "checking" | "live" | "offline";

async function probeBackend(): Promise<Health> {
  // A hung backend should read as offline rather than keeping the dot on its
  // last value forever, so the request is bounded.
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}/health`, { signal: controller.signal });
    return res.ok ? "live" : "offline";
  } catch {
    return "offline";
  } finally {
    clearTimeout(timeout);
  }
}

export default function BackendStatus() {
  const [health, setHealth] = useState<Health>("checking");

  useEffect(() => {
    let active = true;

    const check = async () => {
      const next = await probeBackend();
      if (active) setHealth(next);
    };

    check();
    const timer = setInterval(check, POLL_INTERVAL_MS);

    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const label =
    health === "live"
      ? "Backend live"
      : health === "offline"
      ? "Backend offline"
      : "Checking backend";

  const tone =
    health === "live"
      ? "text-emerald-400 border-emerald-500/25 bg-emerald-500/10"
      : health === "offline"
      ? "text-red-400 border-red-500/25 bg-red-500/10"
      : "text-zinc-400 border-zinc-700/60 bg-zinc-800/40";

  const dot =
    health === "live"
      ? "bg-emerald-400"
      : health === "offline"
      ? "bg-red-400"
      : "bg-zinc-500";

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${tone}`}
      role="status"
      aria-live="polite"
      title={
        health === "offline"
          ? `No response from ${API_BASE}. Start it with ./start.sh`
          : API_BASE
      }
    >
      <span className="relative flex h-2 w-2">
        {health === "live" && (
          <span className="live-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-70" />
        )}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${dot}`} />
      </span>
      {label}
    </div>
  );
}
