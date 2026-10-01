export interface SymbolInfo {
  symbol: string;
  rows: number;
  start: string;
  end: string;
  frequency: "daily" | "monthly";
  source: string;
  license: string;
}

export interface StrategyInfo {
  name: string;
  description: string;
  default_grid: Record<string, unknown[]>;
  default_symbols: string[];
}

export interface DemoInfo {
  key: string;
  title: string;
  family: string;
  symbols: string[];
  grid: Record<string, unknown[]>;
  cost_bps: number;
}

export interface TrialRow {
  label: string;
  entry_id: number;
  sharpe: number;
  ann_return: number;
  max_drawdown: number;
  n_trades: number;
  params: Record<string, unknown>;
}

export interface VerdictComponent {
  key: string;
  label: string;
  weight: number;
  score: number;
  detail: string;
}

export interface Analysis {
  n_trials: number;
  n_days: number;
  periods_per_year?: number;
  frequency?: "daily" | "monthly";
  best_index: number;
  best_label: string;
  best_config: Record<string, unknown>;
  best_metrics: Record<string, number>;
  best_sharpe: number;
  trial_sharpes: Record<string, number>;
  psr: number;
  dsr: number;
  dsr_threshold: number;
  min_btl: number;
  haircuts: Record<string, number>;
  pbo: number;
  p_oos_loss: number;
  degradation_slope: number;
  cscv_lambdas: number[];
  cscv_is_sharpes: number[];
  cscv_oos_sharpes: number[];
  cscv_dominance: { lambda: number[]; cdf: number[] };
  n_combinations: number;
  reality_check_p: number | null;
  reality_check_best: number | null;
  cost_curve: { cost_bps: number[]; sharpe: number[]; breakeven_bps: number; capped: boolean };
  verdict: {
    score: number;
    label: string;
    label_capped?: boolean;
    components: VerdictComponent[];
    narrative: string[];
  };
  equity_curves: { dates: string[]; best: number[] };
  trials: TrialRow[];
  declared_trials?: number;
  observed_trials?: number;
  frequency_verified?: boolean;
}

export interface ProgramInfo {
  program_id: string;
  n: number;
  first_ts: number;
  last_ts: number;
  has_analysis: boolean;
}

export interface LedgerEntryInfo {
  id: number;
  ts: number;
  label: string;
  config: Record<string, unknown>;
  metrics: Record<string, number>;
  config_hash: string;
  entry_hash: string;
  prev_hash: string;
  data_hash: string;
}

export interface Certificate {
  program_id: string;
  trial_count: number;
  chain_head: string;
  chain_valid: boolean;
  chain_message: string;
  best_trial: { label: string; metrics: Record<string, number> } | null;
  verdict: { score: number; label: string } | null;
  data_hash: string;
}
