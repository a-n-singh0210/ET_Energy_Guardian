import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
  Legend,
} from "recharts";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, Loading, ErrorState, SectionTitle } from "../components/ui";
import { tooltipStyle } from "./Timeline";

const SIGNAL_COLORS: Record<string, string> = {
  anomaly_brent: "#2563EB",
  anomaly_freight: "#7C3AED",
  anomaly_events: "#E8730C",
};

export default function Signals() {
  const { data, error, loading } = useApi(api.signals);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "no data"} />;

  return (
    <div className="space-y-5">
      <Card>
        <SectionTitle
          title="Anomaly scores"
          subtitle="Robust z-scores over a 14-day window, clipped to [-3, 3] — computed in anomalies.py"
        />
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={data.anomalies} margin={{ left: -10, right: 10, top: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#00000010" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#1a1a1888" }} minTickGap={40} />
            <YAxis domain={[-3, 3]} tick={{ fontSize: 11, fill: "#1a1a1888" }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend />
            <ReferenceLine y={0} stroke="#00000030" />
            {Object.entries(SIGNAL_COLORS).map(([k, c]) => (
              <Line key={k} type="monotone" dataKey={k} stroke={c} strokeWidth={2} dot={false} connectNulls={false} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card>
          <SectionTitle title="Brent return & corridor pressure" subtitle="Underlying features" />
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data.features} margin={{ left: -10, right: 10, top: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#00000010" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#1a1a1888" }} minTickGap={50} />
              <YAxis tick={{ fontSize: 10, fill: "#1a1a1888" }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend />
              <Line type="monotone" dataKey="brent_return" stroke="#2563EB" dot={false} connectNulls={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="event_severity_14" stroke="#E8730C" dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <SectionTitle title="Freight rate (Drewry WCI)" subtitle="USD per 40ft, forward-filled between documented prints" />
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data.features} margin={{ left: 5, right: 10, top: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#00000010" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#1a1a1888" }} minTickGap={50} />
              <YAxis tick={{ fontSize: 10, fill: "#1a1a1888" }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="stepAfter" dataKey="freight_wci_ffill" stroke="#7C3AED" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}
