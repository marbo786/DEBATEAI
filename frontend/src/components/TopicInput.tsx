import { useState } from "react";

interface TopicInputProps {
  onStart: (topic: string, persona: string, userSide: string) => void;
  loading: boolean;
}

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
      className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center max-w-3xl mx-auto"
    >
      <input
        type="text"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="Enter debate topic (e.g. Universal Basic Income)"
        className="flex-1 rounded-lg border border-slate-600 bg-slate-800/80 px-4 py-3 text-slate-100 placeholder-slate-500 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500 transition"
        disabled={loading}
      />
      <select
        value={persona}
        onChange={(e) => setPersona(e.target.value)}
        disabled={loading}
        className="rounded-lg border border-slate-600 bg-slate-800/80 px-4 py-3 text-slate-100 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500 transition cursor-pointer"
      >
        <option value="default">Balanced</option>
        <option value="skeptic">Skeptic</option>
        <option value="gullible">Gullible</option>
        <option value="partisan_pro">Pro-leaning</option>
      </select>
      <select
        value={userSide}
        onChange={(e) => setUserSide(e.target.value)}
        disabled={loading}
        className="rounded-lg border border-slate-600 bg-slate-800/80 px-4 py-3 text-slate-100 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500 transition cursor-pointer"
      >
        <option value="auto">Spectate (Auto)</option>
        <option value="pro">Play as Pro</option>
        <option value="con">Play as Con</option>
      </select>
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
