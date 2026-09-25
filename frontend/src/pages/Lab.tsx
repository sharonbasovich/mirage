import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useResult } from "../App";
import type { DemoInfo, StrategyInfo, SymbolInfo } from "../types";

export default function Lab() {
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [demos, setDemos] = useState<DemoInfo[]>([]);
  const [family, setFamily] = useState("ma_cross");
  const [picked, setPicked] = useState<string[]>(["SPY"]);
  const [gridText, setGridText] = useState("");
  const [cost, setCost] = useState(5);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const { setResult } = useResult();
  const nav = useNavigate();

  useEffect(() => {
    api.symbols().then(setSymbols).catch(() => {});
    api.strategies().then(setStrategies).catch(() => {});
    api.demos().then(setDemos).catch(() => {});
  }, []);

  useEffect(() => {
    const s = strategies.find((x) => x.name === family);
    if (s) {
      setPicked(s.default_symbols);
      setGridText(JSON.stringify(s.default_grid, null, 2));
    }
  }, [family, strategies]);

  const toggle = (s: string) =>
    setPicked((p) => (p.includes(s) ? p.filter((x) => x !== s) : [...p, s]));

  const run = async () => {
    setErr(null);
    setBusy("run");
    try {
      const grid = gridText.trim() ? JSON.parse(gridText) : null;
      const r = await api.run({
        family,
        symbols: picked,
        grid,
        cost_bps: cost,
      });
      setResult(r.program_id, r.analysis);
      nav("/verdict");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const runDemo = async (key: string) => {
    setErr(null);
    setBusy(key);
    try {
      const r = await api.runDemo(key);
      setResult(r.program_id, r.analysis);
      nav("/verdict");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <section className="space-y-6">
        <div className="card">
          <h1 className="text-xl font-bold mb-1">Strategy Lab</h1>
          <p className="text-sm text-dim mb-5">
            Pick a strategy family, a universe, and a parameter grid. Every trial
            is logged to the tamper-evident Trial Ledger — Mirage counts them all
            when judging your "best" result.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label">Strategy family</label>
              <select className="input" value={family}
                onChange={(e) => setFamily(e.target.value)}>
                {strategies.map((s) => (
                  <option key={s.name} value={s.name}>
                    {s.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-dim mt-1">
                {strategies.find((s) => s.name === family)?.description}
              </p>
            </div>
            <div>
              <label className="label">Transaction cost (bps / turnover)</label>
              <input className="input" type="number" value={cost}
                onChange={(e) => setCost(+e.target.value)} />
            </div>
          </div>
          <div className="mt-4">
            <label className="label">Universe (cached data)</label>
            <div className="flex flex-wrap gap-2">
              {symbols.map((s) => (
                <button
                  key={s.symbol}
                  onClick={() => toggle(s.symbol)}
                  className={`px-2.5 py-1 rounded-md text-xs border transition-colors ${
                    picked.includes(s.symbol)
                      ? "border-accent text-accent bg-accent/10"
                      : "border-edge text-dim hover:text-gray-300"
                  }`}
                  title={`${s.rows} rows ${s.start}→${s.end}`}
                >
                  {s.symbol}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-4">
            <label className="label">Parameter grid (JSON dict of lists)</label>
            <textarea
              className="input font-mono text-xs h-40"
              value={gridText}
              onChange={(e) => setGridText(e.target.value)}
              spellCheck={false}
            />
          </div>
          <div className="mt-5 flex items-center gap-3">
            <button className="btn" onClick={run}
              disabled={busy !== null || picked.length === 0}>
              {busy === "run" ? "Running trials…" : "Run grid + analyze"}
            </button>
            {busy === "run" && (
              <span className="text-xs text-dim">
                running backtests, CSCV over 12,870 splits, bootstrap…
              </span>
            )}
          </div>
          {err && <p className="text-bad text-sm mt-3">{err}</p>}
        </div>
      </section>
      <aside className="space-y-4">
        <div className="card">
          <h2 className="font-bold mb-1">Strategy Zoo</h2>
          <p className="text-xs text-dim mb-4">
            One-click demo programs — a ready-made tour of what Mirage does.
          </p>
          <div className="space-y-2">
            {demos.map((d) => (
              <button
                key={d.key}
                onClick={() => runDemo(d.key)}
                disabled={busy !== null}
                className="w-full text-left px-4 py-3 rounded-lg border border-edge
                  hover:border-accent transition-colors disabled:opacity-40"
              >
                <div className="text-sm font-semibold">{d.title}</div>
                <div className="text-xs text-dim mt-0.5">
                  {d.family} · {d.symbols.join(", ")} · cost {d.cost_bps}bps
                </div>
                {busy === d.key && (
                  <div className="text-xs text-accent mt-1">running…</div>
                )}
              </button>
            ))}
          </div>
        </div>
        <div className="card text-xs text-dim leading-relaxed">
          <span className="text-gray-300 font-semibold">Why the grid matters.</span>{" "}
          Trying 50 parameter combos and reporting the best is selection bias.
          Mirage records every trial in the ledger, so the diagnostics know the
          real search space — no forgotten experiments.
        </div>
      </aside>
    </div>
  );
}
