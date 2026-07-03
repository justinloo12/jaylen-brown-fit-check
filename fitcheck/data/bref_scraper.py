"""Basketball-Reference scraping for the pieces nba_api doesn't expose:
contract (AAV / years) and Win Shares / VORP / BPM.

Be polite: BRef rate-limits aggressively (HTTP 429 with a cooldown). We cache
hard and sleep between requests. Several BRef tables are wrapped in HTML
comments; we un-comment the page before parsing.
"""
from __future__ import annotations

import io
import re
import time
from typing import Any

import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment

from fitcheck.config import CACHE_DIR

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_BASE = "https://www.basketball-reference.com"
_SLEEP = 3.5  # BRef asks for <= 20 req/min; stay well under.


def _slug(player_id_bref: str) -> str:
    return player_id_bref


def _fetch_html(url: str, *, cache_name: str, force: bool = False) -> str:
    path = CACHE_DIR / f"bref_{cache_name}.html"
    if path.exists() and not force:
        return path.read_text(encoding="utf-8")
    time.sleep(_SLEEP)
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    path.write_text(resp.text, encoding="utf-8")
    return resp.text


def _uncomment(html: str) -> str:
    """BRef hides many tables inside <!-- --> comments; surface them."""
    soup = BeautifulSoup(html, "lxml")
    for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
        c.replace_with(BeautifulSoup(c, "lxml"))
    return str(soup)


def _read_table(html: str, table_id: str) -> pd.DataFrame | None:
    soup = BeautifulSoup(html, "lxml")
    node = soup.find("table", id=table_id)
    if node is None:
        return None
    return pd.read_html(io.StringIO(str(node)))[0]


def player_advanced(player_slug: str, *, force: bool = False) -> pd.DataFrame:
    """Per-season Advanced table (contains WS, WS/48, BPM, VORP)."""
    url = f"{_BASE}/players/{player_slug[0]}/{player_slug}.html"
    html = _uncomment(_fetch_html(url, cache_name=f"{player_slug}_page", force=force))
    df = _read_table(html, "advanced")
    if df is None:
        raise ValueError(f"No advanced table found for {player_slug}")
    df = df[df["Season"].notna() & df["Season"].astype(str).str.contains("-")]
    df["player_slug"] = player_slug
    return df.reset_index(drop=True)


def future_contract(player_slug: str, *, force: bool = False) -> pd.DataFrame:
    """The wide 'contracts_<team>' table with future guaranteed years as columns.

    This is the one that reveals when a deal ends (and thus cap flexibility),
    distinct from the historical 'all_salaries' table.
    """
    url = f"{_BASE}/players/{player_slug[0]}/{player_slug}.html"
    html = _uncomment(_fetch_html(url, cache_name=f"{player_slug}_page", force=force))
    soup = BeautifulSoup(html, "lxml")
    for t in soup.find_all("table"):
        if t.get("id", "").startswith("contracts_"):
            df = pd.read_html(io.StringIO(str(t)))[0]
            df["player_slug"] = player_slug
            return df
    return pd.DataFrame()


def player_contract(player_slug: str, *, force: bool = False) -> pd.DataFrame:
    """Year-by-year contract table from the player page (salaries by season)."""
    url = f"{_BASE}/players/{player_slug[0]}/{player_slug}.html"
    html = _uncomment(_fetch_html(url, cache_name=f"{player_slug}_page", force=force))
    # BRef contract table id is "contracts_<team-abbr>" or "all_salaries".
    soup = BeautifulSoup(html, "lxml")
    node = None
    for t in soup.find_all("table"):
        tid = t.get("id", "")
        if tid.startswith("contracts_") or tid == "all_salaries":
            node = t
            break
    if node is None:
        return pd.DataFrame()
    df = pd.read_html(io.StringIO(str(node)))[0]
    df["player_slug"] = player_slug
    return df


# The contract-value comp set: display name -> BRef slug. Max/near-max
# perimeter players; Celtics teammates included for in-house context.
BREF_SLUGS: dict[str, str] = {
    "Jaylen Brown": "brownja02",
    "Jayson Tatum": "tatumja01",
    "Derrick White": "whitede01",
    "Jrue Holiday": "holidjr01",
    "Kristaps Porzingis": "porzikr01",
    "Paul George": "georgpa01",
    "Luka Doncic": "doncilu01",
    "Shai Gilgeous-Alexander": "gilgesh01",
    "Donovan Mitchell": "mitchdo01",
    "Kawhi Leonard": "leonaka01",
    "Pascal Siakam": "siakapa01",
    "Anthony Edwards": "edwaran01",
    "Giannis Antetokounmpo": "antetgi01",
    "De'Aaron Fox": "foxde01",
    "Ja Morant": "moranja01",
    "Zion Williamson": "willizi01",
    "Devin Booker": "bookede01",
    "Jimmy Butler": "butleji01",
    "OG Anunoby": "anunoog01",
    "Mikal Bridges": "bridgmi01",
}
