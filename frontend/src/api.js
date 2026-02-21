/**
 * API client for DebateAI backend.
 * Uses Vite proxy: /api -> http://127.0.0.1:5000
 */

const API_BASE = "/api";

export async function startDebate(topic, maxRounds = 6) {
  const res = await fetch(`${API_BASE}/start`, {
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
  const res = await fetch(`${API_BASE}/state`);
  if (!res.ok) throw new Error("Failed to get state");
  return res.json();
}

export async function getSummary(overrideAudience = null) {
  const url = `${API_BASE}/summary`;
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
