/// <reference types="vite/client" />
/**
 * API client for DebateAI backend.
 *
 * Local dev defaults to Vite proxy (`/api` -> http://127.0.0.1:5000).
 * On hosted frontend, set `VITE_API_BASE_URL` to your backend origin.
 */

const ENV_API_BASE = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}`.replace(/\/$/, "")
  : null;

function normalizeBase(base: string): string {
  return base.endsWith("/api") ? base : `${base}/api`;
}

function getApiBases(): string[] {
  if (ENV_API_BASE) return [normalizeBase(ENV_API_BASE)];

  const bases = ["/api"];

  // Production fallback for split frontend/backend deployments when env is missing.
  if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
    bases.push("https://debateai-backend.vercel.app/api");
  }

  return bases;
}

export type DebateStatePayload = any; // TODO: refine typing later if needed
export type SummaryPayload = any;

async function fetchJson(path: string, options: RequestInit = {}, defaultError = "Request failed"): Promise<any> {
  const bases = getApiBases();
  let lastError: Error | null = null;

  for (const base of bases) {
    const url = `${base}${path}`;
    try {
      const res = await fetch(url, options);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `${defaultError}: ${res.status}`);
      }
      return await res.json();
    } catch (error: any) {
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

export async function startDebate(
  topic: string,
  maxRounds: number = 6,
  persona: string = "default",
  userSide: string = "auto"
): Promise<{ debate_id: string, state: DebateStatePayload, summary: SummaryPayload, facts_from_api: boolean, pruning_logs: any[] }> {
  return fetchJson(
    "/start",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: topic.trim(), max_rounds: maxRounds, persona, user_side: userSide }),
    },
    "Start failed",
  );
}

export function startDebateStream(
  topic: string,
  persona: string = "default",
  maxRounds: number = 6,
  onEvent: (event: any) => void,
  onError: (error: Error) => void
): () => void {
  const base = getApiBases()[0];
  const url = `${base}/stream?topic=${encodeURIComponent(topic)}&persona=${encodeURIComponent(persona)}&max_rounds=${maxRounds}`;
  const source = new EventSource(url);

  source.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data);
      if (data.type === "done") {
        source.close();
      }
    } catch (err) {
      console.error("Failed to parse stream data", err);
    }
  };

  source.onerror = (e) => {
    source.close();
    onError(new Error("Stream connection failed or closed unexpectedly"));
  };

  return () => source.close();
}

export function streamDebateTurn(
  debateId: string,
  onEvent: (event: any) => void,
  onError: (error: Error) => void
): () => void {
  const base = getApiBases()[0];
  const url = `${base}/debate/${debateId}/stream_turn`;
  const source = new EventSource(url);

  source.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data);
      if (data.type === "done" || data.type === "turn_complete" || data.type === "waiting_for_user") {
        source.close();
      }
    } catch (err) {
      console.error("Failed to parse stream data", err);
    }
  };

  source.onerror = (e) => {
    source.close();
    onError(new Error("Stream connection failed or closed unexpectedly"));
  };

  return () => source.close();
}

export async function submitDebateMove(debateId: string, text: string): Promise<{ state: DebateStatePayload, summary: SummaryPayload }> {
  return fetchJson(
    `/debate/${debateId}/move`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    },
    "Failed to submit move"
  );
}

export async function getState(debateId: string): Promise<{ state: DebateStatePayload, summary: SummaryPayload }> {
  return fetchJson(`/state/${debateId}`, {}, "Failed to get state");
}

export async function getSummary(debateId: string, overrideAudience: number | null = null): Promise<SummaryPayload> {
  const options: RequestInit =
    overrideAudience != null
      ? {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ override_audience: overrideAudience }),
      }
      : {};

  return fetchJson(`/summary/${debateId}`, options, "Failed to get summary");
}
