"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8891";
const PROBE_TIMEOUT_MS = 2000;
const PROBE_INTERVAL_MS = 1000;
const OFFLINE_TIMEOUT_MS = 30_000;
const ONLINE_TIMEOUT_MS = 90_000;
const FRONTEND_TIMEOUT_MS = 90_000;

type Action = "restart" | "shutdown";
type Phase = "idle" | "confirming" | "working" | "stopped" | "error";

const COPY: Record<Action, { label: string; question: string; working: string }> = {
  restart: {
    label: "Restart",
    question: "Restart both servers?",
    working: "Restarting both servers...",
  },
  shutdown: {
    label: "Shutdown",
    question: "Stop both servers?",
    working: "Stopping both servers...",
  },
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

async function isBackendUp(): Promise<boolean> {
  // A hung backend must read as down rather than stalling the wait loops.
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}/health`, {
      signal: controller.signal,
      cache: "no-store",
    });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

async function isFrontendUp(): Promise<boolean> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const res = await fetch(`${window.location.origin}/`, {
      signal: controller.signal,
      cache: "no-store",
    });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

/** Polls until the probe matches `expected`, or the timeout runs out. */
async function waitUntil(
  probe: () => Promise<boolean>,
  expected: boolean,
  timeoutMs: number
): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if ((await probe()) === expected) return true;
    await sleep(PROBE_INTERVAL_MS);
  }
  return false;
}

async function requestAction(action: Action): Promise<void> {
  const res = await fetch(`${API_BASE}/api/service/${action}`, { method: "POST" });
  if (!res.ok) {
    const detail = await res
      .json()
      .then((body) => body?.detail)
      .catch(() => null);
    throw new Error(detail || `The backend refused the ${action} request.`);
  }
}

export default function ServiceControls() {
  const [supervised, setSupervised] = useState<boolean | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [action, setAction] = useState<Action>("restart");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/api/service`)
      .then((res) => (res.ok ? res.json() : null))
      .then((body) => {
        if (active) setSupervised(Boolean(body?.supervised));
      })
      .catch(() => {
        if (active) setSupervised(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const runShutdown = async () => {
    await requestAction("shutdown");
    await waitUntil(isBackendUp, false, OFFLINE_TIMEOUT_MS);
    setPhase("stopped");
    setMessage("Both servers stopped. Run ./start.sh to bring them back.");
  };

  const runRestart = async () => {
    await requestAction("restart");

    const wentDown = await waitUntil(isBackendUp, false, OFFLINE_TIMEOUT_MS);
    const cameBack = await waitUntil(isBackendUp, true, ONLINE_TIMEOUT_MS);

    if (!cameBack) {
      throw new Error(
        wentDown
          ? "The backend did not come back. Check the terminal running ./start.sh."
          : "The restart was queued but nothing happened. Check the terminal running ./start.sh."
      );
    }

    // The dev server restarts a moment after the backend, so the page is only
    // worth reloading once it can actually serve the request.
    setMessage("Backend is back. Waiting for the frontend...");
    if (await waitUntil(isFrontendUp, true, FRONTEND_TIMEOUT_MS)) {
      window.location.reload();
      return;
    }
    throw new Error("The frontend did not come back. Check the terminal running ./start.sh.");
  };

  const confirm = async () => {
    setPhase("working");
    setMessage(COPY[action].working);
    try {
      await (action === "shutdown" ? runShutdown() : runRestart());
    } catch (err) {
      setPhase("error");
      setMessage(err instanceof Error ? err.message : "Something went wrong.");
    }
  };

  const ask = (next: Action) => {
    setAction(next);
    setPhase("confirming");
    setMessage("");
  };

  const cancel = () => {
    setPhase("idle");
    setMessage("");
  };

  if (phase === "working") {
    return (
      <Banner tone="neutral" role="status">
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-zinc-400 border-t-transparent" />
        {message}
      </Banner>
    );
  }

  if (phase === "stopped") {
    return <Banner tone="neutral" role="status">{message}</Banner>;
  }

  if (phase === "confirming") {
    return (
      <Banner tone="warn" role="alertdialog">
        {COPY[action].question}
        <button
          onClick={confirm}
          className="rounded-full bg-red-500/90 px-3 py-1 text-xs font-medium text-white transition-colors hover:bg-red-500"
        >
          Yes, {COPY[action].label.toLowerCase()}
        </button>
        <button
          onClick={cancel}
          className="rounded-full border border-zinc-700/60 px-3 py-1 text-xs font-medium text-zinc-400 transition-colors hover:text-zinc-200"
        >
          Cancel
        </button>
      </Banner>
    );
  }

  const disabled = supervised === false;
  const hint = disabled
    ? "Only available when the dashboard is running under ./start.sh"
    : undefined;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="inline-flex items-center gap-2">
        <ControlButton onClick={() => ask("restart")} disabled={disabled} title={hint}>
          Restart
        </ControlButton>
        <ControlButton onClick={() => ask("shutdown")} disabled={disabled} title={hint}>
          Shutdown
        </ControlButton>
      </div>
      {phase === "error" && (
        <p className="max-w-md text-center text-xs text-red-400" role="alert">
          {message}
        </p>
      )}
      {disabled && (
        <p className="text-xs text-zinc-500">
          Start the dashboard with ./start.sh to control the servers from here.
        </p>
      )}
    </div>
  );
}

function ControlButton({
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className="inline-flex items-center gap-2 rounded-full border border-zinc-700/60 bg-zinc-800/40 px-3 py-1.5 text-xs font-medium text-zinc-400 transition-colors hover:border-zinc-600 hover:text-zinc-200 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-zinc-700/60 disabled:hover:text-zinc-400"
    >
      {children}
    </button>
  );
}

function Banner({
  children,
  tone,
  role,
}: {
  children: React.ReactNode;
  tone: "neutral" | "warn";
  role: string;
}) {
  const tones = {
    neutral: "border-zinc-700/60 bg-zinc-800/40 text-zinc-400",
    warn: "border-amber-500/25 bg-amber-500/10 text-amber-400",
  };
  return (
    <div
      role={role}
      aria-live="polite"
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </div>
  );
}
