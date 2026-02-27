/**
 * API client for DebateAI backend.
 *
 * Local dev defaults to Vite proxy (`/api` -> http://127.0.0.1:5000).
 * On hosted frontend, set `VITE_API_BASE_URL` to your backend origin.
 */

const ENV_API_BASE = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}`.replace(/\/$/, "")
  : null;

function normalizeBase(base) {
  return base.endsWith("/api") ? base : `${base}/api`;
}

function getApiBases() {
  if (ENV_API_BASE) return [normalizeBase(ENV_API_BASE)];

  const bases = ["/api"];

  // Production fallback for split frontend/backend deployments when env is missing.
  if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
    bases.push("https://debateai-backend.vercel.app/api");
  }

  return bases;
}

async function fetchJson(path, options = {}, defaultError = "Request failed") {
  const bases = getApiBases();
  let lastError = null;

  for (const base of bases) {
    const url = `${base}${path}`;
    try {
      const res = await fetch(url, options);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `${defaultError}: ${res.status}`);
      }
      return await res.json();
    } catch (error) {
      lastError = error;
      // Try next base only for network-level failures.
      if (!(error instanceof TypeError)) {
        break;
      }
    }
  }

  if (lastError instanceof TypeError) {
    throw new Error(
      "Unable to reach DebateAI backend. Check backend availability or set VITE_API_BASE_URL.",
    );
  }

  throw lastError || new Error(defaultError);
}

export async function startDebate(topic, maxRounds = 6) {
  return fetchJson(
    "/start",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: topic.trim(), max_rounds: maxRounds }),
    },
    "Start failed",
  );
}

export async function getState() {
  return fetchJson("/state", {}, "Failed to get state");
}

export async function getSummary(overrideAudience = null) {
  const options =
    overrideAudience != null
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ override_audience: overrideAudience }),
        }
      : {};

  return fetchJson("/summary", options, "Failed to get summary");
}
