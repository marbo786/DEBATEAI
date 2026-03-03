import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { Argument, Side } from "../types";

export interface AgentPanelProps {
  side: Side;
  argument?: Argument | null;
  roundLabel?: string | null;
  isActive: boolean;
  typingText?: string | null;
}

export default function AgentPanel({ side, argument: arg, roundLabel, isActive, typingText }: AgentPanelProps) {
  const [expandReasoning, setExpandReasoning] = useState(false);
  const isPro = side === "pro";

  const accentBorder = isPro ? "border-emerald-500/40" : "border-rose-500/40";
  const accentGlow = isPro ? "shadow-emerald-900/30" : "shadow-rose-900/30";
  const accentText = isPro ? "text-emerald-400" : "text-rose-400";
  const accentBg = isPro ? "bg-emerald-900/20" : "bg-rose-900/20";
  const dotColor = isPro ? "bg-emerald-400" : "bg-rose-400";
  const strengthBar = isPro
    ? "bg-gradient-to-r from-emerald-700 to-emerald-400"
    : "bg-gradient-to-r from-rose-700 to-rose-400";

  if (!arg && !typingText) {
    return (
      <div
        className={`rounded-2xl border ${isActive ? accentBorder : "border-slate-700/50"} bg-white/[0.03] backdrop-blur-sm p-3 sm:p-5 min-h-[140px] sm:min-h-[180px] flex flex-col justify-center items-center text-slate-500 transition-all duration-300 shadow-lg ${isActive ? accentGlow : ""}`}
      >
        {isActive ? (
          <div className="flex flex-col items-center gap-3">
            <div className="flex gap-1.5 items-center h-5">
              {[0, 150, 300].map((delay) => (
                <span
                  key={delay}
                  className={`h-2 w-2 rounded-full ${dotColor} animate-bounce`}
                  style={{ animationDelay: `${delay}ms` }}
                />
              ))}
            </div>
            <span className={`text-xs font-medium ${accentText}`}>Thinking…</span>
          </div>
        ) : (
          <span className="text-sm text-slate-600">Awaiting turn</span>
        )}
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className={`rounded-2xl border ${accentBorder} ${accentBg} backdrop-blur-sm p-3 sm:p-5 shadow-lg ${accentGlow}`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <span className={`inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest ${accentText}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
          {isPro ? "Pro" : "Con"}
        </span>
        {roundLabel && (
          <span className="text-slate-600 text-xs">{roundLabel}</span>
        )}
      </div>

      {/* Claim / Typing text */}
      {typingText != null ? (
        <p className={`text-slate-100 font-semibold text-sm sm:text-base leading-relaxed min-h-[80px] typing-cursor`}>
          {typingText}
        </p>
      ) : arg ? (
        <>
          <p className="text-slate-100 font-semibold text-sm sm:text-base leading-relaxed mb-4">{arg.claim}</p>

          {/* Premises */}
          {arg.premises?.length > 0 && (
            <ul className="space-y-1.5 mb-4">
              {arg.premises.map((p: string, i: number) => (
                <li key={i} className="flex gap-2 text-sm text-slate-400">
                  <span className={`mt-0.5 flex-shrink-0 w-1.5 h-1.5 rounded-full ${dotColor} opacity-70 mt-1.5`} />
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          )}

          {/* Strength bar */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs text-slate-500 w-14">Strength</span>
            <div className="flex-1 h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <motion.div
                className={`h-full rounded-full ${strengthBar}`}
                initial={{ width: 0 }}
                animate={{ width: `${(arg.strength ?? 0) * 100}%` }}
                transition={{ duration: 0.8, ease: "easeOut" }}
              />
            </div>
            <span className="text-xs text-slate-400 tabular-nums w-8 text-right">
              {Math.round((arg.strength ?? 0) * 100)}%
            </span>
          </div>

          {/* Reasoning toggle */}
          <button
            type="button"
            onClick={() => setExpandReasoning((e) => !e)}
            className="text-xs text-slate-500 hover:text-slate-300 transition flex items-center gap-1"
          >
            <span className={`transition-transform ${expandReasoning ? "rotate-90" : ""}`}>▶</span>
            {expandReasoning ? "Hide" : "Show"} reasoning chain
          </button>

          <AnimatePresence>
            {expandReasoning && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="overflow-hidden"
              >
                <div className="mt-3 pt-3 border-t border-slate-700/50 text-xs text-slate-400 space-y-1">
                  <p className="font-medium text-slate-500">Inference</p>
                  <p>{arg.inference}</p>
                  {arg.reasoning_type && (
                    <p className="text-slate-500">Type: <span className="text-slate-400">{arg.reasoning_type}</span></p>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      ) : null}
    </motion.div>
  );
}
