import { useMemo, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import worldData from "world-atlas/countries-110m.json";
import { api } from "../lib/api";
import { useApi } from "../lib/useApi";
import { Card, Loading, ErrorState, SectionTitle } from "../components/ui";

const W = 960;
const H = 520;

// Build the basemap once. Frame the Atlantic → Africa → Gulf → India region.
/* eslint-disable @typescript-eslint/no-explicit-any */
const topo: any = worldData;
const world: any = feature(topo, topo.objects.countries);
const BBOX: any = {
  type: "Polygon",
  coordinates: [[[-100, -40], [96, -40], [96, 56], [-100, 56], [-100, -40]]],
};

// Per-node label placement so labels don't collide near the Gulf / India.
const CP_LABEL: Record<string, { dx: number; dy: number; anchor: "start" | "end" }> = {
  hormuz: { dx: -6, dy: 16, anchor: "end" },
  bab_el_mandeb: { dx: -9, dy: 5, anchor: "end" },
  suez: { dx: -9, dy: -9, anchor: "end" },
  cape: { dx: 10, dy: 4, anchor: "start" },
};
const PORT_LABEL: Record<string, { dx: number; dy: number; anchor: "start" | "end" }> = {
  sikka: { dx: 10, dy: -6, anchor: "start" },
  paradip: { dx: 10, dy: 13, anchor: "start" },
};
const projection = geoMercator().fitExtent([[12, 12], [W - 12, H - 12]], BBOX);
const pathGen = geoPath(projection);
const countryPaths: string[] = world.features.map((f: any) => pathGen(f) || "");

const CORRIDOR_COLOR: Record<string, string> = {
  hormuz: "#E8730C",
  redsea: "#7C3AED",
  atlantic_cape: "#22A06B",
};

const PRESETS: { label: string; h: number; r: number; o: number }[] = [
  { label: "Calm baseline", h: 0, r: 0, o: 0 },
  { label: "Red Sea suspension", h: 0, r: 0.8, o: 0 },
  { label: "Hormuz major + OPEC+", h: 0.6, r: 0.3, o: 1 },
  { label: "Hormuz full closure", h: 1, r: 0.5, o: 0 },
];

function project(lat: number, lng: number): [number, number] {
  return (projection([lng, lat]) as [number, number]) ?? [0, 0];
}

export default function CorridorMap() {
  const ctx = useApi(api.indiaContext);
  const aisData = useApi(api.ais);
  const [preset, setPreset] = useState(2);
  const p = PRESETS[preset];
  const res = useApi(() => api.resilience(p.h, p.r, p.o), [preset]);
  const norm = (s: string) => s.toLowerCase().replace(/strait|canal|of|the/g, "").replace(/[^a-z]/g, "");
  const tankerByName: Record<string, number> = {};
  (aisData.data?.chokepoints ?? []).forEach((c) => { tankerByName[norm(c.name)] = c.vessel_tanker; });

  const geo = ctx.data?.geo;
  const disrupted = useMemo(() => new Set(res.data?.disrupted_corridors ?? []), [res.data]);
  const selectedSuppliers = useMemo(() => {
    const names = new Set(
      (res.data?.procurement.recommendations ?? [])
        .filter((r) => r.status === "selected")
        .map((r) => r.origin)
    );
    return names;
  }, [res.data]);

  if (ctx.loading) return <Loading />;
  if (ctx.error || !geo) return <ErrorState message={ctx.error ?? "no geo data"} />;

  return (
    <div className="space-y-5">
      <Card>
        <SectionTitle
          title="Corridor & rerouting map"
          subtitle="Supplier origins → chokepoints → India. Disrupted corridors turn red; active reroutes highlight green."
        />
        <div className="flex flex-wrap gap-2 mb-4">
          {PRESETS.map((pr, i) => (
            <button
              key={pr.label}
              onClick={() => setPreset(i)}
              className={
                "px-3.5 py-1.5 rounded-full text-sm font-semibold transition " +
                (i === preset ? "bg-ink text-ivory" : "bg-cream hover:bg-sand")
              }
            >
              {pr.label}
            </button>
          ))}
        </div>

        <div className="rounded-2xl overflow-hidden bg-[#EAF1F5]">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
            {/* landmasses */}
            {countryPaths.map((d, i) => (
              <path key={i} d={d} fill="#DDE6DC" stroke="#C4D2C6" strokeWidth={0.4} />
            ))}

            {/* routes */}
            {geo.routes.map((rt) => {
              const isDisrupted = disrupted.has(rt.corridor);
              const supplierName = geo.suppliers[rt.supplier]?.name ?? "";
              const isActive =
                rt.corridor === "atlantic_cape" &&
                [...selectedSuppliers].some((o) => supplierName.includes(o.split(" ")[0]));
              const pts = rt.points.map(([lat, lng]) => project(lat, lng));
              const dStr = pts.map((pt, i) => (i === 0 ? "M" : "L") + pt[0] + "," + pt[1]).join(" ");
              const color = isDisrupted ? "#DC3545" : isActive ? "#22A06B" : CORRIDOR_COLOR[rt.corridor];
              return (
                <path
                  key={rt.supplier}
                  d={dStr}
                  fill="none"
                  stroke={color}
                  strokeWidth={isDisrupted ? 2.4 : isActive ? 2.4 : 1}
                  strokeOpacity={isDisrupted || isActive ? 0.95 : 0.28}
                  strokeDasharray={isDisrupted ? "5 4" : undefined}
                />
              );
            })}

            {/* suppliers */}
            {Object.entries(geo.suppliers).map(([key, s]) => {
              const [x, y] = project(s.lat, s.lng);
              return (
                <g key={key}>
                  <circle cx={x} cy={y} r={4} fill={CORRIDOR_COLOR[s.corridor ?? ""] ?? "#888"} stroke="#fff" strokeWidth={1} />
                </g>
              );
            })}

            {/* chokepoints */}
            {Object.entries(geo.chokepoints).map(([key, c]) => {
              const [x, y] = project(c.lat, c.lng);
              const hit = disrupted.has(key === "bab_el_mandeb" || key === "suez" ? "redsea" : key);
              const lab = CP_LABEL[key] ?? { dx: 9, dy: 3, anchor: "start" as const };
              return (
                <g key={key}>
                  <rect x={x - 4} y={y - 4} width={8} height={8} transform={`rotate(45 ${x} ${y})`}
                    fill={hit ? "#DC3545" : "#1A1A18"} stroke="#fff" strokeWidth={1} />
                  <text x={x + lab.dx} y={y + lab.dy} fontSize={9.5} fontWeight={600}
                    textAnchor={lab.anchor} fill={hit ? "#B02533" : "#1a1a18"}
                    stroke="#EAF1F5" strokeWidth={3} paintOrder="stroke" strokeLinejoin="round">{c.name}</text>
                  {tankerByName[norm(c.name)] != null && (
                    <text x={x + lab.dx} y={y + lab.dy + 12} fontSize={8.5} fontWeight={700}
                      textAnchor={lab.anchor} fill="#7A5A00"
                      stroke="#EAF1F5" strokeWidth={2.6} paintOrder="stroke" strokeLinejoin="round">
                      {tankerByName[norm(c.name)].toLocaleString()} tankers/yr
                    </text>
                  )}
                </g>
              );
            })}

            {/* India ports */}
            {Object.entries(geo.india_ports).map(([key, port]) => {
              const [x, y] = project(port.lat, port.lng);
              const lab = PORT_LABEL[key] ?? { dx: 9, dy: 3, anchor: "start" as const };
              return (
                <g key={key}>
                  <circle cx={x} cy={y} r={5} fill="#F2C14E" stroke="#1A1A18" strokeWidth={1.5} />
                  <text x={x + lab.dx} y={y + lab.dy} fontSize={9.5} fontWeight={700}
                    textAnchor={lab.anchor} fill="#1a1a18"
                    stroke="#EAF1F5" strokeWidth={3} paintOrder="stroke" strokeLinejoin="round">{port.name}</text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* legend */}
        <div className="flex flex-wrap gap-4 mt-4 text-xs text-ink/60">
          <Legend color="#E8730C" label="Hormuz corridor" />
          <Legend color="#7C3AED" label="Red Sea corridor" />
          <Legend color="#22A06B" label="Atlantic / Cape (resilient)" />
          <Legend color="#DC3545" label="Disrupted" />
          <Legend color="#F2C14E" label="India port" />
        </div>
        <div className="text-xs text-ink/40 mt-2">
          Tanker transit counts are AIS-derived (IMF PortWatch). The Strait of Hormuz alone carries ~19,500 tanker transits/yr — the world's most oil-critical chokepoint.
        </div>
      </Card>

      {res.data && (
        <Card dark>
          <div className="text-gold text-sm font-semibold uppercase tracking-wide mb-1">Under this scenario</div>
          <p className="text-ivory/80 text-sm">
            {disrupted.size > 0
              ? `${[...disrupted].join(" + ")} disrupted → ${res.data.scenario.india_import_gap_mbd} mb/d at risk. `
              : "No corridor disrupted. "}
            Orchestrator reroutes to {selectedSuppliers.size} Atlantic/Cape source(s), first cargo in{" "}
            {res.data.procurement.first_cargo_eta_days ?? "—"} days at ~${res.data.procurement.blended_landed_usd}/bbl.
          </p>
        </Card>
      )}
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
