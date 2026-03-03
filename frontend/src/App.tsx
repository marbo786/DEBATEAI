import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMutation } from "@tanstack/react-query";
import {
  startDebate,
  streamDebateTurn,
  submitDebateMove,
  getSummary,
} from "./api";
import type { DebateState, SummaryPayload, StreamEvent, DebateHistoryItem } from "./types";
import TopicInput from "./components/TopicInput";
import DebateView from "./components/DebateView";
import SummaryCard from "./components/SummaryCard";

interface DebateSession {
  debate_id: string;
  state: DebateState;
  summary: SummaryPayload;
  facts_from_api: boolean;
}

export default function App() {
  const [debate, setDebate] = useState<DebateSession | null>(null);
  const [streamingState, setStreamingState] = useState<DebateState | null>(null);
  const [activeTyping, setActiveTyping] = useState<{ side: "pro" | "con"; text: string } | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isWaitingForUser, setIsWaitingForUser] = useState(false);
  const [userText, setUserText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [isDone, setIsDone] = useState(false);
  // User move feedback: the last argument the user submitted
  const [lastUserMove, setLastUserMove] = useState<DebateHistoryItem | null>(null);
  const moveFeedbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelStreamRef = useRef<(() => void) | null>(null);
  // Prevent double-triggering next turn
  const isTurnInFlightRef = useRef(false);

  const [overrideFeedback, setOverrideFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const overrideMutation = useMutation({
    mutationFn: ({ id, overrideAudience }: { id: string; overrideAudience: number }) =>
      getSummary(id, overrideAudience),
    onSuccess: (s) => {
      setDebate((d) => (d ? { ...d, summary: s } : d));
      setOverrideFeedback({ type: "success", message: "Summary updated for selected audience." });
    },
    onError: (e: Error) => {
      setOverrideFeedback({ type: "error", message: e?.message ?? "Failed to override summary." });
    },
  });

  const handleStart = async (topic: string, persona: string, userSide: string) => {
    // Cancel any in-flight stream
    if (cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }
    isTurnInFlightRef.current = false;

    setDebate(null);
    setStreamingState(null);
    setActiveTyping(null);
    setStreamError(null);
    setIsStarting(true);
    setIsStreaming(false);
    setIsWaitingForUser(false);
    setUserText("");
    setOverrideFeedback(null);
    setLastUserMove(null);
    if (moveFeedbackTimerRef.current) clearTimeout(moveFeedbackTimerRef.current);
    setIsDone(false);

    try {
      const res = await startDebate(topic, 6, persona, userSide);
      const initialState = res.state;
      setDebate({
        debate_id: res.debate_id,
        state: initialState,
        facts_from_api: res.facts_from_api,
        summary: res.summary,
      });
      setStreamingState(initialState);
      setIsStarting(false);
      // Kick off the first turn
      startNextTurn(res.debate_id);
    } catch (err: unknown) {
      setIsStarting(false);
      setStreamError(err instanceof Error ? err.message : "An unexpected error occurred.");
    }
  };

  const startNextTurn = (debateId: string) => {
    if (isTurnInFlightRef.current) return;
    isTurnInFlightRef.current = true;
    setIsStreaming(true);
    setActiveTyping(null);

    const cancel = streamDebateTurn(
      debateId,
      (event: StreamEvent) => {
        if (event.type === "typing") {
          setActiveTyping((prev) => ({
            side: event.side,
            text: (prev?.side === event.side ? prev.text : "") + event.chunk,
          }));
        } else if (event.type === "move") {
          setActiveTyping(null);
          setStreamingState(event.state);
          setDebate((d) => d ? { ...d, state: event.state } : d);
        } else if (event.type === "waiting_for_user") {
          setActiveTyping(null);
          setStreamingState(event.state);
          setDebate((d) => d ? { ...d, state: event.state } : d);
          setIsStreaming(false);
          isTurnInFlightRef.current = false;
          setIsWaitingForUser(true);
        } else if (event.type === "turn_complete") {
          setActiveTyping(null);
          setStreamingState(event.state);
          setDebate((d) => d ? { ...d, state: event.state } : d);
          isTurnInFlightRef.current = false;
          // Small pacing delay so the user can read the completed argument
          setTimeout(() => startNextTurn(debateId), 1200);
        } else if (event.type === "done") {
          setActiveTyping(null);
          setIsStreaming(false);
          isTurnInFlightRef.current = false;
          setIsDone(true);
          setDebate((d) => d ? { ...d, state: event.state, summary: event.summary } : d);
          setStreamingState(null);
        }
      },
      (err: Error) => {
        setStreamError(err.message);
        setIsStreaming(false);
        isTurnInFlightRef.current = false;
      },
    );
    cancelStreamRef.current = cancel;
  };

  const handleUserSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userText.trim() || !debate?.debate_id) return;
    setIsSubmitting(true);
    setStreamError(null);
    setIsWaitingForUser(false);
    setLastUserMove(null);
    if (moveFeedbackTimerRef.current) clearTimeout(moveFeedbackTimerRef.current);
    try {
      const res = await submitDebateMove(debate.debate_id, userText.trim());
      setStreamingState(res.state);
      setDebate((d) => d ? { ...d, state: res.state } : d);
      // Show feedback: find the user's move (last entry matching their side)
      const userSide = debate.state.user_side;
      const lastEntry = res.state.history[res.state.history.length - 1];
      if (lastEntry && (userSide === "auto" || lastEntry.side === userSide)) {
        setLastUserMove(lastEntry);
        // Auto-dismiss after 10 seconds
        moveFeedbackTimerRef.current = setTimeout(() => setLastUserMove(null), 10000);
      }
      setUserText("");
      setIsSubmitting(false);
      startNextTurn(debate.debate_id);
    } catch (err: unknown) {
      setStreamError(err instanceof Error ? err.message : "Failed to submit move.");
      setIsSubmitting(false);
      setIsWaitingForUser(true);
    }
  };

  const displayState = streamingState ?? debate?.state ?? null;

  return (
    <div className="min-h-screen bg-[#080d18] text-slate-100">
      {/* Ambient gradients */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-emerald-950/40 blur-[100px]" />
        <div className="absolute -bottom-40 -right-40 w-[600px] h-[600px] rounded-full bg-rose-950/30 blur-[100px]" />
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-white/[0.06] bg-white/[0.02] backdrop-blur-xl">
        <div className="mx-auto max-w-5xl px-4 py-5 flex flex-col items-center">
          <div className="flex items-center gap-2.5 mb-1">
            <span className="text-2xl">⚔️</span>
            <h1 className="font-display font-bold text-2xl tracking-tight text-white">
              Debate<span className="text-emerald-400">AI</span>
            </h1>
          </div>
          <p className="text-center text-slate-500 text-[10px] sm:text-xs tracking-widest uppercase font-medium">
            Adversarial Search · Minimax · Probabilistic Belief
          </p>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-5xl px-4 pb-20 pt-4 md:pt-8">
        <TopicInput onStart={handleStart} loading={isStarting} />

        {/* Error */}
        <AnimatePresence>
          {streamError && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-4 rounded-xl border border-red-700/40 bg-red-900/20 text-red-200 px-4 py-3 text-sm"
            >
              ⚠ {streamError}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Override feedback */}
        <AnimatePresence>
          {overrideFeedback && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className={`mt-4 rounded-xl border px-4 py-3 text-sm ${overrideFeedback.type === "error"
                ? "bg-red-900/20 border-red-700/40 text-red-200"
                : "bg-emerald-900/20 border-emerald-700/40 text-emerald-200"}`}
              role="status"
            >
              {overrideFeedback.message}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Debate view */}
        {displayState && (
          <DebateView
            state={displayState}
            history={displayState?.history}
            factsFromApi={debate?.facts_from_api ?? false}
            activeTyping={activeTyping}
            isStreaming={isStreaming}
          />
        )}

        {/* User move input */}
        <AnimatePresence>
          {isWaitingForUser && (
            <motion.form
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              onSubmit={handleUserSubmit}
              className="mt-6 flex flex-col gap-3 rounded-2xl border border-emerald-500/30 bg-white/[0.03] backdrop-blur-sm p-5"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <label className="text-sm text-emerald-300 font-bold">Your Turn — Enter Your Argument</label>
              </div>
              <textarea
                value={userText}
                onChange={(e) => setUserText(e.target.value)}
                disabled={isSubmitting}
                placeholder="E.g., Despite the risks, the economic upside strongly justifies…"
                maxLength={2000}
                className="w-full rounded-xl bg-slate-900/80 border border-slate-700/60 p-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500/60 min-h-[100px] transition text-sm"
              />
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-600">{userText.length}/2000</span>
                <button
                  type="submit"
                  disabled={isSubmitting || !userText.trim()}
                  className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white px-5 py-3 min-h-[44px] rounded-xl font-semibold transition text-sm"
                >
                  {isSubmitting ? "Submitting…" : "Submit Move →"}
                </button>
              </div>
            </motion.form>
          )}
        </AnimatePresence>

        {/* User move feedback panel */}
        <AnimatePresence>
          {lastUserMove && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.3 }}
              className="mt-4 rounded-xl border border-emerald-700/40 bg-emerald-950/30 backdrop-blur-sm p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-[10px] font-bold tracking-widest text-emerald-600 uppercase mb-1">
                    Your Argument — Analysis
                  </p>
                  <p className="text-sm text-slate-200 leading-snug mb-3 line-clamp-2">
                    {lastUserMove.argument.claim}
                  </p>
                  <div className="flex items-center gap-3 flex-wrap">
                    {/* Strength bar */}
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-slate-500 uppercase">Strength</span>
                      <div className="w-20 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                        <motion.div
                          className="h-full bg-gradient-to-r from-emerald-700 to-emerald-400 rounded-full"
                          initial={{ width: 0 }}
                          animate={{ width: `${Math.round(lastUserMove.argument.strength * 100)}%` }}
                          transition={{ duration: 0.6, delay: 0.1 }}
                        />
                      </div>
                      <span className="text-xs font-bold text-emerald-400">
                        {Math.round(lastUserMove.argument.strength * 100)}%
                      </span>
                    </div>
                    {/* Reasoning type badge */}
                    <span className="px-2 py-0.5 rounded-full border border-slate-700/50 bg-slate-800/60 text-[10px] font-medium text-slate-400 capitalize">
                      {lastUserMove.argument.reasoning_type}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (moveFeedbackTimerRef.current) clearTimeout(moveFeedbackTimerRef.current);
                    setLastUserMove(null);
                  }}
                  className="text-slate-600 hover:text-slate-400 transition text-lg leading-none flex-shrink-0 mt-0.5"
                  aria-label="Dismiss"
                >
                  ✕
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Summary card */}
        <AnimatePresence>
          {isDone && debate?.state?.winner != null && !streamingState && !isWaitingForUser && (
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <SummaryCard
                summary={debate.summary}
                state={debate.state}
                onOverride={async (overrideAudience: number) => {
                  setOverrideFeedback(null);
                  try {
                    if (!debate.state?.id) throw new Error("Missing debate ID");
                    await overrideMutation.mutateAsync({ id: debate.state.id, overrideAudience });
                    return true;
                  } catch {
                    return false;
                  }
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
