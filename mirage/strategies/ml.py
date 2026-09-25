"""ML strategy: predict next-day direction with purged walk-forward training.

Uses only scikit-learn; labels are sign(next-day return). Features are
computed strictly from past prices. Training uses expanding walk-forward
windows with an embargo - and the whole thing is exactly the kind of
predictive ML that overfits, which Mirage exists to catch.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from mirage.diagnostics.cv import walk_forward_splits
from mirage.strategies.base import Strategy, register, rsi

FEAT_NAMES = ["mom5", "mom10", "mom21", "vol21", "rsi14", "sma_ratio", "z21"]


def make_features(close: pd.Series) -> pd.DataFrame:
    r = close.pct_change()
    feats = pd.DataFrame(index=close.index)
    feats["mom5"] = close.pct_change(5)
    feats["mom10"] = close.pct_change(10)
    feats["mom21"] = close.pct_change(21)
    feats["vol21"] = r.rolling(21).std()
    feats["rsi14"] = rsi(close, 14) / 100.0
    sma = close.rolling(50).mean()
    feats["sma_ratio"] = close / sma - 1.0
    roll = close.rolling(21)
    feats["z21"] = (close - roll.mean()) / roll.std()
    return feats


def _make_model(params: dict):
    kind = params.get("model", "gbm")
    if kind == "logit":
        return LogisticRegression(C=float(params.get("C", 1.0)), max_iter=1000)
    if kind == "rf":
        return RandomForestClassifier(
            n_estimators=int(params.get("n_estimators", 100)),
            max_depth=int(params.get("max_depth", 4)),
            random_state=int(params.get("seed", 0)),
            n_jobs=1,
        )
    return GradientBoostingClassifier(
        n_estimators=int(params.get("n_estimators", 100)),
        max_depth=int(params.get("max_depth", 2)),
        learning_rate=float(params.get("learning_rate", 0.05)),
        random_state=int(params.get("seed", 0)),
    )


def ml_strategy(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Walk-forward ML classifier -> positions in {0, +1} or {-1, +1}."""
    close = prices.iloc[:, 0]
    r = close.pct_change()
    feats = make_features(close)
    y = (r.shift(-1) > 0).astype(float)

    train_window = int(params.get("train_window", 756))
    test_window = int(params.get("test_window", 63))
    embargo = int(params.get("embargo", 2))
    long_only = bool(params.get("long_only", True))
    thresh = float(params.get("thresh", 0.0))

    valid = feats.notna().all(axis=1) & y.notna()
    idx = np.where(valid.to_numpy())[0]

    sig = pd.Series(0.0, index=prices.index)
    model = _make_model(params)

    X = feats.to_numpy()
    yv = y.to_numpy()
    splits = walk_forward_splits(len(idx), train_window, test_window, embargo)
    for tr_i, te_i in splits:
        tr = idx[tr_i]
        te = idx[te_i]
        model.fit(X[tr], yv[tr])
        if hasattr(model, "predict_proba"):
            p = model.predict_proba(X[te])[:, 1]
            pred = np.where(p > 0.5 + thresh, 1.0, np.where(p < 0.5 - thresh, -1.0, 0.0))
        else:
            pred = np.where(model.predict(X[te]) > 0.5, 1.0, -1.0)
        if long_only:
            pred = np.clip(pred, 0.0, 1.0)
        sig.iloc[te] = pred
    return pd.DataFrame({prices.columns[0]: sig}, index=prices.index)


register(
    Strategy(
        name="ml_daily",
        description="Gradient-boosting / logistic classifier predicting next-day direction "
        "(purged walk-forward training)",
        position_fn=ml_strategy,
        default_grid={
            "model": ["gbm"],
            "n_estimators": [50, 100, 200],
            "max_depth": [2, 3],
            "learning_rate": [0.03, 0.05, 0.1],
            "embargo": [2],
            "train_window": [504, 756],
            "test_window": [63],
            "thresh": [0.0, 0.05],
            "long_only": [True],
        },
        default_symbols=["SPY"],
    )
)
