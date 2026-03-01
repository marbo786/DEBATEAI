import { useState, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { startDebate, streamDebateTurn, submitDebateMove, getSummary, DebateStatePayload, SummaryPayload } from "./api";
import TopicInput from "./components/TopicInput";
import DebateView from "./components/DebateView";
import SummaryCard from "./components/SummaryCard";

export default function App() {
  const [debate, setDebate] = useState<{
    debate_id?: string;
    state: DebateStatePayload;
    summary: SummaryPayload;
    facts_from_api: boolean;
  } | null>(null);

  // Streaming states
  const [streamingDebate, setStreamingDebate] = useState<{
    debate_id?: string;
    state: DebateStatePayload;
    facts_from_api: boolean;
  } | null>(null);
  const [activeTyping, setActiveTyping] = useState<{ side: "pro" | "con", text: string } | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isWaitingForUser, setIsWaitingForUser] = useState(false);
  const [userText, setUserText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const cancelStreamRef = useRef<(() => void) | null>(null);

  const [overrideFeedback, setOverrideFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const overrideMutation = useMutation({
    mutationFn: ({ id, overrideAudience }: { id: string; overrideAudience: number }) => getSummary(id, overrideAudience),
    onSuccess: (s) => {
      setDebate((d) => (d ? { ...d, summary: s } : d));
      setOverrideFeedback({
        type: "success",
        message: "Summary updated for selected audience override.",
      });
    },
    onError: (e: any) => {
      setOverrideFeedback({
        type: "error",
        message: e?.message ?? "Failed to override summary. Showing last confirmed server summary.",
      });
    },
  });

  const handleStart = async (topic: string, persona: string, userSide: string) => {
    setDebate(null);
    setStreamingDebate(null);
    setActiveTyping(null);
    setStreamError(null);
    setIsStreaming(true);
    setIsWaitingForUser(false);
    setUserText("");
    setOverrideFeedback(null);

    if (cancelStreamRef.current) {
      cancelStreamRef.current();
    }

    try {
      const res = await startDebate(topic, 6, persona, userSide);
      const initialDebate = { debate_id: res.debate_id, state: res.state, facts_from_api: res.facts_from_api, summary: res.summary };
      setDebate(initialDebate);
      setStreamingDebate(initialDebate);
      setIsStreaming(false);
      startNextTurn(res.debate_id);
    } catch (err: any) {
      setIsStreaming(false);
      setStreamError(err.message);
    }
  };

  const startNextTurn = (debateId: string) => {
    const cancel = streamDebateTurn(
      debateId,
      (event) => {
        if (event.type === "typing") {
          setActiveTyping(prev => ({
            side: event.side,
            text: (prev?.side === event.side ? prev.text : "") + event.chunk
          }));
        } else if (event.type === "move") {
          setActiveTyping(null);
          setStreamingDebate(prev => prev ? { ...prev, state: event.state } : null);
        } else if (event.type === "waiting_for_user") {
          setActiveTyping(null);
          setStreamingDebate(prev => prev ? { ...prev, state: event.state } : null);
          setIsWaitingForUser(true);
        } else if (event.type === "turn_complete") {
          setActiveTyping(null);
          setStreamingDebate(prev => prev ? { ...prev, state: event.state } : null);
          setTimeout(() => startNextTurn(debateId), 100);
        } else if (event.type === "done") {
          setActiveTyping(null);
          setDebate(prev => prev ? { ...prev, state: event.state, summary: event.summary } : null);
          setStreamingDebate(null);
        }
      },
      (err) => {
        setStreamError(err.message);
      }
    );
    cancelStreamRef.current = cancel;
  };

  const handleUserSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userText.trim() || !debate?.debate_id) return;
    setIsSubmitting(true);
    setStreamError(null);
    setIsWaitingForUser(false);
    try {
      const res = await submitDebateMove(debate.debate_id, userText.trim());
      setStreamingDebate(prev => prev ? { ...prev, state: res.state } : null);
      setUserText("");
      setIsSubmitting(false);
      startNextTurn(debate.debate_id);
    } catch (err: any) {
      setStreamError(err.message);
      setIsSubmitting(false);
      setIsWaitingForUser(true);
    }
  };

  const activeData = streamingDebate ?? debate;

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-body">
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 py-5">
          <h1 className="font-display font-bold text-2xl tracking-tight text-center text-slate-100">
            DebateAI: Watch Algorithms Argue
          </h1>
          <p className="text-center text-slate-400 text-sm mt-1">
            Adversarial search · Logical reasoning · Probabilistic belief
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <TopicInput onStart={handleStart} loading={isStreaming && !streamingDebate} />
        {streamError && (
          <div className="mt-4 rounded-lg bg-red-900/30 border border-red-700/50 text-red-200 px-4 py-3 text-sm">
            {streamError}
          </div>
        )}
        {overrideFeedback && (
          <div
            className={`mt-4 rounded-lg border px-4 py-3 text-sm ${overrideFeedback.type === "error"
              ? "bg-red-900/30 border-red-700/50 text-red-200"
              : "bg-emerald-900/30 border-emerald-700/50 text-emerald-200"
              }`}
            role="status"
          >
            {overrideFeedback.message}
          </div>
        )}
        {activeData && (
          <>
            <DebateView
              state={activeData.state}
              history={activeData.state?.history}
              factsFromApi={activeData.facts_from_api}
              activeTyping={activeTyping}
            />
            {isWaitingForUser && (
              <form onSubmit={handleUserSubmit} className="mt-6 flex flex-col gap-2 bg-slate-800 p-4 rounded-lg border border-teal-500/30 shadow-lg">
                <label className="text-sm text-teal-300 font-semibold mb-1">Your Turn! Enter your argument:</label>
                <textarea
                  value={userText}
                  onChange={(e) => setUserText(e.target.value)}
                  disabled={isSubmitting}
                  placeholder="E.g., Despite the risks, the economic upside..."
                  className="w-full rounded-lg bg-slate-900 border border-slate-700 p-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-teal-500 min-h-[100px] transition"
                />
                <div className="flex justify-end mt-2">
                  <button type="submit" disabled={isSubmitting || !userText.trim()} className="bg-teal-600 hover:bg-teal-500 text-white px-6 py-2 rounded-lg font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed">
                    {isSubmitting ? "Submitting..." : "Submit Move"}
                  </button>
                </div>
              </form>
            )}
            {debate?.state?.winner != null && !streamingDebate && !isWaitingForUser && (
              <SummaryCard
                summary={debate.summary}
                state={debate.state}
                onOverride={async (overrideAudience: number) => {
                  setOverrideFeedback(null);
                  try {
                    if (!debate.state?.id) throw new Error("Missing debate ID");
                    await overrideMutation.mutateAsync({ id: debate.state.id, overrideAudience });
                    return true;
                  } catch (e) {
                    return false;
                  }
                }}
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}
