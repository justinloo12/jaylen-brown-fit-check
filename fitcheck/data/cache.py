"""Disk cache so we never hammer stats.nba.com twice for the same pull.

DataFrames are stored as Parquet; anything else as JSON. Cache keys are derived
from a logical name plus the call's keyword arguments, so
``celtics_lineups(season="2024-25")`` and ``season="2025-26"`` are distinct files.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from fitcheck.config import CACHE_DIR


def _key(name: str, params: dict[str, Any]) -> str:
    blob = json.dumps(params, sort_keys=True, default=str)
    digest = hashlib.md5(blob.encode()).hexdigest()[:10]
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    return f"{safe}__{digest}"


def cached_df(
    name: str,
    fetch: Callable[[], pd.DataFrame],
    *,
    params: dict[str, Any] | None = None,
    ttl_days: float | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """Return a cached DataFrame, fetching + persisting on a miss.

    Parameters
    ----------
    name : logical name of the pull (becomes the filename stem).
    fetch : zero-arg callable that returns the DataFrame on a cache miss.
    params : call parameters, folded into the cache key.
    ttl_days : if set, cache older than this is treated as stale.
    force : ignore any existing cache and refetch.
    """
    params = params or {}
    path = CACHE_DIR / f"{_key(name, params)}.parquet"

    if path.exists() and not force:
        fresh = True
        if ttl_days is not None:
            age_days = (time.time() - path.stat().st_mtime) / 86_400
            fresh = age_days <= ttl_days
        if fresh:
            return pd.read_parquet(path)

    df = fetch()
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"fetch for {name!r} returned {type(df)}, expected DataFrame")
    # Parquet dislikes object columns of mixed types; stringify them defensively.
    df.to_parquet(path, index=False)
    return df


def cache_path(name: str, params: dict[str, Any] | None = None) -> Path:
    """Expose the on-disk path for a given logical pull (for inspection)."""
    return CACHE_DIR / f"{_key(name, params or {})}.parquet"
