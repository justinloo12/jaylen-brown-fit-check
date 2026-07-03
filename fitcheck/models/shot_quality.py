"""Predictive piece: model make-probability (a shot-quality proxy) from the
*context* of a shot — distance, defender distance, dribbles, touch time, clock.

We fit a logistic regression on shot-level features. The gap between a player's
actual FG% and the model's expected FG% given context = shot-making over/under
expectation; the model's predicted make-prob itself is an "expected quality"
score we can average per player to compare shot diets on a common scale.

If shot-level defender/clock data isn't available (ShotChartDetail lacks it),
we fall back to distance + zone, which still yields a useful xFG baseline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.model_selection import cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC = ["SHOT_DISTANCE"]
CATEGORICAL = ["SHOT_ZONE_BASIC", "SHOT_ZONE_AREA"]


def _feature_frame(shots: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    df = shots.copy()
    num = [c for c in NUMERIC if c in df]
    cat = [c for c in CATEGORICAL if c in df]
    # Optional richer context if a merged tracking frame provides it.
    for c in ["CLOSE_DEF_DIST", "DRIBBLES", "TOUCH_TIME", "SHOT_CLOCK"]:
        if c in df:
            num.append(c)
    return df, num, cat


def build_model(num: list[str], cat: list[str]) -> Pipeline:
    pre = ColumnTransformer([
        ("num", StandardScaler(), num),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat),
    ])
    return Pipeline([
        ("pre", pre),
        ("clf", LogisticRegression(max_iter=1000)),
    ])


def fit_expected_fg(shots: pd.DataFrame) -> tuple[Pipeline, pd.DataFrame, dict]:
    """Fit xFG model; return (model, shots-with-xFG, metrics).

    Adds an ``xFG`` column (cross-validated predicted make prob) so we don't
    score training rows with a model that saw them.
    """
    df, num, cat = _feature_frame(shots)
    if "SHOT_MADE_FLAG" not in df or df["SHOT_MADE_FLAG"].nunique() < 2:
        raise ValueError("Need SHOT_MADE_FLAG with both makes and misses.")

    X = df[num + cat]
    y = df["SHOT_MADE_FLAG"].astype(int)
    model = build_model(num, cat)

    proba = cross_val_predict(model, X, y, cv=5, method="predict_proba")[:, 1]
    df["xFG"] = proba
    model.fit(X, y)  # refit on all data for downstream scoring

    metrics = {
        "n": int(len(df)),
        "auc": float(roc_auc_score(y, proba)),
        "log_loss": float(log_loss(y, proba)),
        "actual_fg": float(y.mean()),
        "expected_fg": float(proba.mean()),
        "shot_making_over_expected": float(y.mean() - proba.mean()),
    }
    return model, df, metrics


def player_shot_quality(shots_with_xfg: pd.DataFrame) -> pd.Series:
    """Summarize a player's shot diet on the xFG scale (mean expected make%)."""
    return pd.Series({
        "mean_xFG": float(shots_with_xfg["xFG"].mean()),
        "actual_FG": float(shots_with_xfg["SHOT_MADE_FLAG"].mean()),
        "shot_making_over_expected": float(
            shots_with_xfg["SHOT_MADE_FLAG"].mean() - shots_with_xfg["xFG"].mean()
        ),
    })
