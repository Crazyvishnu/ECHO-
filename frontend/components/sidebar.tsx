"use client";
import { BrainCircuit, Clock3, Database, LayoutDashboard, PlusCircle, Scale, Sparkles } from "lucide-react";
type View = "dashboard" | "new" | "history" | "memory" | "debate" | "debate-new";
export function Sidebar({ view, setView }: { view: View; setView: (view: View) => void }) {
  const items = [["dashboard", "Dashboard", LayoutDashboard], ["debate-new", "Debate an idea", Scale], ["new", "New decision", PlusCircle], ["history", "Decision history", Clock3], ["memory", "Memory explorer", Database]] as const;
  return <aside className="sidebar"><div className="brand"><span className="brand-mark"><BrainCircuit size={20}/></span><span>echo<br/><b>chamber</b></span></div><nav>{items.map(([id, label, Icon]) => <button key={id} onClick={() => setView(id)} className={view === id ? "nav-item active" : "nav-item"}><Icon size={18}/><span>{label}</span></button>)}</nav><div className="sidebar-foot"><Sparkles size={15}/><span>Hindsight connected<br/><b>Outcome memory</b></span></div></aside>;
}
