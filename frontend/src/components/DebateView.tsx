import { useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import AgentPanel from "./AgentPanel";
import BeliefMeter from "./BeliefMeter";
import BeliefChart from "./BeliefChart";
import type { DebateState, DebateHistoryItem, Side } from "../types";

export interface DebateViewProps {
  state: DebateState | null;
  history: DebateHistoryItem[] | null | undefined;
  factsFromApi: boolean;
  activeTyping?: { side: Side; text: string } | null;
  isStreaming?: boolean;
}

/** Pair Pro and Con into rounds */
function getRoundPairs(history: DebateHistoryItem[] | null | undefined) {
  const h = history ?? [];
  const pairs: Array<{
    roundNum: number;
    pro: DebateHistoryItem | null;
    con: DebateHistoryItem | null;
  }> = [];
  for (let i = 0; i < h.length; i += 2) {
    const a = h[i];
    const b = h[i + 1];
    pairs.push({
      roundNum: pairs.length + 1,
      pro: a?.side === "pro" ? a : b?.side === "pro" ? b : null,
      con: a?.side === "con" ? a : b?.side === "con" ? b : null,
    });
  }
  // Add a "live" round when typing is happening but turn isn't committed yet
  return pairs;
}

const containerVariants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.12 },
  },
};

const roundVariants = {
  hidden: { opacity: 0, y: 24 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: "easeOut" as const },
  },
};

