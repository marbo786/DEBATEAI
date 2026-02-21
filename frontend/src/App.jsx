import { useState } from "react";
import TopicInput from "./components/TopicInput";
import DebateView from "./components/DebateView";
import SummaryCard from "./components/SummaryCard";

export default function App() {
  const [debate, setDebate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleStart(topic) {
    setError(null);
    setLoading(true);
    try {
      const data = await import("./api").then((m) => m.startDebate(topic));
      setDebate(data);
    } catch (e) {
      setError(e.message);
      setDebate(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-body">
      <header className="border-b border-slate-700/50 bg-slate-900/80 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 py-5">
          <h1 className="font-display font-bold text-2xl tracking-tight text-center text-slate-100">
            DebateAI: Watch Algorithms Argue
          </h1>
          <p className="text-center text-slate-400 text-sm mt-1">
            Adversarial search · Logical reasoning · Probabilistic belief
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8">
        <TopicInput onStart={handleStart} loading={loading} />
        {error && (
          <div className="mt-4 rounded-lg bg-red-900/30 border border-red-700/50 text-red-200 px-4 py-3 text-sm">
            {error}
          </div>
        )}
        {debate && (
          <>
            <DebateView
              state={debate.state}
              history={debate.state?.history}
              factsFromApi={debate.facts_from_api}
            />
            {debate.state?.winner != null && (
              <SummaryCard
                summary={debate.summary}
                state={debate.state}
                onOverride={(overrideAudience) =>
                  import("./api")
                    .then((m) => m.getSummary(overrideAudience))
                    .then((s) => setDebate((d) => (d ? { ...d, summary: s } : d)))
                    .catch(() => {})
                }
              />
            )}
          </>
        )}
      </main>
    </div>
  );
}
