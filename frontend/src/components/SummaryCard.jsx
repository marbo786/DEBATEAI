import { useRef, useState } from "react";
import html2canvas from "html2canvas";

export default function SummaryCard({ summary, state, onOverride }) {
  const cardRef = useRef(null);
  const [downloading, setDownloading] = useState(false);
  const [override, setOverride] = useState(null);

  const s = summary ?? {};
  const proPct = override != null ? Math.round(override * 100) : (s.final_pro_pct ?? 50);
  const conPct = override != null ? 100 - proPct : (s.final_con_pct ?? 50);
  const winner =
    override != null
      ? override > 0.5
        ? "Pro"
        : override < 0.5
          ? "Con"
          : "Tie"
      : s.winner === "pro"
        ? "Pro"
        : s.winner === "con"
          ? "Con"
          : "Tie";

  async function handleDownload() {
    if (!cardRef.current) return;
    setDownloading(true);
    try {
      const canvas = await html2canvas(cardRef.current, {
        backgroundColor: "#1e293b",
        scale: 2,
      });
      const link = document.createElement("a");
      link.download = `debateai-${(s.topic ?? "debate").replace(/\s+/g, "-")}.png`;
      link.href = canvas.toDataURL("image/png");
      link.click();
    } finally {
      setDownloading(false);
    }
  }

  function handleOverride(value) {
    setOverride(value);
    if (typeof onOverride === "function") onOverride(value);
  }

  return (
    <div className="mt-12 space-y-4">
      <h2 className="font-display font-bold text-xl text-slate-100">
        Debate summary
      </h2>
      <div
        ref={cardRef}
        className="rounded-2xl border-2 border-slate-600 bg-slate-800 p-6 text-slate-100 shadow-xl"
      >
        <div className="flex flex-col gap-6">
          {/* 1. Topic as main title */}
          <div>
            <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1">Topic</p>
            <p className="text-xl font-bold text-slate-100">{s.topic ?? state?.topic}</p>
          </div>

          {/* 2. Winner with strong emphasis */}
          <div>
            <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1">Winner</p>
            <p
              className={
                winner === "Pro"
                  ? "text-teal-400 font-bold text-2xl"
                  : winner === "Con"
                    ? "text-amber-400 font-bold text-2xl"
                    : "text-slate-300 font-bold text-2xl"
              }
            >
              {winner}
            </p>
          </div>

          {/* 3. Final result: bar + large percentages */}
          <div>
            <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">Final result</p>
            <div className="flex items-center gap-3 mb-2">
              <span className="text-teal-400 font-semibold text-lg w-16">Pro {proPct}%</span>
              <div className="flex-1 h-6 rounded-full bg-slate-700 overflow-hidden flex">
                <div
                  className="h-full bg-teal-500 transition-all duration-300"
                  style={{ width: `${proPct}%` }}
                />
                <div
                  className="h-full bg-amber-600 transition-all duration-300"
                  style={{ width: `${conPct}%` }}
                />
              </div>
              <span className="text-amber-400 font-semibold text-lg w-16 text-right">Con {conPct}%</span>
            </div>
          </div>

          {/* 4. Turning point */}
          {s.turning_point_round != null && (
            <div>
              <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1">Turning point round</p>
              <p className="text-slate-200 font-medium">Round {s.turning_point_round}</p>
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <button
          type="button"
          onClick={handleDownload}
          disabled={downloading}
          className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-500 disabled:opacity-50 transition"
        >
          {downloading ? "Downloading…" : "Download as image"}
        </button>
        <div className="flex items-center gap-2">
          <span className="text-slate-500 text-sm">Override audience:</span>
          <button
            type="button"
            onClick={() => handleOverride(1)}
            className={`rounded-md px-3 py-1.5 text-sm transition ${
              override === 1 ? "bg-teal-600 text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            Pro
          </button>
          <button
            type="button"
            onClick={() => handleOverride(0.5)}
            className={`rounded-md px-3 py-1.5 text-sm transition ${
              override === 0.5 ? "bg-slate-500 text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            Neutral
          </button>
          <button
            type="button"
            onClick={() => handleOverride(0)}
            className={`rounded-md px-3 py-1.5 text-sm transition ${
              override === 0 ? "bg-amber-600 text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            Con
          </button>
          <button
            type="button"
            onClick={() => handleOverride(null)}
            className="rounded-md px-3 py-1.5 text-sm bg-slate-700 text-slate-400 hover:bg-slate-600 transition"
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}
