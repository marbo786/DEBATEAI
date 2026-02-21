import { useEffect, useState } from "react";

export default function BeliefMeter({ belief, round, maxRounds }) {
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
      <div className="w-full h-8 rounded-full bg-slate-700 overflow-hidden flex">
        <div
          className="belief-fill h-full rounded-l-full bg-teal-500"
          style={{ width: `${displayWidth}%` }}
        />
        <div
          className="h-full rounded-r-full bg-amber-600"
          style={{ width: `${100 - displayWidth}%` }}
        />
      </div>
      <div className="flex justify-between w-full text-xs text-slate-400">
        <span>Pro {pct}%</span>
        <span>Con {100 - pct}%</span>
      </div>
    </div>
  );
}