export default function DebateView({ state, history, factsFromApi, activeTyping, isStreaming }: DebateViewProps) {
  const maxRounds = state?.max_rounds ?? 6;
  const roundPairs = useMemo(() => getRoundPairs(history), [history]);
  const belief = state?.belief ?? 0.5;
  const displayRound = state?.round ?? 0;

  // Current live round: 1-indexed, one ahead if actively typing
  const liveRoundNum = activeTyping ? roundPairs.length + 1 : roundPairs.length;
  const proTyping = activeTyping?.side === "pro" ? activeTyping.text : null;
  const conTyping = activeTyping?.side === "con" ? activeTyping.text : null;

  return (
    <div className="mt-10 flex flex-col gap-8">
      {/* Topic header */}
      <AnimatePresence>
        {state?.topic && (
          <motion.div
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            className="relative rounded-2xl border border-slate-700/50 bg-white/[0.02] backdrop-blur-sm px-6 py-4 overflow-hidden"
          >
            {/* Accent line */}
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-slate-500/50 to-transparent" />
            <div className="flex items-start gap-3">
              <div className="flex-1">
                <p className="text-xs font-bold tracking-widest text-slate-500 uppercase mb-1">Debate Topic</p>
                <p className="text-slate-100 text-lg font-semibold leading-snug">{state.topic}</p>
              </div>
              {factsFromApi && (
                <span className="flex-shrink-0 mt-1 rounded-full bg-emerald-900/50 text-emerald-300 text-xs font-medium px-3 py-1 border border-emerald-700/40">
                  Live facts ✦
                </span>
              )}
            </div>
            {state.user_side && state.user_side !== "auto" && (
              <p className="mt-2 text-xs text-slate-500">
                You are playing as: <span className={state.user_side === "pro" ? "text-emerald-400 font-semibold" : "text-rose-400 font-semibold"}>{state.user_side === "pro" ? "Pro ✦" : "Con ✦"}</span>
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Belief Meter + Chart (persistent) */}
      {state && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="rounded-2xl border border-slate-700/40 bg-white/[0.025] backdrop-blur-sm px-6 py-5 shadow-xl flex flex-col gap-5"
        >
          <BeliefMeter belief={belief} round={displayRound} maxRounds={maxRounds} />
          {/* Chart — only show once we have 2+ belt history points */}
          <AnimatePresence>
            {(state.belief_history?.length ?? 0) >= 2 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.4 }}
              >
                <BeliefChart
                  beliefHistory={state.belief_history!}
                  maxRounds={maxRounds}
                  turningPointRound={state.turning_point_round}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      )}

      {/* Round progress dots */}
      {state && maxRounds > 0 && (
        <div className="flex items-center gap-1.5 justify-center">
          {Array.from({ length: maxRounds }).map((_, i) => {
            const roundNum = i + 1;
            const isCompleted = roundNum <= roundPairs.length;
            const isCurrent = roundNum === roundPairs.length + 1 && !!(activeTyping || isStreaming);
            // Color by who was winning at end of that round
            const belief_after = state.belief_history?.[i * 2 + 2];
            const dotColor = isCompleted
              ? (belief_after !== undefined
                ? belief_after > 0.52 ? "bg-emerald-500"
                  : belief_after < 0.48 ? "bg-rose-500"
                    : "bg-slate-500"
                : "bg-slate-600")
              : isCurrent ? "bg-slate-400 animate-pulse"
                : "bg-slate-800";
            return (
              <motion.div
                key={roundNum}
                title={`Round ${roundNum}`}
                className={`rounded-full transition-all duration-300 ${isCurrent ? "w-3 h-3 ring-2 ring-slate-400/50" : "w-2 h-2"
                  } ${dotColor}`}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: i * 0.05 }}
              />
            );
          })}
        </div>
      )}

      {/* Rounds — stagger them in as they arrive */}
      <motion.div
        className="flex flex-col gap-6"
        variants={containerVariants}
        initial="hidden"
        animate="show"
      >
        {roundPairs.map(({ roundNum, pro, con }) => (
          <motion.section
            key={roundNum}
            variants={roundVariants}
            className="rounded-2xl border border-slate-700/30 bg-white/[0.015] backdrop-blur-sm overflow-hidden"
          >
            {/* Round header */}
            <div className="flex items-center gap-2 px-3 sm:px-5 py-2 sm:py-3 border-b border-slate-700/30 bg-white/[0.015]">
              <span className="flex items-center justify-center w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-slate-700/60 text-xs font-bold text-slate-300">
                {roundNum}
              </span>
              <span className="text-sm font-semibold text-slate-300">Round {roundNum}</span>
              {roundNum === roundPairs.length && isStreaming && (
                <span className="ml-auto flex items-center gap-1.5 text-xs text-slate-500">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Live
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 p-3 sm:p-4">
              <AgentPanel
                side="pro"
                argument={pro?.argument ?? null}
                isActive={false}
              />
              <AgentPanel
                side="con"
                argument={con?.argument ?? null}
                isActive={false}
              />
            </div>
          </motion.section>
        ))}

        {/* Live typing round (not yet committed) */}
        {activeTyping && (
          <motion.section
            key="live"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-2xl border border-slate-600/50 bg-white/[0.02] backdrop-blur-sm overflow-hidden"
          >
            <div className="flex items-center gap-2 px-3 sm:px-5 py-2 sm:py-3 border-b border-slate-700/30 bg-white/[0.02]">
              <span className="flex items-center justify-center w-5 h-5 sm:w-6 sm:h-6 rounded-full bg-slate-700/60 text-xs font-bold text-slate-300">
                {liveRoundNum}
              </span>
              <span className="text-sm font-semibold text-slate-300">Round {liveRoundNum}</span>
              <span className="ml-auto flex items-center gap-1.5 text-xs text-slate-500">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
              <AgentPanel
                side="pro"
                argument={null}
                isActive={!!proTyping}
                typingText={proTyping}
              />
              <AgentPanel
                side="con"
                argument={null}
                isActive={!!conTyping}
                typingText={conTyping}
              />
            </div>
          </motion.section>
        )}
      </motion.div>

      {/* Debate hasn't started yet */}
      {roundPairs.length === 0 && !activeTyping && state && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center text-slate-500 py-10 text-sm"
        >
          <div className="flex justify-center gap-1.5 mb-3">
            {[0, 150, 300].map((d) => (
              <span key={d} className="w-2 h-2 rounded-full bg-slate-600 animate-bounce" style={{ animationDelay: `${d}ms` }} />
            ))}
          </div>
          Waiting for first argument…
        </motion.div>
      )}
    </div>
  );
}
