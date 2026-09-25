import { useEffect, useState } from "react";
import { api } from "../api";
import { useResult } from "../App";
import {
  CostCurve,
  DominanceCurve,
  EquityCurve,
  IsVsOos,
  LambdaHistogram,
  ScoreGauge,
  scoreColor,
} from "../components/widgets";

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="card !p-4">
      <div className="text-xs text-dim uppercase tracking-wide">{label}</div>
      <div className="stat-num mt-1">{value}</div>
      {hint && <div className="text-xs text-dim mt-1">{hint}</div>}
    </div>
  );
}

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

export default function Verdict() {
  const { programId, analysis, setResult } = useResult();
  const [loading, setLoading] = useState(false);
  const [pidInput, setPidInput] = useState("");

  useEffect(() => {
    if (!analysis && programId) {
      setLoading(true);
      api.analysis(programId)
        .then((a) => setResult(programId, a))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [analysis, programId, setResult]);

  if (!analysis) {
    return (
      <div className="card max-w-xl mx-auto text-center py-14">
        <h1 className="text-xl font-bold mb-2">No analysis loaded</h1>
        <p className="text-sm text-dim mb-6">
          Run a grid in the Strategy Lab, a one-click Strategy Zoo demo, or
          audit an uploaded returns CSV.
        </p>
        <div className="flex gap-2 max-w-sm mx-auto">
          <input
            className="input"
            placeholder="program id"
            value={pidInput}
            onChange={(e) => setPidInput(e.target.value)}
          />
          <button
            className="btn-ghost whitespace-nowrap"
            disabled={loading || !pidInput}
            onClick={() =>
              api.analysis(pidInput).then((a) => setResult(pidInput, a))
            }
          >
            Load
          </button>
        </div>
      </div>
    );
  }

  const a = analysis;
  const v = a.verdict;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-xl font-bold">Autopsy report</h1>
        <span className="text-xs text-dim font-mono">{programId}</span>
        <span className="text-xs text-dim">
          {a.n_trials} recorded trials · {a.n_days} days
          {a.declared_trials ? ` · ${a.declared_trials} declared` : ""}
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
        <div className="card flex flex-col items-center justify-center">
          <ScoreGauge score={v.score} label={v.label} />
          <p className="text-xs text-dim text-center mt-4 leading-relaxed">
            {v.label === "Mirage" &&
              "Likely overfit — the in-sample winner does not survive scrutiny."}
            {v.label === "Unclear" &&
              "Mixed evidence — inspect components before trusting this backtest."}
            {v.label === "Survives" &&
              "The best result holds up under the diagnostic battery."}
          </p>
        </div>
        <div className="card">
          <h2 className="font-bold mb-3">Component table</h2>
          <table className="data">
            <thead>
              <tr>
                <th>Component</th>
                <th>Weight</th>
                <th>Score</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {v.components.map((c) => (
                <tr key={c.key}>
                  <td className="font-medium">{c.label}</td>
                  <td>{(c.weight * 100).toFixed(0)}%</td>
                  <td className={scoreColor(c.score)}>{c.score.toFixed(0)}</td>
                  <td className="text-dim">{c.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2 className="font-bold mb-2">Plain-English read</h2>
        <ul className="list-disc list-inside space-y-1 text-sm text-gray-300">
          {v.narrative.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
        <p className="text-xs text-dim mt-3">
          Best trial: <span className="font-mono">{a.best_label}</span>
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Best IS Sharpe" value={a.best_sharpe.toFixed(2)}
          hint={`PSR (vs 0) = ${pct(a.psr)}`} />
        <Stat label="DSR p-value" value={pct(a.dsr)}
          hint={`E[max Sharpe | luck] = ${a.dsr_threshold.toFixed(2)}`} />
        <Stat label="PBO (CSCV)" value={pct(a.pbo)}
          hint={`${a.n_combinations.toLocaleString()} splits`} />
        <Stat label="P(OOS loss)" value={pct(a.p_oos_loss)}
          hint={a.reality_check_p != null ? `Reality Check p = ${a.reality_check_p.toFixed(2)}` : "no benchmark"} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card">
          <h2 className="font-bold mb-1">Equity curve — in-sample winner</h2>
          <p className="text-xs text-dim mb-3">net of costs, full sample</p>
          <EquityCurve dates={a.equity_curves.dates} best={a.equity_curves.best} />
        </div>
        <div className="card">
          <h2 className="font-bold mb-1">CSCV rank logits (λ)</h2>
          <p className="text-xs text-dim mb-3">
            λ &lt; 0 → IS winner below OOS median. PBO = share of red mass ={" "}
            {pct(a.pbo)}
          </p>
          <LambdaHistogram lambdas={a.cscv_lambdas} />
        </div>
        <div className="card">
          <h2 className="font-bold mb-1">In-sample vs out-of-sample Sharpe</h2>
          <p className="text-xs text-dim mb-3">
            one point per CSCV split · degradation slope {a.degradation_slope.toFixed(2)}
          </p>
          <IsVsOos isv={a.cscv_is_sharpes} oos={a.cscv_oos_sharpes} />
        </div>
        <div className="card">
          <h2 className="font-bold mb-1">Cost fragility</h2>
          <p className="text-xs text-dim mb-3">
            Sharpe vs transaction cost · breakeven{" "}
            {a.cost_curve.breakeven_bps.toFixed(0)} bps
          </p>
          <CostCurve
            costBps={a.cost_curve.cost_bps}
            sharpe={a.cost_curve.sharpe}
            breakeven={a.cost_curve.breakeven_bps}
            assumed={5}
          />
        </div>
        <div className="card">
          <h2 className="font-bold mb-1">Stochastic dominance</h2>
          <p className="text-xs text-dim mb-3">empirical CDF of λ across splits</p>
          <DominanceCurve
            lambda={a.cscv_dominance.lambda}
            cdf={a.cscv_dominance.cdf}
          />
        </div>
        <div className="card">
          <h2 className="font-bold mb-1">Min backtest length</h2>
          <p className="text-xs text-dim mb-3">Bailey &amp; López de Prado (2012)</p>
          <div className="stat-num">
            {Number.isFinite(a.min_btl) ? `${a.min_btl.toFixed(0)} days` : "���"}
          </div>
          <p className="text-xs text-dim mt-2">
            sample has {a.n_days.toLocaleString()} days
          </p>
          <h3 className="font-bold mt-5 mb-1 text-sm">Multiple-testing haircuts</h3>
          <table className="data">
            <tbody>
              {Object.entries(a.haircuts).map(([k, val]) => (
                <tr key={k}>
                  <td className="capitalize">{k}</td>
                  <td className="text-right">adj. p = {val.toExponential(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2 className="font-bold mb-2">All recorded trials</h2>
        <div className="max-h-80 overflow-auto">
          <table className="data">
            <thead className="sticky top-0 bg-panel">
              <tr>
                <th>#</th>
                <th>params</th>
                <th>Sharpe</th>
                <th>ann. ret</th>
                <th>max DD</th>
                <th>trades</th>
              </tr>
            </thead>
            <tbody>
              {[...a.trials]
                .sort((x, y) => (y.sharpe ?? 0) - (x.sharpe ?? 0))
                .map((t, i) => (
                  <tr key={i} className={t.label === a.best_label ? "text-accent" : ""}>
                    <td>{i + 1}</td>
                    <td className="font-mono text-xs">{JSON.stringify(t.params)}</td>
                    <td>{t.sharpe?.toFixed(2)}</td>
                    <td>{t.ann_return != null ? pct(t.ann_return) : "—"}</td>
                    <td>{t.max_drawdown != null ? pct(t.max_drawdown) : "—"}</td>
                    <td>{t.n_trades}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
