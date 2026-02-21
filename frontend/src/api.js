/**
 * API client for DebateAI backend.
 *
 * Local dev defaults to Vite proxy (`/api` -> http://127.0.0.1:5000).
 * On Vercel (or any hosted frontend), set `VITE_API_BASE_URL`
 * to your deployed backend URL, e.g.:
 *   VITE_API_BASE_URL=https://debateai-backend.vercel.app
 */

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL
    ? `${import.meta.env.VITE_API_BASE_URL}`.replace(/\/$/, "")
    : "/api"
);

function buildUrl(path) {
  if (API_BASE.endsWith("/api")) {
    return `${API_BASE}${path}`;
  }
  return `${API_BASE}/api${path}`;
}

export async function startDebate(topic, maxRounds = 6) {
  const res = await fetch(buildUrl("/start"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic: topic.trim(), max_rounds: maxRounds }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `Start failed: ${res.status}`);
  }
  return res.json();
}

export async function getState() {
  const res = await fetch(buildUrl("/state"));
  if (!res.ok) throw new Error("Failed to get state");
  return res.json();
}

export async function getSummary(overrideAudience = null) {
  const url = buildUrl("/summary");
  const options =
    overrideAudience != null
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ override_audience: overrideAudience }),
        }
      : {};
  const res = await fetch(url, options);
  if (!res.ok) throw new Error("Failed to get summary");
  return res.json();
}
