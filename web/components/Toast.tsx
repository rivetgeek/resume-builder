"use client";

import { useEffect } from "react";

export function Toast({
  message,
  variant = "info",
  onClose,
}: {
  message: string | null;
  variant?: "info" | "error" | "success";
  onClose: () => void;
}) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, 5000);
    return () => clearTimeout(t);
  }, [message, onClose]);

  if (!message) return null;
  const border =
    variant === "error"
      ? "border-red-700/50"
      : variant === "success"
        ? "border-emerald-700/50"
        : "border-[var(--color-border)]";
  return (
    <div
      role="status"
      className={`fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded border px-4 py-3 shadow-sm ${border} bg-[var(--color-bg)] text-[var(--color-fg)]`}
    >
      {message}
    </div>
  );
}
