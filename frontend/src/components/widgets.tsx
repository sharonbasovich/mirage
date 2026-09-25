import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function scoreColor(score: number): string {
  if (score >= 65) return "text-good";
  if (score >= 40) return "text-warn";
  return "text-bad";
}
export function scoreHex(score: number): string {
  if (score >= 65) return "#34d399";
  if (score >= 40) return "#fbbf24";
  return "#f87171";
}

export function ScoreGauge({ score, label }: { score: number; label: string }) {
  const pct = Math.min(100, Math.max(0, score));
  return (
    <div className="flex flex-col items-center">
      <div className="relative w-40 h-20 overflow-hidden">
        <div className="absolute inset-0 rounded-t-full bg-edge" />
        <div
          className="absolute inset-0 rounded-t-full origin-bottom transition-transform"
          style={{
            background: `conic-gradient(from 270deg, ${scoreHex(score)} ${pct * 1.8}deg, transparent 0deg)`,
          }}
        />
        <div className="absolute inset-2 rounded-t-full bg-panel" />
        <div className={`absolute bottom-0 w-full text-center text-3xl font-bold ${scoreColor(score)}`}>
          {score.toFixed(0)}
        </div>
      </div>
      <div className={`mt-2 text-lg font-semibold ${scoreColor(score)}`}>{label}</div>
      <div className="text-xs text-dim">Mirage Score / 100</div>
    </div>
  );
}

const TIP = {
  contentStyle: { background: "#111827", border: "1px solid #1f2937", borderRadius: 8 },
  labelStyle: { color: "#9ca3af" },
};

export function LambdaHistogram({ lambdas }: { lambdas: number[] }) {
  const bins: Record<number, number> = {};
  for (const l of lambdas) {
    const b = Math.round(l * 2) / 2;
    bins[b] = (bins[b] ?? 0) + 1;
  }
  const data = Object.entries(bins)
    .map(([x, y]) => ({ x: +x, count: y }))
    .sort((a, b) => a.x - b.x);
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data}>
        <CartesianGrid stroke="#1f2937" vertical={false} />
        <XAxis dataKey="x" stroke="#9ca3af" fontSize={11} />
        <YAxis stroke="#9ca3af" fontSize={11} />
        <Tooltip {...TIP} />
        <ReferenceLine x={0} stroke="#f87171" strokeWidth={2} />
        <Bar dataKey="count" radius={[3, 3, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.x} fill={d.x < 0 ? "#f87171" : "#38bdf8"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function IsVsOos({ isv, oos }: { isv: number[]; oos: number[] }) {
  const data = isv.map((x, i) => ({ is: x, oos: oos[i] }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <ScatterChart>
        <CartesianGrid stroke="#1f2937" />
        <XAxis dataKey="is" name="IS Sharpe" stroke="#9ca3af" fontSize={11}
          label={{ value: "IS Sharpe", position: "insideBottom", offset: -2, fill: "#9ca3af" }} />
        <YAxis dataKey="oos" name="OOS Sharpe" stroke="#9ca3af" fontSize={11}
          label={{ value: "OOS Sharpe", angle: -90, position: "insideLeft", fill: "#9ca3af" }} />
        <Tooltip {...TIP} cursor={{ strokeDasharray: "3 3" }} />
        <ReferenceLine y={0} stroke="#f87171" />
        <Scatter data={data} fill="#38bdf8" fillOpacity={0.6} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export function CostCurve({
  costBps,
  sharpe,
  breakeven,
  assumed,
}: {
  costBps: number[];
  sharpe: number[];
  breakeven: number;
  assumed: number;
}) {
  const data = costBps.map((c, i) => ({ cost: c, sharpe: sharpe[i] }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data}>
        <CartesianGrid stroke="#1f2937" />
        <XAxis dataKey="cost" stroke="#9ca3af" fontSize={11}
          label={{ value: "cost (bps)", position: "insideBottom", offset: -2, fill: "#9ca3af" }} />
        <YAxis stroke="#9ca3af" fontSize={11} />
        <Tooltip {...TIP} />
        <ReferenceLine y={0} stroke="#f87171" />
        <ReferenceLine x={assumed} stroke="#fbbf24" strokeDasharray="4 4"
          label={{ value: "assumed", fill: "#fbbf24", fontSize: 10 }} />
        <ReferenceLine x={breakeven} stroke="#f87171" strokeDasharray="4 4"
          label={{ value: `breakeven ${breakeven.toFixed(0)}bps`, fill: "#f87171", fontSize: 10 }} />
        <Line type="monotone" dataKey="sharpe" stroke="#38bdf8" dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function EquityCurve({ dates, best }: { dates: string[]; best: number[] }) {
  const step = Math.max(1, Math.floor(dates.length / 300));
  const data = dates
    .map((d, i) => ({ d: d.slice(0, 7), v: best[i] }))
    .filter((_, i) => i % step === 0);
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data}>
        <CartesianGrid stroke="#1f2937" />
        <XAxis dataKey="d" stroke="#9ca3af" fontSize={11} minTickGap={40} />
        <YAxis stroke="#9ca3af" fontSize={11} domain={["auto", "auto"]} />
        <Tooltip {...TIP} />
        <Line type="monotone" dataKey="v" stroke="#38bdf8" dot={false} strokeWidth={1.5} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function DominanceCurve({ lambda, cdf }: { lambda: number[]; cdf: number[] }) {
  const step = Math.max(1, Math.floor(lambda.length / 400));
  const data = lambda
    .map((x, i) => ({ x, cdf: cdf[i] }))
    .filter((_, i) => i % step === 0);
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data}>
        <CartesianGrid stroke="#1f2937" />
        <XAxis dataKey="x" stroke="#9ca3af" fontSize={11}
          label={{ value: "λ (OOS rank logit)", position: "insideBottom", offset: -2, fill: "#9ca3af" }} />
        <YAxis stroke="#9ca3af" fontSize={11} domain={[0, 1]} />
        <Tooltip {...TIP} />
        <ReferenceLine x={0} stroke="#f87171" />
        <Line type="monotone" dataKey="cdf" stroke="#a78bfa" dot={false} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function SharpeHistogram({ sharpes }: { sharpes: number[] }) {
  const bins: Record<number, number> = {};
  const lo = Math.min(...sharpes);
  const hi = Math.max(...sharpes);
  const w = Math.max((hi - lo) / 20, 0.01);
  for (const s of sharpes) {
    const b = Math.round(s / w) * w;
    bins[+b.toFixed(3)] = (bins[+b.toFixed(3)] ?? 0) + 1;
  }
  const data = Object.entries(bins)
    .map(([x, y]) => ({ x: +x, count: y }))
    .sort((a, b) => a.x - b.x);
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data}>
        <CartesianGrid stroke="#1f2937" vertical={false} />
        <XAxis dataKey="x" stroke="#9ca3af" fontSize={11} />
        <YAxis stroke="#9ca3af" fontSize={11} />
        <Tooltip {...TIP} />
        <Bar dataKey="count" fill="#38bdf8" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
