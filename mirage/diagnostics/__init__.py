"""Overfitting diagnostics from the academic literature.

Implemented in pure numpy/scipy:
- Sharpe, Probabilistic Sharpe Ratio (Bailey & Lopez de Prado 2012)
- Deflated Sharpe Ratio + Minimum Backtest Length (Bailey & Lopez de Prado 2014)
- Probability of Backtest Overfitting via CSCV (Bailey, Borwein,
  Lopez de Prado & Zhu 2017)
- Purged k-fold CV with embargo (Lopez de Prado 2018)
- Stationary-bootstrap Reality Check (White 2000; Politis & Romano 1994)
- Cost fragility and multiple-testing haircuts (Harvey & Liu 2015)
"""
