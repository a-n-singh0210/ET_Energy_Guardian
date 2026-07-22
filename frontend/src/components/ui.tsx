import type { ReactNode } from "react";
import { RISK_COLORS, type RiskLevel } from "../lib/api";

/** A soft rounded surface. `dark` renders the charcoal "focus" variant. */
export function Card({
  children,
  className = "",
  dark = false,
}: {
  children: ReactNode;
  className?: string;
  dark?: boolean;
}) {
  return (
    <div
      className={
        (dark
          ? "bg-ink text-ivory "
          : "bg-white/80 text-ink ") +
        "rounded-3xl shadow-card p-6 " +
        className
      }
    >
      {children}
    </div>
  );
}

export function SectionTitle({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div>
        <h2 className="text-xl font-bold">{title}</h2>
        {subtitle && <p className="text-sm text-ink/50 mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function RiskBadge({ level, large = false }: { level: RiskLevel; large?: boolean }) {
  return (
    <span
      className={
        "inline-flex items-center gap-1.5 font-semibold rounded-full " +
        (large ? "text-sm px-3.5 py-1.5" : "text-xs px-2.5 py-1")
      }
      style={{ backgroundColor: RISK_COLORS[level] + "22", color: RISK_COLORS[level] }}
    >
      <span
        className="rounded-full"
        style={{
          width: large ? 9 : 7,
          height: large ? 9 : 7,
          backgroundColor: RISK_COLORS[level],
        }}
      />
      {level}
    </span>
  );
}

export function Kpi({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: string;
}) {
  return (
    <div>
      <div className="text-sm text-ink/50 font-medium">{label}</div>
      <div className="text-5xl font-extrabold tabular mt-1" style={accent ? { color: accent } : {}}>
        {value}
      </div>
      {sub && <div className="text-sm text-ink/50 mt-1">{sub}</div>}
    </div>
  );
}

export function Loading() {
  return (
    <div className="flex items-center justify-center h-64 text-ink/40 text-sm">
      Loading…
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <Card className="border border-risk-severe/30">
      <div className="text-risk-severe font-semibold mb-1">Cannot reach the API</div>
      <p className="text-sm text-ink/60">{message}</p>
      <p className="text-sm text-ink/60 mt-2">
        Start the backend with <code className="bg-sand px-1.5 py-0.5 rounded">python api.py</code>{" "}
        in the <code className="bg-sand px-1.5 py-0.5 rounded">v2</code> folder (serves on port 5001).
      </p>
    </Card>
  );
}
