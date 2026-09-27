import { useEffect, useState } from "react";
import { api } from "../api";
import { useResult } from "../App";
import type { Certificate, LedgerEntryInfo, ProgramInfo } from "../types";

export default function Ledger() {
  const [programs, setPrograms] = useState<ProgramInfo[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [entries, setEntries] = useState<LedgerEntryInfo[]>([]);
  const [cert, setCert] = useState<Certificate | null>(null);
  const [chain, setChain] = useState<{ valid: boolean; message: string } | null>(null);
  const { setResult } = useResult();

  useEffect(() => {
    api.programs().then(setPrograms).catch(() => {});
    api.ledgerVerify().then(setChain).catch(() => {});
  }, []);

  const pick = async (pid: string) => {
    setSelected(pid);
    setCert(null);
    const [es, c] = await Promise.all([api.trials(pid), api.certificate(pid)]);
    setEntries(es);
    setCert(c);
  };

  const loadAnalysis = async (pid: string) => {
    const a = await api.analysis(pid);
    setResult(pid, a);
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
      <aside className="space-y-4">
        <div className="card">
          <h1 className="text-xl font-bold mb-1">Trial Ledger</h1>
          <p className="text-xs text-dim mb-4">
            Every backtest run appends a hash-chained entry. Editing or deleting a
            row inside an intact ledger breaks the chain. The chain is not signed
            or externally anchored, so a full rewrite of the database cannot be
            detected. Publish a program's chain head to anchor it.
          </p>
          <div className={`text-xs px-3 py-2 rounded-lg border mb-4 ${
            chain?.valid ? "border-good/40 text-good" : "border-bad/40 text-bad"
          }`}>
            hash chain: {chain ? chain.message : "checking…"}
          </div>
          <div className="space-y-2 max-h-[520px] overflow-auto">
            {programs.map((p) => (
              <button
                key={p.program_id}
                onClick={() => pick(p.program_id)}
                className={`w-full text-left px-3 py-2.5 rounded-lg border transition-colors ${
                  selected === p.program_id
                    ? "border-accent bg-accent/10"
                    : "border-edge hover:border-accent/50"
                }`}
              >
                <div className="text-xs font-mono truncate">{p.program_id}</div>
                <div className="text-xs text-dim mt-0.5">
                  {p.n} trials · {new Date(p.last_ts * 1000).toLocaleDateString()}
                </div>
              </button>
            ))}
            {programs.length === 0 && (
              <p className="text-sm text-dim">No programs yet — run a grid in the Lab.</p>
            )}
          </div>
        </div>
      </aside>
      <section className="space-y-4">
        {!selected ? (
          <div className="card py-16 text-center text-dim">
            Select a research program to inspect its ledger entries.
          </div>
        ) : (
          <>
            {cert && (
              <div className="card">
                <h2 className="font-bold mb-2">Trial-ledger certificate (unsigned)</h2>
                <div className="grid sm:grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="label">trials recorded</div>
                    <div className="stat-num">{cert.trial_count}</div>
                  </div>
                  <div>
                    <div className="label">chain head</div>
                    <div className="font-mono text-xs break-all text-dim">
                      {cert.chain_head}
                    </div>
                  </div>
                  <div>
                    <div className="label">chain valid</div>
                    <div className={cert.chain_valid ? "text-good" : "text-bad"}>
                      {String(cert.chain_valid)} — {cert.chain_message}
                    </div>
                  </div>
                  <div>
                    <div className="label">data hash</div>
                    <div className="font-mono text-xs break-all text-dim">
                      {cert.data_hash}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  <button
                    className="btn-ghost text-xs"
                    onClick={() =>
                      navigator.clipboard.writeText(JSON.stringify(cert, null, 2))
                    }
                  >
                    copy certificate JSON
                  </button>
                  <button
                    className="btn-ghost text-xs"
                    onClick={() => loadAnalysis(selected)}
                  >
                    load analysis → Verdict
                  </button>
                </div>
              </div>
            )}
            <div className="card">
              <h2 className="font-bold mb-2">Ledger entries ({entries.length})</h2>
              <div className="max-h-[560px] overflow-auto">
                <table className="data">
                  <thead className="sticky top-0 bg-panel">
                    <tr>
                      <th>id</th>
                      <th>label</th>
                      <th>Sharpe</th>
                      <th>entry hash</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map((e) => (
                      <tr key={e.id}>
                        <td>{e.id}</td>
                        <td className="font-mono text-xs max-w-[280px] truncate">
                          {e.label}
                        </td>
                        <td>{e.metrics.sharpe?.toFixed(2)}</td>
                        <td className="font-mono text-[10px] text-dim max-w-[200px] truncate">
                          {e.entry_hash}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
