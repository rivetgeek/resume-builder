"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";

export function Header() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const router = useRouter();

  useEffect(() => setMounted(true), []);

  async function logout() {
    await apiFetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] px-4 py-3">
      <span className="text-lg font-semibold tracking-tight">Resume Builder</span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="min-tap rounded border border-[var(--color-border)] px-3 py-2 text-sm hover:bg-[var(--color-border)]/30"
          aria-label="Toggle color theme"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {mounted ? (theme === "dark" ? "Light" : "Dark") : "Theme"}
        </button>
        <button
          type="button"
          className="min-tap rounded bg-[var(--color-accent)] px-3 py-2 text-sm text-[var(--color-accent-fg)]"
          onClick={() => void logout()}
        >
          Log out
        </button>
      </div>
    </header>
  );
}
