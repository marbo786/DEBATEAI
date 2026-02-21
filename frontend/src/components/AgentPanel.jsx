import { useState } from "react";

export default function AgentPanel({ side, argument: arg, roundLabel, isActive }) {
  const [expandReasoning, setExpandReasoning] = useState(false);
  const isPro = side === "pro";

  if (!arg) {
    return (
      <div
        className={`rounded-xl border-2 border-slate-600 bg-slate-800/40 p-5 min-h-[200px] flex flex-col justify-center items-center text-slate-500`}
      >
        <span className="text-sm">Waiting for argument…</span>
      </div>
    );
  }

  const borderClass = isActive
    ? isPro
      ? "border-teal-500 bg-slate-800/60"
      : "border-amber-500 bg-slate-800/60"
    : "border-slate-600 bg-slate-800/40";

  return (
    <div className={`rounded-xl border-2 ${borderClass} p-5 transition`}>
      <div className="flex items-center gap-2 mb-3">
        <span
          className={`text-xs font-semibold uppercase tracking-wider ${
            isPro ? "text-teal-400" : "text-amber-400"
          }`}
        >
          {isPro ? "Pro" : "Con"}
        </span>
        {roundLabel && (
          <span className="text-slate-500 text-xs">{roundLabel}</span>
        )}
      </div>
      <p className="text-slate-100 font-medium mb-3">{arg.claim}</p>
      <div className="space-y-1 text-sm text-slate-400">
        {arg.premises?.map((p, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-slate-500">•</span>
            <span>{p}</span>
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2">
        <span className="text-xs text-slate-500">Strength</span>
        <div className="flex-1 h-1.5 rounded-full bg-slate-700 overflow-hidden">
          <div
            className={`h-full rounded-full ${
              isPro ? "bg-teal-500" : "bg-amber-500"
            }`}
            style={{ width: `${(arg.strength ?? 0) * 100}%` }}
          />
        </div>
        <span className="text-xs text-slate-400 w-8">
          {Math.round((arg.strength ?? 0) * 100)}%
        </span>
      </div>
      <button
        type="button"
        onClick={() => setExpandReasoning((e) => !e)}
        className="mt-3 text-xs text-slate-500 hover:text-slate-300 transition"
      >
        {expandReasoning ? "Hide" : "Show"} reasoning chain
      </button>
      {expandReasoning && (
        <div className="mt-2 pt-2 border-t border-slate-600 text-xs text-slate-400">
          <p className="font-medium text-slate-500 mb-1">Inference</p>
          <p>{arg.inference}</p>
          {arg.reasoning_type && (
            <p className="mt-1 text-slate-500">Type: {arg.reasoning_type}</p>
          )}
        </div>
      )}
    </div>
  );
}
