import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Read a single KEY=value from a dotenv-style file (no interpolation). */
function readEnvValueFromFile(filePath, keyName) {
  try {
    const raw = fs.readFileSync(filePath, "utf8");
    for (const line of raw.split(/\r?\n/)) {
      const t = line.trim();
      if (!t || t.startsWith("#")) continue;
      const eq = t.indexOf("=");
      if (eq === -1) continue;
      const key = t.slice(0, eq).trim();
      if (key !== keyName) continue;
      let v = t.slice(eq + 1).trim();
      if (
        (v.startsWith('"') && v.endsWith('"') && v.length >= 2) ||
        (v.startsWith("'") && v.endsWith("'") && v.length >= 2)
      ) {
        v = v.slice(1, -1);
      }
      return v;
    }
  } catch {
    // missing or unreadable .env
  }
  return "";
}

function isTruthyEnv(s) {
  return ["1", "true", "yes"].includes(String(s ?? "").trim().toLowerCase());
}

const rootEnvPath = path.join(__dirname, "..", ".env");
const fromFile = readEnvValueFromFile(rootEnvPath, "RESUME_BUILDER_DEV_NO_AUTH");
const fromProc =
  process.env.RESUME_BUILDER_DEV_NO_AUTH ||
  process.env.NEXT_PUBLIC_RESUME_BUILDER_DEV_NO_AUTH ||
  "";
const devNoAuth = isTruthyEnv(fromProc) || isTruthyEnv(fromFile);

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Mirrors repo-root .env so server and client see the same flag (restart `npm run dev` after changing .env).
  env: devNoAuth
    ? {
        RESUME_BUILDER_DEV_NO_AUTH: "1",
        NEXT_PUBLIC_RESUME_BUILDER_DEV_NO_AUTH: "1",
      }
    : {},
};

export default nextConfig;
