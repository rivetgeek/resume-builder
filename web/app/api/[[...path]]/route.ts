import type { NextRequest } from "next/server";

/**
 * Proxy /api/* to the FastAPI backend so Set-Cookie from login is returned to the browser.
 * (next.config rewrites often do not forward Set-Cookie reliably for external destinations.)
 */
const API_BASE = (process.env.INTERNAL_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "content-length",
  "host",
]);

async function proxy(req: NextRequest, ctx: { params: { path?: string[] } }) {
  const segments = ctx.params.path ?? [];
  const suffix = segments.length ? segments.join("/") : "";
  const u = new URL(req.url);
  const target = `${API_BASE}/api/${suffix}${u.search}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (HOP_BY_HOP.has(key.toLowerCase())) return;
    headers.set(key, value);
  });

  const init: RequestInit = {
    method: req.method,
    headers,
    redirect: "manual",
  };

  if (!["GET", "HEAD"].includes(req.method)) {
    init.body = await req.arrayBuffer();
  }

  const res = await fetch(target, init);
  const out = new Headers();
  res.headers.forEach((value, key) => {
    const kl = key.toLowerCase();
    if (HOP_BY_HOP.has(kl)) return;
    if (kl === "set-cookie") {
      out.append(key, value);
    } else {
      out.set(key, value);
    }
  });

  return new Response(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers: out,
  });
}

export const GET = (req: NextRequest, ctx: { params: { path?: string[] } }) => proxy(req, ctx);
export const POST = (req: NextRequest, ctx: { params: { path?: string[] } }) => proxy(req, ctx);
export const PUT = (req: NextRequest, ctx: { params: { path?: string[] } }) => proxy(req, ctx);
export const PATCH = (req: NextRequest, ctx: { params: { path?: string[] } }) => proxy(req, ctx);
export const DELETE = (req: NextRequest, ctx: { params: { path?: string[] } }) => proxy(req, ctx);
