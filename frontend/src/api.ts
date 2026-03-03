/// <reference types="vite/client" />
/**
 * API client for DebateAI backend.
 *
 * Local dev defaults to Vite proxy (`/api` -> http://127.0.0.1:5000).
 * On hosted frontend, set `VITE_API_BASE_URL` to your backend origin.
 */

import type {
  DebateState,
  SummaryPayload,
  StartResponse,
  MoveResponse,
  StreamEvent,
} from "./types";

export type { DebateState, SummaryPayload, StartResponse, MoveResponse, StreamEvent };

const rawEnvBase = import.meta.env.VITE_API_BASE_URL;
let ENV_API_BASE = rawEnvBase ? `${rawEnvBase}`.replace(/\/$/, "") : null;

if (ENV_API_BASE && !ENV_API_BASE.startsWith("http")) {
  ENV_API_BASE = `https://${ENV_API_BASE}`;
}

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

async function fetchJson<T>(path: string, options: RequestInit = {}, defaultError = "Request failed"): Promise<T> {
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
      return (await res.json()) as T;
    } catch (error: unknown) {
      lastError = error instanceof Error ? error : new Error(String(error));
      // Try next base only for network-level failures.
      if (!(error instanceof TypeError)) {
        break;
      }
    }
  }

  if (lastError instanceof TypeError) {
    console.error(`[DebateAI] Network/CORS Error when hitting ${bases.join(", ")}`, lastError);
    throw new Error(
      "Unable to reach DebateAI backend. Check the browser console (F12) for exact CORS/Network details, or verify VITE_API_BASE_URL.",
    );
  }

  throw lastError || new Error(defaultError);
}

export async function startDebate(
  topic: string,
  maxRounds: number = 6,
  persona: string = "default",
  userSide: string = "auto",
): Promise<StartResponse> {
  return fetchJson<StartResponse>(
    "/start",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: topic.trim(), max_rounds: maxRounds, persona, user_side: userSide }),
    },
    "Start failed",
  );
}


export function streamDebateTurn(
  debateId: string,
  onEvent: (event: StreamEvent) => void,
  onError: (error: Error) => void,
): () => void {
  const base = getApiBases()[0];
  const url = `${base}/debate/${debateId}/stream_turn`;
  const source = new EventSource(url);

  source.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data) as StreamEvent;
      onEvent(data);
      if (data.type === "done" || data.type === "turn_complete" || data.type === "waiting_for_user") {
        source.close();
      }
    } catch (err) {
      console.error("Failed to parse stream data", err);
    }
  };

  source.onerror = () => {
    source.close();
    onError(new Error("Stream connection failed or closed unexpectedly"));
  };

  return () => source.close();
}

export async function submitDebateMove(debateId: string, text: string): Promise<MoveResponse> {
  return fetchJson<MoveResponse>(
    `/debate/${debateId}/move`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    },
    "Failed to submit move",
  );
}

export async function getState(debateId: string): Promise<{ state: DebateState; summary: SummaryPayload }> {
  return fetchJson<{ state: DebateState; summary: SummaryPayload }>(`/state/${debateId}`, {}, "Failed to get state");
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

  return fetchJson<SummaryPayload>(`/summary/${debateId}`, options, "Failed to get summary");
}
