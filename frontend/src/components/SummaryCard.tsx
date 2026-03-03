import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import html2canvas from "html2canvas";
import type { SummaryPayload, DebateState } from "../types";
import BeliefChart from "./BeliefChart";

export interface SummaryCardProps {
  summary: SummaryPayload;
  state: DebateState;
  onOverride: (value: number | null) => Promise<boolean>;
}

// These are the STARTING PRIOR beliefs for the replay.
// 0.65 = audience starts leaning Pro; 0.5 = neutral; 0.35 = audience starts leaning Con.
// The backend replays all debate history through a BeliefModel at this prior.
const AUDIENCE_OPTIONS = [
  {
    value: 0.65,
    label: "Pro-Leaning",
    desc: "Audience starts at 65% Pro",
    accent: "emerald",
  },
  {
    value: 0.5,
    label: "Neutral",
    desc: "Unbiased starting audience",
    accent: "slate",
  },
  {
    value: 0.35,
    label: "Con-Leaning",
    desc: "Audience starts at 35% Con",
    accent: "rose",
  },
];

export default function SummaryCard({ summary, state, onOverride }: SummaryCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [downloading, setDownloading] = useState(false);
  const [previewOverride, setPreviewOverride] = useState<number | null>(null);
  const [isOverrideLoading, setIsOverrideLoading] = useState(false);

  const s = summary;

  useEffect(() => {
    setPreviewOverride(null);
  }, [summary]);

  const effectiveProPct = useMemo(() => {
    if (previewOverride == null) return s.final_pro_pct ?? 50;
    return Math.round(previewOverride * 100);
  }, [previewOverride, s.final_pro_pct]);

  const proPct = effectiveProPct;
  const conPct = previewOverride == null ? (s.final_con_pct ?? 50) : 100 - effectiveProPct;
  const winner =
    previewOverride != null
      ? previewOverride > 0.5 ? "Pro" : previewOverride < 0.5 ? "Con" : "Tie"
      : s.winner === "pro" ? "Pro" : s.winner === "con" ? "Con" : "Tie";

  async function handleDownload() {
    if (!cardRef.current) return;
    setDownloading(true);
    try {
      const canvas = await html2canvas(cardRef.current, {
        backgroundColor: "#080d18",
        scale: 2,
        useCORS: true,
      });
      const link = document.createElement("a");
      link.download = `debateai-${(s.topic ?? "debate").replace(/\s+/g, "-")}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
    } finally {
      setDownloading(false);
    }
  }

  async function handleOverride(value: number | null) {
    if (isOverrideLoading) return;
    setPreviewOverride(value);
    if (value == null || typeof onOverride !== "function") return;
    setIsOverrideLoading(true);
    try {
      const ok = await onOverride(value);
      if (!ok) setPreviewOverride(null);
    } catch {
      setPreviewOverride(null);
    } finally {
      setIsOverrideLoading(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 32 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="mt-12 space-y-4"
    >
      {/* Section header */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-slate-700 to-transparent" />
        <h2 className="text-xs font-bold tracking-widest text-slate-500 uppercase">Debate Summary</h2>
        <div className="flex-1 h-px bg-gradient-to-l from-transparent via-slate-700 to-transparent" />
      </div>

      {/* Main card (this is captured for download) */}
      <div
        ref={cardRef}
        className="rounded-2xl border border-white/[0.07] bg-white/[0.025] backdrop-blur-sm p-6 shadow-2xl overflow-hidden relative"
      >
        {/* Subtle top glow */}
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent" />

        <div className="flex flex-col gap-6">
          {/* Topic */}
          <div>
            <p className="text-xs font-bold tracking-widest text-slate-600 uppercase mb-1">Topic</p>
            <p className="text-lg font-bold text-slate-100 leading-snug">{s.topic ?? state?.topic}</p>
          </div>

          {/* Winner */}
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs font-bold tracking-widest text-slate-600 uppercase mb-1">Winner</p>
              <p
                className={`font-extrabold text-3xl tracking-tight ${winner === "Pro"
                  ? "text-emerald-400"
                  : winner === "Con"
                    ? "text-rose-400"
                    : "text-slate-400"
                  }`}
              >
                {winner}
              </p>
            </div>
            {s.turning_point_round != null && (
              <div className="ml-auto text-right">
                <p className="text-xs font-bold tracking-widest text-slate-600 uppercase mb-1">Turning Point</p>
                <p className="text-slate-300 font-semibold">Round {s.turning_point_round}</p>
              </div>
            )}
          </div>

          {/* Final belief bar */}
          <div>
            <p className="text-xs font-bold tracking-widest text-slate-600 uppercase mb-3">Final Result</p>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-emerald-400 font-bold text-sm tabular-nums w-14">Pro {proPct}%</span>
              <div className="flex-1 h-4 rounded-full bg-slate-800 border border-slate-700/50 overflow-hidden flex">
                <motion.div
                  className="h-full bg-gradient-to-r from-emerald-700 to-emerald-400"
                  animate={{ width: `${proPct}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                />
                <motion.div
                  className="h-full bg-gradient-to-l from-rose-700 to-rose-400"
                  animate={{ width: `${conPct}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                />
              </div>
              <span className="text-rose-400 font-bold text-sm tabular-nums w-14 text-right">Con {conPct}%</span>
            </div>
          </div>

          {/* Belief trajectory chart */}
          {(state?.belief_history?.length ?? 0) >= 2 && (
            <BeliefChart
              beliefHistory={state!.belief_history!}
              maxRounds={state!.max_rounds}
              turningPointRound={s.turning_point_round}
              className="mt-2"
            />
          )}

          {/* Stats row */}
          <div className="flex gap-4 flex-wrap">
            {s.total_rounds != null && (
              <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 px-4 py-2 text-center">
                <p className="text-xs text-slate-500 mb-0.5">Total Rounds</p>
                <p className="text-slate-200 font-bold">{s.total_rounds}</p>
              </div>
            )}
            <div className="rounded-xl border border-emerald-800/50 bg-emerald-900/20 px-4 py-2 text-center">
              <p className="text-xs text-emerald-600 mb-0.5">Pro Confidence</p>
              <p className="text-emerald-300 font-bold">{proPct}%</p>
            </div>
            <div className="rounded-xl border border-rose-800/50 bg-rose-900/20 px-4 py-2 text-center">
              <p className="text-xs text-rose-600 mb-0.5">Con Confidence</p>
              <p className="text-rose-300 font-bold">{conPct}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Actions Section */}
      <div className="rounded-2xl border border-white/[0.05] bg-white/[0.015] backdrop-blur-sm p-5 space-y-5">

        {/* Audience override */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-bold tracking-widest text-slate-500 uppercase">
              Re-score for Audience
            </span>
            {isOverrideLoading && (
              <span className="w-3 h-3 border border-slate-500 border-t-slate-300 rounded-full animate-spin" />
            )}
            {previewOverride != null && (
              <button
                type="button"
                onClick={() => handleOverride(null)}
                className="ml-auto text-xs text-slate-500 hover:text-slate-300 transition"
              >
                ✕ Reset
              </button>
            )}
          </div>
          <p className="text-xs text-slate-600 mb-3">
            Replay the debate through a different starting audience. The arguments stay the same — only the audience bias changes.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {AUDIENCE_OPTIONS.map((opt) => {
              const isActive = previewOverride === opt.value;
              const borderMap: Record<string, string> = {
                emerald: isActive ? "border-emerald-500/60 bg-emerald-900/30 text-emerald-300" : "border-slate-700/40 bg-slate-800/30 text-slate-400 hover:border-emerald-800/60 hover:text-emerald-400",
                slate: isActive ? "border-slate-500/60 bg-slate-700/40 text-slate-200" : "border-slate-700/40 bg-slate-800/30 text-slate-400 hover:border-slate-600/60 hover:text-slate-300",
                rose: isActive ? "border-rose-500/60 bg-rose-900/30 text-rose-300" : "border-slate-700/40 bg-slate-800/30 text-slate-400 hover:border-rose-800/60 hover:text-rose-400",
              };
              return (
                <button
                  key={opt.value}
                  type="button"
                  disabled={isOverrideLoading}
                  onClick={() => handleOverride(opt.value)}
                  className={`rounded-xl px-3 py-3 text-left transition border text-xs disabled:opacity-50 ${borderMap[opt.accent]}`}
                >
                  <div className="font-bold mb-0.5">{opt.label}</div>
                  <div className="text-[10px] opacity-70">{opt.desc}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Download */}
        <div className="pt-3 border-t border-white/[0.05]">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <p className="text-xs font-bold tracking-widest text-slate-500 uppercase mb-0.5">Share Results</p>
              <p className="text-xs text-slate-600">Download the summary card as a PNG image</p>
            </div>
            <motion.button
              type="button"
              onClick={handleDownload}
              disabled={downloading}
              whileHover={{ scale: downloading ? 1 : 1.03 }}
              whileTap={{ scale: 0.97 }}
              className="flex items-center gap-2 rounded-xl border border-slate-600/50 bg-slate-800/60 hover:bg-slate-700/60 px-4 py-2.5 text-sm font-semibold text-slate-300 hover:text-slate-100 transition disabled:opacity-50"
            >
              {downloading ? (
                <>
                  <span className="w-3.5 h-3.5 border border-slate-400 border-t-white rounded-full animate-spin" />
                  Saving…
                </>
              ) : (
                <>
                  <span>⬇</span>
                  Download PNG
                </>
              )}
            </motion.button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
