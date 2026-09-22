"use client";

import { useEffect, useState } from "react";

export interface Activity {
  phase: "executing" | "scoring" | "analyzing" | "mutating" | string;
  round?: number;
  scenario_index?: number;
  scenario_total?: number;
  scenario_name?: string;
}

interface LiveActivityProps {
  activity: Activity | null;
  isRunning: boolean;
  /** Changes whenever a round completes, so the timer restarts. */
  stepKey: string;
}

// Each agent's turn, named the way the README names them.
const PHASE_LABELS: Record<string, string> = {
  executing: "Executor is running the skill",
  scoring: "Executor is scoring the output",
  analyzing: "Analyst is diagnosing failures",
  mutating: "Mutator is rewriting the skill",
};

function formatElapsed(seconds: number) {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${String(seconds % 60).padStart(2, "0")}s`;
}

/** A ticking clock is the clearest proof the run is alive between round results. */
function useElapsedSeconds(resetKey: string, isRunning: boolean) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    setSeconds(0);
    if (!isRunning) return;

    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [resetKey, isRunning]);

  return seconds;
}

export default function LiveActivity({
  activity,
  isRunning,
  stepKey,
}: LiveActivityProps) {
  const elapsed = useElapsedSeconds(stepKey, isRunning);

  if (!isRunning) return null;

  const label = activity
    ? PHASE_LABELS[activity.phase] ?? "Working"
    : "Starting up";

  const hasScenario =
    activity?.scenario_index != null && activity?.scenario_total != null;

  const progress = hasScenario
    ? (activity!.scenario_index! / activity!.scenario_total!) * 100
    : null;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
      <div className="flex items-baseline justify-between gap-4">
        <p className="text-sm font-medium text-zinc-200">
          {label}
          {hasScenario && (
            <span className="text-zinc-400">
              {" "}
              · scenario {activity!.scenario_index} of{" "}
              {activity!.scenario_total}
            </span>
          )}
        </p>
        <p
          className="shrink-0 text-sm tabular-nums text-zinc-400"
          aria-label={`Elapsed ${formatElapsed(elapsed)}`}
        >
          {formatElapsed(elapsed)}
        </p>
      </div>

      {activity?.scenario_name && (
        <p className="mt-1 truncate text-xs text-zinc-500">
          {activity.scenario_name}
        </p>
      )}

      <div className="mt-3 h-1 overflow-hidden rounded-full bg-zinc-800">
        {progress === null ? (
          <div className="indeterminate h-full w-1/3 rounded-full bg-violet-500/70" />
        ) : (
          <div
            className="h-full rounded-full bg-violet-500 transition-[width] duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        )}
      </div>
    </div>
  );
}
