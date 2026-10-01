import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useResult } from "../App";
import type { SymbolInfo } from "../types";

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [nTrials, setNTrials] = useState(50);
  const [bench, setBench] = useState("");
  const [freq, setFreq] = useState<"daily" | "monthly">("daily");
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [cost, setCost] = useState(5);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const { setResult } = useResult();
  const nav = useNavigate();

  useEffect(() => {
    api.symbols().then(setSymbols).catch(() => {});
  }, []);
  const benchOptions = symbols.filter((s) => s.frequency === freq);

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await api.audit(file, nTrials, bench, cost, freq);
      setResult("audit", r.analysis);
      nav("/verdict");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const downloadSample = () => {
    const rows = ["Date,trial_0,trial_1,trial_2"];
    let d = new Date("2020-01-01").getTime();
    let seed = 42;
    const rand = () => {
      seed = (seed * 1103515245 + 12345) % 2147483648;
      return seed / 2147483648 - 0.5;
    };
    for (let i = 0; i < 500; i++) {
      d += 86400000;
      rows.push(
        `${new Date(d).toISOString().slice(0, 10)},${rand() / 50},${rand() / 50},${rand() / 50}`,
      );
    }
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "sample_returns.csv";
    a.click();
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="card">
        <h1 className="text-xl font-bold mb-1">Audit an external backtest</h1>
        <p className="text-sm text-dim mb-5">
          Built your strategy in another tool? Upload a CSV of daily or monthly returns —
          one column per tried configuration, decimal simple returns
          (0.01 = +1%), optional Date column — and declare how many total
          parameter combinations you searched. Mirage runs the same diagnostic
          battery and verdict. Unsupported inputs (blank cells, non-numeric
          columns, values |r| ≥ 1, near-constant or near-riskless columns,
          off-calendar dates) are refused with an explicit error rather than
          guessed at.
        </p>
        <div className="space-y-4">
          <div>
            <label className="label">Returns CSV (Date + one column per trial)</label>
            <input
              className="input file:mr-3 file:text-accent file:bg-transparent file:border-0"
              type="file"
              accept=".csv"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <button className="text-xs text-accent mt-1 hover:underline" onClick={downloadSample}>
              download a sample CSV
            </button>
          </div>
          <div className="grid sm:grid-cols-4 gap-4">
            <div>
              <label className="label">Declared # trials</label>
              <input
                className="input"
                type="number"
                min={1}
                max={100000}
                value={nTrials}
                onChange={(e) => setNTrials(+e.target.value)}
              />
            </div>
            <div>
              <label className="label">Frequency</label>
              <select
                className="input"
                value={freq}
                onChange={(e) => {
                  setFreq(e.target.value as "daily" | "monthly");
                  setBench("");
                }}
              >
                <option value="daily">daily</option>
                <option value="monthly">monthly</option>
              </select>
            </div>
            <div>
              <label className="label">Benchmark</label>
              <select className="input" value={bench} onChange={(e) => setBench(e.target.value)}>
                <option value="">(none)</option>
                {benchOptions.map((s) => (
                  <option key={s.symbol} value={s.symbol}>
                    {s.symbol}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Cost (bps)</label>
              <input
                className="input"
                type="number"
                value={cost}
                onChange={(e) => setCost(+e.target.value)}
              />
            </div>
          </div>
          <button className="btn" onClick={submit} disabled={!file || busy}>
            {busy ? "Auditing…" : "Audit this backtest"}
          </button>
          {err && <p className="text-bad text-sm">{err}</p>}
        </div>
      </div>
      <div className="card text-xs text-dim leading-relaxed">
        <span className="text-gray-300 font-semibold">Honesty note.</span> Mirage
        cannot verify the declared trial count for external uploads — the
        Deflated Sharpe Ratio rescales to whatever number you report. If you
        upload fewer columns than you declare, the luck threshold is
        extrapolated from the uploaded subset — trials you didn't upload were
        not seen — and because a subset can never certify unseen trials, such
        audits are capped at Unclear no matter how strong the numbers look.
        Without a Date column, the declared frequency can't be verified either.
        That is exactly why the Trial Ledger exists: inside Mirage,
        the count is the ledger's, not yours.
      </div>
    </div>
  );
}
