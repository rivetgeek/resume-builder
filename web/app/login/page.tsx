"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      if (res.status === 429) {
        setError("Too many attempts. Try again later.");
        return;
      }
      if (res.status === 403) {
        const t = await res.text();
        setError(
          t.includes("origin")
            ? "Request blocked (origin). For local dev set RESUME_BUILDER_SKIP_ORIGIN_CHECK=1 in .env."
            : `Request blocked (${t || "403"}).`,
        );
        return;
      }
      if (!res.ok) {
        if (res.status === 401) {
          setError("Invalid password (or hash in .env does not match this password).");
        } else {
          setError(`Sign-in failed (${res.status}). Open /api/auth/self-check in this tab for diagnostics.`);
        }
        return;
      }
      router.push("/");
      router.refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4">
      <h1 className="mb-6 text-2xl font-semibold">Resume Builder</h1>
      <form onSubmit={(e) => void onSubmit(e)} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-[var(--color-muted)]">Password</span>
          <input
            type="password"
            autoComplete="current-password"
            className="min-tap rounded border border-[var(--color-border)] bg-transparent px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null}
        <button
          type="submit"
          disabled={loading}
          className="min-tap rounded bg-[var(--color-accent)] py-3 text-[var(--color-accent-fg)] disabled:opacity-50"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
