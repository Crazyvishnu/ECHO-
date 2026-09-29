"use client";
import { useState } from "react";
import { CircleAlert, LoaderCircle, Scale, ShieldOff, Sparkles, ThumbsUp, Gavel } from "lucide-react";
import { api, Debate, DebateTurn } from "@/lib/api";

const AGENT_META = {
  supporter: { label: "Supporter", icon: ThumbsUp, tone: "pro" },
  opposer: { label: "Opposer", icon: ShieldOff, tone: "con" },
} as const;

const VERDICT_META: Record<string, { label: string; className: string }> = {
  proceed: { label: "Proceed", className: "verdict-pro" },
  proceed_with_changes: { label: "Proceed with changes", className: "verdict-changes" },
  do_not_proceed: { label: "Do not proceed", className: "verdict-no" },
};

function TurnBubble({ turn }: { turn: DebateTurn }) {
  const meta = AGENT_META[turn.agent as keyof typeof AGENT_META];
  const Icon = meta.icon;
  return (
    <div className={`turn ${meta.tone}`}>
      <div className="turn-head">
        <span className={`turn-glyph ${meta.tone}`}><Icon size={16} /></span>
        <b>{meta.label}</b>
        <span className="turn-round">Round {turn.round}</span>
      </div>
      <p>{turn.argument}</p>
      {turn.weaknesses_found.length > 0 && (
        <div className="turn-weaknesses">
          {turn.weaknesses_found.map((w, i) => <span key={i}>{w}</span>)}
        </div>
      )}
    </div>
  );
}

export function DebateView({ debate, onClose }: { debate: Debate; onClose?: () => void }) {
  if (!debate) return null;
  const verdict = debate.verdict;
  const verdictMeta = verdict ? VERDICT_META[verdict.decision] : null;
  return (
    <section className="debate">
      <div className="eyebrow">Three-agent debate</div>
      <div className="analysis-heading">
        <div>
          <h1>{debate.topic}</h1>
          <p>{debate.description}</p>
        </div>
        {onClose && <button className="text-button" onClick={onClose}>Close</button>}
      </div>

      {debate.memory_used.length > 0 && (
        <article className="memory-panel">
          <div className="memory-icon"><Sparkles size={20} /></div>
          <div className="memory-copy">
            <div className="eyebrow">Memory used <span>Recalled from Hindsight</span></div>
            <h2>{debate.memory_used.length} past {debate.memory_used.length === 1 ? "memory" : "memories"} informed this debate</h2>
            {debate.memory_used.map((m) => (
              <div key={m.id} className="memory-item"><b>{m.kind}</b><span>{m.text}</span></div>
            ))}
          </div>
        </article>
      )}

      <div className="turns">
        {debate.turns.map((turn, i) => <TurnBubble key={i} turn={turn} />)}
      </div>

      {verdict && verdictMeta && (
        <article className={`verdict-panel ${verdictMeta.className}`}>
          <div className="verdict-head">
            <span className="verdict-glyph"><Gavel size={20} /></span>
            <div>
              <div className="eyebrow">Judge's verdict</div>
              <h2>{verdictMeta.label}</h2>
            </div>
            <div className="confidence"><span>{verdict.confidence}</span><small>confidence</small></div>
          </div>
          <p>{verdict.reasoning}</p>
          {verdict.conditions.length > 0 && (
            <div className="verdict-conditions">
              <b>Conditions to clear</b>
              <ul>{verdict.conditions.map((c, i) => <li key={i}>{c}</li>)}</ul>
            </div>
          )}
          {verdict.memory_influence && (
            <div className="verdict-memory"><Scale size={15} /><span>{verdict.memory_influence}</span></div>
          )}
        </article>
      )}
    </section>
  );
}

export function NewDebateForm({ onDone, onError }: { onDone: (d: Debate) => void; onError: (m: string) => void }) {
  const [topic, setTopic] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const debate = await api.createDebate({ topic, description, rounds: 2 });
      onDone(debate);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unable to run the debate.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="new-decision" onSubmit={submit}>
      <div className="eyebrow">New debate</div>
      <h1>Put an idea on trial</h1>
      <p>A SUPPORTER argues for it, an OPPOSER argues against it, and a JUDGE rules on what is best to do. Past debate lessons from memory are cited in the arguments.</p>
      <label>Topic
        <input required value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g. Launch an AI cover-letter generator" />
      </label>
      <label>The idea
        <textarea required value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Describe the idea, who it serves, and why now." />
      </label>
      <button className="primary" disabled={loading}>
        {loading ? <LoaderCircle className="spin" /> : <Scale />} Run the debate
      </button>
    </form>
  );
}
