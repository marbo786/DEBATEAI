import { useState } from "react";
import { motion } from "framer-motion";

interface TopicInputProps {
  onStart: (topic: string, persona: string, userSide: string) => void;
  loading: boolean;
}

const PERSONAS = [
  { value: "default", label: "⚖️ Balanced", desc: "Equal weight to logic & emotion" },
  { value: "skeptic", label: "🔬 Skeptic", desc: "Demands hard evidence" },
  { value: "gullible", label: "💭 Credulous", desc: "Swayed by emotional arguments" },
  { value: "partisan_pro", label: "📢 Pro-leaning", desc: "Biased toward the Pro side" },
];

const SIDES = [
  { value: "auto", label: "👁️ Spectate", desc: "Watch AI vs. AI" },
  { value: "pro", label: "✦ Play Pro", desc: "Argue in favor" },
  { value: "con", label: "✦ Play Con", desc: "Argue against" },
];

export default function TopicInput({ onStart, loading }: TopicInputProps) {
  const [topic, setTopic] = useState("");
  const [persona, setPersona] = useState("default");
  const [userSide, setUserSide] = useState("auto");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (topic.trim()) onStart(topic.trim(), persona, userSide);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-white/[0.07] bg-white/[0.025] backdrop-blur-sm p-4 sm:p-6 shadow-2xl"
    >
      {/* Topic input */}
      <div className="mb-5">
        <label className="block text-xs font-bold tracking-widest text-slate-500 uppercase mb-2">
          Debate Topic
        </label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. AI will replace most human jobs in 20 years"
          className="w-full rounded-xl border border-slate-700/60 bg-slate-900/70 px-4 py-3.5 text-slate-100 placeholder-slate-600 focus:border-emerald-500/60 focus:outline-none focus:ring-1 focus:ring-emerald-500/30 transition text-base"
          disabled={loading}
        />
      </div>

      {/* Options row */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        {/* Audience persona */}
        <div className="flex-1">
          <label className="block text-xs font-bold tracking-widest text-slate-500 uppercase mb-2">
            Audience Persona
          </label>
          <div className="grid grid-cols-2 gap-2">
            {PERSONAS.map((p) => (
              <button
                key={p.value}
                type="button"
                disabled={loading}
                onClick={() => setPersona(p.value)}
                className={`rounded-xl px-3 py-2.5 text-left transition border text-xs ${persona === p.value
                  ? "border-emerald-500/60 bg-emerald-900/30 text-emerald-300"
                  : "border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600 hover:text-slate-300"
                  }`}
              >
                <div className="font-semibold">{p.label}</div>
                <div className="text-[10px] opacity-70 mt-0.5">{p.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Play mode */}
        <div className="flex-1">
          <label className="block text-xs font-bold tracking-widest text-slate-500 uppercase mb-2">
            Play Mode
          </label>
          <div className="flex flex-col gap-2">
            {SIDES.map((s) => (
              <button
                key={s.value}
                type="button"
                disabled={loading}
                onClick={() => setUserSide(s.value)}
                className={`rounded-xl px-3 py-2.5 text-left transition border text-xs ${userSide === s.value
                  ? s.value === "auto"
                    ? "border-slate-500/60 bg-slate-700/40 text-slate-200"
                    : s.value === "pro"
                      ? "border-emerald-500/60 bg-emerald-900/30 text-emerald-300"
                      : "border-rose-500/60 bg-rose-900/30 text-rose-300"
                  : "border-slate-700/50 bg-slate-800/40 text-slate-400 hover:border-slate-600 hover:text-slate-300"
                  }`}
              >
                <div className="font-semibold">{s.label}</div>
                <div className="text-[10px] opacity-70 mt-0.5">{s.desc}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Submit */}
      <motion.button
        type="submit"
        disabled={loading || !topic.trim()}
        whileHover={{ scale: loading || !topic.trim() ? 1 : 1.01 }}
        whileTap={{ scale: 0.98 }}
        className="w-full rounded-xl py-3.5 font-bold text-sm text-white transition disabled:opacity-40 disabled:cursor-not-allowed relative overflow-hidden"
        style={{
          background: loading || !topic.trim()
            ? "#1e293b"
            : "linear-gradient(135deg, #059669 0%, #10b981 50%, #34d399 100%)",
          boxShadow: loading || !topic.trim() ? "none" : "0 0 30px rgba(16,185,129,0.25)",
        }}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Starting Debate…
          </span>
        ) : (
          "⚔️ Start Debate"
        )}
      </motion.button>
    </form>
  );
}
