"use client";

import { ShieldCheck } from "lucide-react";

interface ApiKeyFieldProps {
  value: string;
  onChange: (value: string) => void;
  /** True once the backend reports a key in backend/.env. */
  hasEnvKey: boolean;
  /** Which provider the backend resolved: "gemini", "ollama", or null. */
  provider?: string | null;
  /** The model that will run, as the backend reports it. */
  model?: string | null;
  showHint?: boolean;
}

/**
 * Asks for a Gemini key only when the backend does not already have one.
 * With backend/.env configured the key is entered once, not every session.
 */
export default function ApiKeyField({
  value,
  onChange,
  hasEnvKey,
  provider = null,
  model = null,
  showHint = true,
}: ApiKeyFieldProps) {
  if (hasEnvKey) {
    const isOllama = provider === "ollama";
    const title = isOllama
      ? "Running on Ollama Cloud"
      : "API key loaded from backend/.env";
    const detail = isOllama
      ? `${model ?? "Model"} — set OLLAMA_MODEL in backend/.env to change it.`
      : "Nothing to enter. Edit that file to use a different key.";

    return (
      <div className="flex items-start gap-3 rounded-lg border border-emerald-500/25 bg-emerald-500/10 px-4 py-3">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
        <div>
          <p className="text-sm font-medium text-emerald-400">{title}</p>
          <p className="mt-0.5 text-xs text-zinc-400">{detail}</p>
        </div>
      </div>
    );
  }

  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-zinc-400">
        Google API Key
      </span>
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Enter your Google API key"
        className="w-full rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-3 transition-colors focus:border-violet-500 focus:outline-none"
      />
      {showHint && (
        <span className="mt-1 block text-xs text-zinc-500">
          Sent only to your local backend. Add it to backend/.env to skip this
          step next time.
        </span>
      )}
    </label>
  );
}
