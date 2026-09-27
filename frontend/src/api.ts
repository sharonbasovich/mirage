import type {
  Analysis,
  Certificate,
  DemoInfo,
  LedgerEntryInfo,
  ProgramInfo,
  StrategyInfo,
  SymbolInfo,
} from "./types";

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const j = await r.json();
      detail = j.detail ?? detail;
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

export const api = {
  symbols: () => req<SymbolInfo[]>("/api/symbols"),
  strategies: () => req<StrategyInfo[]>("/api/strategies"),
  demos: () => req<DemoInfo[]>("/api/demos"),
  programs: () => req<ProgramInfo[]>("/api/programs"),
  run: (body: unknown) =>
    req<{ program_id: string; analysis: Analysis }>("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  runDemo: (key: string) =>
    req<{ program_id: string; analysis: Analysis }>(`/api/demo/${key}`, {
      method: "POST",
    }),
  analysis: (pid: string) => req<Analysis>(`/api/programs/${pid}/analysis`),
  trials: (pid: string) => req<LedgerEntryInfo[]>(`/api/programs/${pid}/trials`),
  certificate: (pid: string) => req<Certificate>(`/api/programs/${pid}/certificate`),
  ledgerVerify: () => req<{ valid: boolean; message: string }>("/api/ledger/verify"),
  audit: (
    file: File,
    nTrials: number,
    benchmark: string,
    costBps: number,
    frequency: "daily" | "monthly",
  ) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("n_trials", String(nTrials));
    fd.append("benchmark", benchmark);
    fd.append("cost_bps", String(costBps));
    fd.append("frequency", frequency);
    return req<{ program_id: string; analysis: Analysis }>("/api/audit", {
      method: "POST",
      body: fd,
    });
  },
};
