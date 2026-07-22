import { useState } from "react";
import RiskIntel from "./pages/RiskIntel";
import CommandCenter from "./pages/CommandCenter";
import CorridorMap from "./pages/CorridorMap";
import KnowledgeGraph from "./pages/KnowledgeGraph";
import AskIntel from "./pages/AskIntel";
import Overview from "./pages/Overview";
import Timeline from "./pages/Timeline";
import Signals from "./pages/Signals";
import CompoundVsBaseline from "./pages/CompoundVsBaseline";
import Explanation from "./pages/Explanation";
import Assumptions from "./pages/Assumptions";

export default function App() {
  const [tab, setTab] = useState("intel");
  const [knobs, setKnobs] = useState({ h: 0.6, r: 0.3, o: 1 });

  const simulate = (h: number, r: number, o: number) => {
    setKnobs({ h, r, o });
    setTab("command");
  };

  const TABS = [
    { key: "intel", label: "Risk Intel", group: "live", el: <RiskIntel onSimulate={simulate} /> },
    { key: "command", label: "Command Center", group: "live", el: <CommandCenter knobs={knobs} setKnobs={setKnobs} /> },
    { key: "map", label: "Corridor Map", group: "live", el: <CorridorMap /> },
    { key: "graph", label: "Knowledge Graph", group: "live", el: <KnowledgeGraph /> },
    { key: "ask", label: "Intelligence Q&A", group: "live", el: <AskIntel /> },
    { key: "overview", label: "Detection", group: "model", el: <Overview /> },
    { key: "timeline", label: "Timeline", group: "model", el: <Timeline /> },
    { key: "signals", label: "Signals", group: "model", el: <Signals /> },
    { key: "compare", label: "Compound vs Baseline", group: "model", el: <CompoundVsBaseline /> },
    { key: "explain", label: "Explanation", group: "model", el: <Explanation /> },
    { key: "assumptions", label: "Assumptions", group: "model", el: <Assumptions /> },
  ];
  const active = TABS.find((t) => t.key === tab)!;
  const GROUPS = [
    { key: "live", label: "Live Intelligence" },
    { key: "model", label: "Detection Model" },
  ];
  const subtitle: Record<string, string> = {
    live: "Live corridor risk, scenario simulation & procurement response",
    model: "Compound disruption detection from weak public signals",
  };

  return (
    <div className="min-h-full p-3 md:p-5">
      <div className="mx-auto max-w-[1500px] rounded-[2rem] overflow-hidden shadow-2xl">
        {/* Warm gradient shell */}
        <div
          className="min-h-[95vh]"
          style={{
            background:
              "linear-gradient(135deg, #FBF7EF 0%, #F4ECD9 45%, #F1E4C4 100%)",
          }}
        >
          {/* Top bar */}
          <header className="flex items-center justify-between px-6 md:px-9 pt-6 pb-4">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-ink flex items-center justify-center shadow-card">
                <svg viewBox="0 0 24 24" className="w-6 h-6" fill="none" aria-hidden="true">
                  <path
                    d="M12 2.4l7.2 2.7v6.03c0 4.5-3.06 8.4-7.2 9.87-4.14-1.47-7.2-5.37-7.2-9.87V5.1L12 2.4z"
                    fill="#F5D45F"
                  />
                  <path
                    d="M12.9 7.1l-4.2 6.1h2.85l-.75 4.1 4.2-6.1h-2.85l.75-4.1z"
                    fill="#211F1A"
                  />
                </svg>
              </div>
              <div className="leading-tight">
                <div className="font-display font-semibold text-[19px] tracking-tight">
                  Energy<span className="text-goldDeep">Guardian</span>
                </div>
                <div className="text-[10.5px] text-ink/40 font-semibold uppercase tracking-[0.16em]">
                  Energy Supply-Chain Resilience
                </div>
              </div>
            </div>

            <div className="hidden md:flex items-center gap-2 text-xs font-semibold text-ink/50 bg-white/50 border border-black/5 rounded-full px-3.5 py-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-risk-low animate-pulse" />
              Red Sea corridor · 2023–24
            </div>
          </header>

          {/* Nav band */}
          <nav className="hidden lg:flex items-end gap-4 2xl:gap-6 px-6 md:px-9 pb-1 border-b border-black/[0.06]">
            {GROUPS.map((g) => (
              <div key={g.key} className="flex flex-col gap-1.5">
                <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-ink/35 pl-1">
                  {g.label}
                </span>
                <div className="flex items-center gap-0.5">
                  {TABS.filter((t) => t.group === g.key).map((t) => (
                    <button
                      key={t.key}
                      onClick={() => setTab(t.key)}
                      className={
                        "relative whitespace-nowrap px-2.5 2xl:px-3 py-2.5 text-xs 2xl:text-[13px] font-semibold transition-colors rounded-t-lg " +
                        (tab === t.key
                          ? "text-ink"
                          : "text-ink/45 hover:text-ink hover:bg-white/40")
                      }
                    >
                      {t.label}
                      {tab === t.key && (
                        <span className="absolute left-2.5 right-2.5 -bottom-px h-[2.5px] rounded-full bg-gold" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </nav>

          {/* Mobile nav */}
          <div className="lg:hidden px-4 pb-3 pt-1 flex flex-col gap-3 border-b border-black/[0.06]">
            {GROUPS.map((g) => (
              <div key={g.key} className="flex flex-col gap-1.5">
                <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-ink/35 px-1">
                  {g.label}
                </span>
                <div className="flex gap-1.5 overflow-x-auto no-scrollbar -mx-1 px-1">
                  {TABS.filter((t) => t.group === g.key).map((t) => (
                    <button
                      key={t.key}
                      onClick={() => setTab(t.key)}
                      className={
                        "px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition shrink-0 " +
                        (tab === t.key ? "bg-ink text-ivory" : "bg-white/60 text-ink/55")
                      }
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Title */}
          <div className="px-6 md:px-9 pt-6 pb-4">
            <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-goldDeep mb-1.5">
              {GROUPS.find((g) => g.key === active.group)?.label}
            </div>
            <h1 className="font-display text-4xl md:text-5xl font-semibold tracking-tight">{active.label}</h1>
            <p className="text-ink/45 mt-2 text-sm">{subtitle[active.group]}</p>
          </div>

          {/* Page content */}
          <main className="px-6 md:px-9 pb-10">{active.el}</main>
        </div>
      </div>
    </div>
  );
}
