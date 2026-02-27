import { useEffect, useMemo, useRef, useState } from "react";
import html2canvas from "html2canvas";

export default function SummaryCard({ summary, state, onOverride }) {
  const cardRef = useRef(null);
  const [downloading, setDownloading] = useState(false);
  const [previewOverride, setPreviewOverride] = useState(null);
  const [isOverrideLoading, setIsOverrideLoading] = useState(false);

  const s = summary ?? {};

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
      ? previewOverride > 0.5
        ? "Pro"
        : previewOverride < 0.5
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

  async function handleOverride(value) {
    if (isOverrideLoading) return;
    setPreviewOverride(value);
    if (value == null || typeof onOverride !== "function") return;

    setIsOverrideLoading(true);
    try {
      const succeeded = await onOverride(value);
      if (!succeeded) {
        setPreviewOverride(null);
      }
    } catch {
      setPreviewOverride(null);
    } finally {
      setIsOverrideLoading(false);
    }
  }

  return (
    <div className="mt-12 space-y-4">
      <h2 className="font-display font-bold text-xl text-slate-100">
        Debate summary
      </h2>
      {isOverrideLoading && (
        <p className="text-xs text-slate-400" role="status">Updating summary…</p>
      )}
      <div
        ref={cardRef}
        className="rounded-2xl border-2 border-slate-600 bg-slate-800 p-6 text-slate-100 shadow-xl"
      >
        <div className="flex flex-col gap-6">
          <div>
            <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1">Topic</p>
            <p className="text-xl font-bold text-slate-100">{s.topic ?? state?.topic}</p>
          </div>

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
            disabled={isOverrideLoading}
            className={`rounded-md px-3 py-1.5 text-sm transition disabled:opacity-50 ${
              previewOverride === 1 ? "bg-teal-600 text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            Pro
          </button>
          <button
            type="button"
            onClick={() => handleOverride(0.5)}
            disabled={isOverrideLoading}
            className={`rounded-md px-3 py-1.5 text-sm transition disabled:opacity-50 ${
              previewOverride === 0.5 ? "bg-slate-500 text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            Neutral
          </button>
          <button
            type="button"
            onClick={() => handleOverride(0)}
            disabled={isOverrideLoading}
            className={`rounded-md px-3 py-1.5 text-sm transition disabled:opacity-50 ${
              previewOverride === 0 ? "bg-amber-600 text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"
            }`}
          >
            Con
          </button>
          <button
            type="button"
            onClick={() => handleOverride(null)}
            disabled={isOverrideLoading}
            className="rounded-md px-3 py-1.5 text-sm bg-slate-700 text-slate-400 hover:bg-slate-600 transition disabled:opacity-50"
          >
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}
