import { motion, AnimatePresence } from "framer-motion";

export interface BeliefMeterProps {
  belief: number;
  round: number;
  maxRounds: number;
}

export default function BeliefMeter({ belief, round, maxRounds }: BeliefMeterProps) {
  const pct = Math.round((belief ?? 0.5) * 100);
  const conPct = 100 - pct;
  const isPro = pct > 50;
  const isTie = pct === 50;

  return (
    <div className="flex flex-col items-center gap-4 w-full">
      {/* Header */}
      <div className="flex items-center justify-between w-full">
        <span className="text-xs font-bold tracking-widest text-emerald-400 uppercase">Pro</span>
        <div className="flex flex-col items-center">
          <span className="text-slate-400 text-xs font-medium">
            Round <span className="text-white font-bold">{round}</span> / {maxRounds}
          </span>
        </div>
        <span className="text-xs font-bold tracking-widest text-rose-400 uppercase">Con</span>
      </div>

      {/* Belief bar */}
      <div className="w-full h-5 rounded-full bg-slate-800 border border-slate-700 overflow-hidden flex shadow-inner">
        <motion.div
          className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-l-full"
          initial={{ width: "50%" }}
          animate={{ width: `${pct}%` }}
          transition={{ type: "spring", stiffness: 80, damping: 18 }}
        />
        <motion.div
          className="h-full bg-gradient-to-l from-rose-600 to-rose-400 rounded-r-full"
          initial={{ width: "50%" }}
          animate={{ width: `${conPct}%` }}
          transition={{ type: "spring", stiffness: 80, damping: 18 }}
        />
      </div>

      {/* Percentages + winning label */}
      <div className="flex justify-between w-full">
        <motion.span
          key={pct}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className={`text-sm font-bold tabular-nums ${isPro ? "text-emerald-300" : "text-slate-400"}`}
        >
          {pct}%
        </motion.span>
        <AnimatePresence mode="wait">
          {isTie ? (
            <motion.span
              key="tie"
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              className="text-xs font-semibold text-slate-400 bg-slate-700/60 px-2 py-0.5 rounded-full border border-slate-600"
            >
              Tied
            </motion.span>
          ) : (
            <motion.span
              key={isPro ? "pro-lead" : "con-lead"}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${isPro
                  ? "text-emerald-300 bg-emerald-900/40 border-emerald-700/50"
                  : "text-rose-300 bg-rose-900/40 border-rose-700/50"
                }`}
            >
              {isPro ? "Pro leads" : "Con leads"}
            </motion.span>
          )}
        </AnimatePresence>
        <motion.span
          key={conPct}
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className={`text-sm font-bold tabular-nums ${!isPro && !isTie ? "text-rose-300" : "text-slate-400"}`}
        >
          {conPct}%
        </motion.span>
      </div>
    </div>
  );
}
