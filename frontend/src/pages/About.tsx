const METHODS = [
  {
    name: "Probabilistic Sharpe Ratio (PSR)",
    formula: "PSR(SR*) = Φ[(SR̂ − SR*)√(T−1) / √(1 − γ₃SR̂ + (γ₄−1)SR̂²/4)]",
    desc: "Probability that the true Sharpe exceeds a benchmark, with skewness (γ₃) and kurtosis (γ₄) corrections.",
    cite: "Bailey & López de Prado (2012), The Sharpe Ratio Efficient Frontier, J. of Risk 15(2).",
  },
  {
    name: "Deflated Sharpe Ratio (DSR)",
    formula: "DSR = PSR[E[max_N]·√V̂],  E[max_N] ≈ (1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne))",
    desc: "PSR where the benchmark is the Sharpe you would expect from the best of N lucky trials — the selection-bias haircut. N comes from the Trial Ledger, not your memory.",
    cite: "Bailey & López de Prado (2014), The Deflated Sharpe Ratio, J. of Portfolio Mgmt 40(5).",
  },
  {
    name: "Probability of Backtest Overfitting (PBO) via CSCV",
    formula: "λ = log(ω/(1−ω)),  PBO = P(λ < 0)",
    desc: "Split the sample into S=16 blocks; for every C(16,8)=12,870 choice of half as in-sample, rank configs by IS Sharpe, then locate the IS winner's normalized OOS rank ω. PBO is the share of splits where the IS winner lands below the OOS median.",
    cite: "Bailey, Borwein, López de Prado & Zhu (2017), The Probability of Backtest Overfitting, J. Comp. Finance.",
  },
  {
    name: "Purged k-fold CV + embargo",
    formula: "drop train i if [t₀ᵢ, t₁ᵢ] ∩ [a,b] ≠ ∅;  embargo (b, b+h]",
    desc: "For ML strategies, training samples whose labels overlap the test window are purged, and an embargo window follows each test fold — otherwise walk-forward results leak.",
    cite: "López de Prado (2018), Advances in Financial Machine Learning, ch. 7.",
  },
  {
    name: "Stationary-bootstrap Reality Check",
    formula: "p = #(max_k mean(d*_b − d̄) ≥ max_k mean(d)) / B",
    desc: "Politis–Romano stationary bootstrap (mean block 10) resamples days jointly across all N trials, preserving cross-correlation, to test whether the best strategy beats the benchmark beyond luck.",
    cite: "White (2000), A Reality Check for Data Snooping, Econometrica 68(5); Politis & Romano (1994).",
  },
  {
    name: "Cost fragility",
    formula: "Sharpe(c): net = gross − c·turnover/10⁴",
    desc: "Sweeps transaction cost to find the breakeven at which the edge disappears. An edge that dies at 8bps was never an edge.",
    cite: "Standard practice; see e.g. Harvey & Liu (2015) on realistic frictions.",
  },
  {
    name: "Multiple-testing haircuts",
    formula: "Bonferroni / Holm / BHY adjusted p-values",
    desc: "Adjusts the best trial's significance for the full set of recorded trials under family-wise error and FDR control.",
    cite: "Harvey & Liu (2015), Backtesting, J. of Portfolio Mgmt 42(1).",
  },
  {
    name: "Minimum Backtest Length",
    formula: "MinBTL = 1 + (1 − γ₃SR̂ + (γ₄−1)SR̂²/4)·(zα/(SR̂−SR*))²",
    desc: "How long a track record the claimed Sharpe needs to be significant at the chosen confidence.",
    cite: "Bailey & López de Prado (2012).",
  },
];

export default function About() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="card">
        <h1 className="text-xl font-bold mb-2">Why Mirage exists</h1>
        <p className="text-sm text-gray-300 leading-relaxed">
          Anyone can find a parameter combination with a great backtest. With
          enough tries, luck guarantees it. Clinical trials solved this problem
          with pre-registration and multiple-testing corrections; quant research
          mostly has not. Mirage records <em>every</em> trial in a tamper-evident
          ledger, then asks the question that matters:{" "}
          <em>would the best of what you tried still look good if you hadn't
          cherry-picked it?</em>
        </p>
      </div>
      {METHODS.map((m) => (
        <div className="card" key={m.name}>
          <h2 className="font-bold">{m.name}</h2>
          <code className="block text-xs text-accent bg-ink rounded-lg px-3 py-2 mt-2 overflow-x-auto">
            {m.formula}
          </code>
          <p className="text-sm text-gray-300 mt-2">{m.desc}</p>
          <p className="text-xs text-dim mt-1">{m.cite}</p>
        </div>
      ))}
      <div className="card">
        <h2 className="font-bold mb-2">Backtester convention</h2>
        <p className="text-sm text-gray-300">
          Signals computed from data through close of day t become positions at
          t+1 (strict no-lookahead). Costs are charged per unit of one-way
          turnover. The optional volatility target uses only trailing realized
          vol.
        </p>
      </div>
      <div className="card">
        <h2 className="font-bold mb-2">Mirage Score</h2>
        <p className="text-sm text-gray-300">
          0–100 weighted composite of: DSR p-value (25%), 1−PBO (25%), IS-vs-OOS
          Sharpe retention (20%), cost breakeven (15%), sample length vs MinBTL
          (15%). Labels: ≥65 <span className="text-good">Survives</span>, 40–65{" "}
          <span className="text-warn">Unclear</span>, &lt;40{" "}
          <span className="text-bad">Mirage</span> (likely overfit). The full
          component table is always shown — the score is transparent, not a
          black box.
        </p>
      </div>
      <div className="card text-xs text-dim leading-relaxed">
        <p>
          <span className="text-gray-300 font-semibold">Data.</span> Daily OHLCV
          for SPY, QQQ, IWM, TLT, GLD, 11 SPDR sector ETFs, BTC-USD, ETH-USD via
          Yahoo Finance (yfinance), cached in the repo; historical simulation
          only. This is a research prototype built for GIBC V2 — not a product,
          not a financial service, not financial advice.
        </p>
      </div>
    </div>
  );
}
