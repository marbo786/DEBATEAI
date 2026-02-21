import { useState } from "react";

export default function TopicInput({ onStart, loading }) {
  const [topic, setTopic] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (topic.trim()) onStart(topic.trim());
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center max-w-2xl mx-auto"
    >
      <input
        type="text"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="Enter debate topic (e.g. Universal Basic Income)"
        className="flex-1 rounded-lg border border-slate-600 bg-slate-800/80 px-4 py-3 text-slate-100 placeholder-slate-500 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500 transition"
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading || !topic.trim()}
        className="rounded-lg bg-teal-600 px-6 py-3 font-semibold text-white hover:bg-teal-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
      >
        {loading ? "Running debate…" : "Start Debate"}
      </button>
    </form>
  );
}
