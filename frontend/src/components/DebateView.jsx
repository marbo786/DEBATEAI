import { useState, useMemo } from "react";
import AgentPanel from "./AgentPanel";
import BeliefMeter from "./BeliefMeter";

/** Group history by debate round: round 1 = [Pro, Con], round 2 = [Pro, Con], ... */
function getRoundPairs(history) {
  const h = history ?? [];
  const pairs = [];
  for (let r = 0; r < h.length; r += 2) {
    pairs.push({
      roundNum: pairs.length + 1,
      pro: h[r]?.side === "pro" ? h[r] : null,
      con: h[r + 1]?.side === "con" ? h[r + 1] : null,
    });
  }
  return pairs;
}

export default function DebateView({ state, history, factsFromApi }) {
  const maxRounds = state?.max_rounds ?? 6;
  const roundPairs = useMemo(() => getRoundPairs(history), [history]);
  const [selectedRound, setSelectedRound] = useState(1);

  const belief = state?.belief ?? 0.5;
  const displayRound = state?.round ?? 0;

  const pair = roundPairs.find((p) => p.roundNum === selectedRound) ?? roundPairs[0] ?? null;
  const proForRound = pair?.pro ?? null;
  const conForRound = pair?.con ?? null;

  return (
    <div className="mt-10 space-y-8">
      {/* Topic and round selector */}
      {state?.topic && (
        <div className="rounded-xl border border-slate-600 bg-slate-800/50 px-4 py-3">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-slate-400 text-sm font-medium">Debate topic</p>
            {factsFromApi && (
              <span className="rounded-md bg-teal-900/60 text-teal-300 text-xs font-medium px-2 py-0.5 border border-teal-700/50">
                Using API facts
              </span>
            )}
          </div>
          <p className="text-slate-100 text-lg font-semibold">{state.topic}</p>
        </div>
      )}

      {/* Round selector: "Round 1" … "Round 6" */}
      {roundPairs.length > 0 && (
        <div className="rounded-xl border border-slate-600 bg-slate-800/50 p-4">
          <p className="text-slate-300 font-medium mb-3">View round</p>
          <div className="flex flex-wrap gap-2">
            {roundPairs.map(({ roundNum }) => (
              <button
                key={roundNum}
                type="button"
                onClick={() => setSelectedRound(roundNum)}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                  selectedRound === roundNum
                    ? "bg-teal-600 text-white ring-2 ring-teal-400"
                    : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                }`}
              >
                Round {roundNum}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Main debate: Pro | Meter | Con for selected round */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
        <div className="order-2 md:order-1">
          <AgentPanel
            side="pro"
            argument={proForRound?.argument ?? null}
            roundLabel={pair ? `Round ${pair.roundNum} — Pro` : null}
            isActive={!!proForRound}
          />
        </div>
        <div className="order-1 md:order-2 flex flex-col gap-4">
          <BeliefMeter belief={belief} round={displayRound} maxRounds={maxRounds} />
          {state?.winner != null && (
            <div className="text-center">
              <span className="text-slate-400 text-sm">Winner: </span>
              <span
                className={
                  state.winner === "pro"
                    ? "text-teal-400 font-semibold"
                    : "text-amber-400 font-semibold"
                }
              >
                {state.winner === "pro" ? "Pro" : "Con"}
              </span>
            </div>
          )}
        </div>
        <div className="order-3">
          <AgentPanel
            side="con"
            argument={conForRound?.argument ?? null}
            roundLabel={pair ? `Round ${pair.roundNum} — Con` : null}
            isActive={!!conForRound}
          />
        </div>
      </div>

      {/* All moves list (optional detail) */}
      {(history?.length ?? 0) > 0 && (
        <details className="rounded-lg border border-slate-600 bg-slate-800/40 p-4">
          <summary className="text-slate-400 text-sm font-medium cursor-pointer hover:text-slate-300">
            All moves (Pro #1, Con #2, …)
          </summary>
          <div className="flex flex-wrap gap-2 mt-3">
            {history.map((r, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setSelectedRound(Math.floor(i / 2) + 1)}
                className={`rounded-md px-3 py-1.5 text-sm transition ${
                  r.side === "pro" ? "bg-teal-800/80 text-teal-200" : "bg-amber-900/50 text-amber-200"
                } hover:opacity-90`}
              >
                {r.side === "pro" ? "Pro" : "Con"} #{i + 1}
              </button>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
