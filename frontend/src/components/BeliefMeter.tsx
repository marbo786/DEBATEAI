import { useEffect, useState } from "react";
import { motion } from "framer-motion";

export interface BeliefMeterProps {
  belief: number;
  round: number;
  maxRounds: number;
}

export default function BeliefMeter({ belief, round, maxRounds }: BeliefMeterProps) {
  const pct = Math.round((belief ?? 0.5) * 100);
  const [displayWidth, setDisplayWidth] = useState(pct);

  useEffect(() => {
    setDisplayWidth(pct);
  }, [pct]);

  return (
    <div className="flex flex-col items-center gap-2 w-full max-w-sm mx-auto">
      <span className="text-slate-400 text-sm font-medium">
        Round {round ?? 0} of {maxRounds ?? 6}
      </span>
      <div className="w-full h-8 rounded-full bg-slate-700 overflow-hidden flex relative">
        <motion.div
          className="absolute left-0 top-0 bottom-0 bg-teal-500"
          initial={{ width: `${displayWidth}%` }}
          animate={{ width: `${displayWidth}%` }}
          transition={{ type: "spring", stiffness: 100, damping: 20 }}
        />
        <motion.div
          className="absolute right-0 top-0 bottom-0 bg-amber-600"
          initial={{ width: `${100 - displayWidth}%` }}
          animate={{ width: `${100 - displayWidth}%` }}
          transition={{ type: "spring", stiffness: 100, damping: 20 }}
        />
      </div>
      <div className="flex justify-between w-full text-xs text-slate-400">
        <span>Pro {pct}%</span>
        <span>Con {100 - pct}%</span>
      </div>
    </div>
  );
}
