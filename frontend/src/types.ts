/**
 * Shared TypeScript types for DebateAI.
 * These mirror the backend's Python dataclasses and `to_dict()` shapes exactly.
 */

// --------------------------------------------------------------------- //
// Domain types
// --------------------------------------------------------------------- //

export type Side = "pro" | "con";
export type Winner = "pro" | "con" | "tie" | null;
export type PersonaKey = "default" | "skeptic" | "gullible" | "partisan_pro" | "partisan_con";
export type UserSide = "auto" | "pro" | "con";
export type ReasoningType =
    | "causal"
    | "tradeoff"
    | "ethical"
    | "risk"
    | "rebuttal"
    | "deductive"
    | "inductive"
    | "informal";

/**
 * A single structured argument produced by an AI agent or parsed from a user submission.
 * Mirrors backend `Argument.to_dict()`.
 */
export interface Argument {
    claim: string;
    premises: string[];
    inference: string;
    strength: number;         // 0.0 – 1.0
    reasoning_type: ReasoningType | string;
    attack_target?: number | null;
}

/**
 * One entry in the debate history — which side spoke, what they said, and the belief after.
 * Mirrors backend `RoundRecord.to_dict()`.
 */
export interface DebateHistoryItem {
    side: Side;
    argument: Argument;
    belief_after: number;     // 0.0 – 1.0
}

/**
 * Full serialized debate state as returned by the backend.
 * Mirrors backend `DebateState.to_dict()`.
 */
export interface DebateState {
    id?: string | null;
    topic: string;
    user_side: UserSide;
    /** Display round (1-based, capped at max_rounds). */
    round: number;
    max_rounds: number;
    belief: number;           // 0.0 – 1.0, current audience belief
    belief_history?: number[];
    pro_claims: string[];
    con_claims: string[];
    history: DebateHistoryItem[];
    winner?: Winner;
    turning_point_round?: number | null;
}

// --------------------------------------------------------------------- //
// API response types
// --------------------------------------------------------------------- //

/**
 * Summary object returned after debate or on-demand.
 * Mirrors backend `DebateService.summarize()` return value.
 */
export interface SummaryPayload {
    topic: string;
    winner: "pro" | "con" | "tie";
    final_belief: number;
    final_pro_pct: number;
    final_con_pct: number;
    turning_point_round: number | null;
    total_rounds: number;
}

/** Response from POST /api/start */
export interface StartResponse {
    debate_id: string;
    state: DebateState;
    summary: SummaryPayload;
    facts_from_api: boolean;
    pruning_logs: PruningLogEntry[];
}

/** Response from GET /api/state/:id */
export interface StateResponse {
    state: DebateState;
    summary: SummaryPayload;
}

/** Response from POST /api/debate/:id/move */
export interface MoveResponse {
    state: DebateState;
    summary: SummaryPayload;
}

// --------------------------------------------------------------------- //
// Stream event types
// --------------------------------------------------------------------- //

export interface TypingEvent {
    type: "typing";
    side: Side;
    chunk: string;
}

export interface MoveEvent {
    type: "move";
    state: DebateState;
}

export interface InitEvent {
    type: "init";
    state: DebateState;
    facts_from_api: boolean;
}

export interface WaitingForUserEvent {
    type: "waiting_for_user";
    state: DebateState;
}

export interface TurnCompleteEvent {
    type: "turn_complete";
    state: DebateState;
}

export interface DoneEvent {
    type: "done";
    state: DebateState;
    summary: SummaryPayload;
}

export type StreamEvent =
    | TypingEvent
    | MoveEvent
    | InitEvent
    | WaitingForUserEvent
    | TurnCompleteEvent
    | DoneEvent;

// --------------------------------------------------------------------- //
// Pruning / debug types
// --------------------------------------------------------------------- //

export interface PruningLogEntry {
    depth: number;
    side: Side;
    action_description: string;
    cut_type: "alpha" | "beta";
    value: number;
    alpha: number;
    beta: number;
}
