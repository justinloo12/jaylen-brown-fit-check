"""Thin, cached wrappers around nba_api (stats.nba.com).

Every public function returns a tidy pandas DataFrame and is cache-backed, so
re-running the pipeline is cheap and offline-friendly once data is pulled.

stats.nba.com blocks requests that don't look like a browser. nba_api ships the
right headers, but we also bump the timeout because the endpoint is slow.
"""
from __future__ import annotations

import time
from typing import Any

import pandas as pd

from fitcheck import config
from fitcheck.data.cache import cached_df

# nba_api imports are done lazily inside functions so the rest of the package
# (features, viz, models operating on cached parquet) works without it installed.

_TIMEOUT = 60


def _pace() -> None:
    time.sleep(config.REQUEST_SLEEP)


def _get(endpoint_cls, *, dataset_index: int = 0, **kwargs) -> pd.DataFrame:
    """Instantiate an nba_api endpoint and return one of its result frames."""
    _pace()
    ep = endpoint_cls(timeout=_TIMEOUT, **kwargs)
    frames = ep.get_data_frames()
    return frames[dataset_index]


# ---------------------------------------------------------------------------
# Shot-level data (Angle 1: shot profile fit)
# ---------------------------------------------------------------------------
def shot_chart(player_id: int, season: str, *, team_id: int = 0,
               force: bool = False) -> pd.DataFrame:
    """Every FGA with x/y location, distance, zone, and make/miss."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import shotchartdetail
        return _get(
            shotchartdetail.ShotChartDetail,
            team_id=team_id,
            player_id=player_id,
            season_nullable=season,
            season_type_all_star=config.SEASON_TYPE,
            context_measure_simple="FGA",
        )
    return cached_df("shot_chart", _fetch,
                     params={"player_id": player_id, "season": season},
                     force=force)


def player_tracking_shots(player_id: int, season: str, *, team_id: int = 0,
                          split: str = "general", force: bool = False) -> pd.DataFrame:
    """Tracking shot splits: shot clock, dribbles, touch time, defender distance.

    ``split`` selects which breakdown table nba_api returns:
    general | shotclock | dribble | touchtime | closestdef | closestdef10.
    """
    # PlayerDashPtShots result-set order: 0=Overall, 1=General, 2=ShotClock,
    # 3=Dribble, 4=ClosestDef, 5=ClosestDef10ft+, 6=TouchTime.
    dataset = {
        "general": 1, "shotclock": 2, "dribble": 3,
        "closestdef": 4, "closestdef10": 5, "touchtime": 6,
    }[split]

    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import playerdashptshots
        df = _get(
            playerdashptshots.PlayerDashPtShots,
            team_id=team_id,
            player_id=player_id,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
            dataset_index=dataset,
        )
        df["SPLIT"] = split
        return df
    return cached_df("player_track_shots", _fetch,
                     params={"player_id": player_id, "season": season, "split": split},
                     force=force)


def team_tracking_shots(team_id: int, season: str, *, split: str = "general",
                        force: bool = False) -> pd.DataFrame:
    """Team-level tracking shot splits (for the 'Celtics identity' baseline)."""
    # TeamDashPtShots has 6 result sets (no separate General frame like the
    # player endpoint): 0=Overall, 1=ShotClock, 2=Dribble, 3=ClosestDef,
    # 4=ClosestDef10ft+, 5=TouchTime.
    dataset = {
        "general": 0, "shotclock": 1, "dribble": 2,
        "closestdef": 3, "closestdef10": 4, "touchtime": 5,
    }[split]

    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import teamdashptshots
        df = _get(
            teamdashptshots.TeamDashPtShots,
            team_id=team_id,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
            dataset_index=dataset,
        )
        df["SPLIT"] = split
        return df
    return cached_df("team_track_shots", _fetch,
                     params={"team_id": team_id, "season": season, "split": split},
                     force=force)


# ---------------------------------------------------------------------------
# Team & league profile (assisted-3 rate, pace, 3PA rate)
# ---------------------------------------------------------------------------
def league_team_stats(season: str, *, measure: str = "Advanced",
                      force: bool = False) -> pd.DataFrame:
    """All 30 teams, one row each. measure=Base|Advanced|Four Factors|Scoring."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import leaguedashteamstats
        return _get(
            leaguedashteamstats.LeagueDashTeamStats,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
            measure_type_detailed_defense=measure,
            per_mode_detailed="PerGame",
        )
    return cached_df("league_team_stats", _fetch,
                     params={"season": season, "measure": measure}, force=force)


def league_player_stats(season: str, *, measure: str = "Advanced",
                        force: bool = False) -> pd.DataFrame:
    """League-wide player stats (Advanced gives NET_RATING, USG, TS%, etc.)."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import leaguedashplayerstats
        return _get(
            leaguedashplayerstats.LeagueDashPlayerStats,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
            measure_type_detailed_defense=measure,
            per_mode_detailed="PerGame",
        )
    return cached_df("league_player_stats", _fetch,
                     params={"season": season, "measure": measure}, force=force)


# ---------------------------------------------------------------------------
# On/off & lineups (Angle 2: winning basketball)
# ---------------------------------------------------------------------------
def team_on_off(team_id: int, season: str, *, measure: str = "Advanced",
                force: bool = False) -> pd.DataFrame:
    """Per-player on-court / off-court splits for a team (standard on/off)."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import teamplayeronoffdetails
        ep_kwargs = dict(
            team_id=team_id,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
            measure_type_detailed_defense=measure,
        )
        # dataset 1 = ON court, dataset 2 = OFF court; tag and stack them.
        from nba_api.stats.endpoints.teamplayeronoffdetails import TeamPlayerOnOffDetails
        _pace()
        ep = TeamPlayerOnOffDetails(timeout=_TIMEOUT, **ep_kwargs)
        on = ep.get_data_frames()[1].assign(COURT_STATUS="ON")
        off = ep.get_data_frames()[2].assign(COURT_STATUS="OFF")
        return pd.concat([on, off], ignore_index=True)
    return cached_df("team_on_off", _fetch,
                     params={"team_id": team_id, "season": season, "measure": measure},
                     force=force)


def team_lineups(team_id: int, season: str, *, group_quantity: int = 5,
                 force: bool = False) -> pd.DataFrame:
    """Lineup-level advanced stats. GROUP_ID encodes the player IDs in the unit,
    which lets us build with/without-teammate splits downstream."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import leaguedashlineups
        return _get(
            leaguedashlineups.LeagueDashLineups,
            team_id_nullable=team_id,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
            group_quantity=group_quantity,
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
        )
    return cached_df("team_lineups", _fetch,
                     params={"team_id": team_id, "season": season, "g": group_quantity},
                     force=force)


def player_clutch(season: str, *, measure: str = "Base",
                  force: bool = False) -> pd.DataFrame:
    """League clutch stats (last 5 min, margin <= 5). Filter to players of interest."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import leaguedashplayerclutch
        return _get(
            leaguedashplayerclutch.LeagueDashPlayerClutch,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
            measure_type_detailed_defense=measure,
            per_mode_detailed="Totals",
        )
    return cached_df("player_clutch", _fetch,
                     params={"season": season, "measure": measure}, force=force)


def player_stats_by_type(season: str, *, measure: str = "Base",
                         season_type: str = "Regular Season",
                         per_mode: str = "PerGame",
                         force: bool = False) -> pd.DataFrame:
    """League player stats for an arbitrary season type (e.g. 'Playoffs')."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import leaguedashplayerstats
        return _get(
            leaguedashplayerstats.LeagueDashPlayerStats,
            season=season,
            season_type_all_star=season_type,
            measure_type_detailed_defense=measure,
            per_mode_detailed=per_mode,
        )
    return cached_df("player_stats_by_type", _fetch,
                     params={"season": season, "measure": measure,
                             "st": season_type, "pm": per_mode}, force=force)


def player_gamelogs(player_id: int, season: str, *,
                    season_type: str = "Regular Season",
                    force: bool = False) -> pd.DataFrame:
    """Per-game logs (PTS, FGA, FTA, PLUS_MINUS, MATCHUP) for opponent-quality
    and streak analysis."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import playergamelogs
        return _get(
            playergamelogs.PlayerGameLogs,
            player_id_nullable=player_id,
            season_nullable=season,
            season_type_nullable=season_type,
        )
    return cached_df("player_gamelogs", _fetch,
                     params={"player_id": player_id, "season": season,
                             "st": season_type}, force=force)


def team_gamelogs(team_id: int, season: str, *,
                  season_type: str = "Regular Season",
                  force: bool = False) -> pd.DataFrame:
    """Per-game team box scores (W/L, PTS, FGA, FTA, OREB, TOV, PLUS_MINUS).

    Used to (a) join Tatum's game logs against team totals for the standard
    usage formula and (b) compute team record / per-game margin in
    games-with vs games-without splits."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import teamgamelogs
        return _get(
            teamgamelogs.TeamGameLogs,
            team_id_nullable=team_id,
            season_nullable=season,
            season_type_nullable=season_type,
        )
    return cached_df("team_gamelogs", _fetch,
                     params={"team_id": team_id, "season": season,
                             "st": season_type}, force=force)


def play_by_play(game_id: str, *, force: bool = False) -> pd.DataFrame:
    """Full PlayByPlayV3 event stream for one game (turnover classification,
    points-off-turnover walks). V2 no longer serves recent seasons. Heaviest
    pull in the project: one call per game — always cached, standard pacing
    applies."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import playbyplayv3
        df = _get(playbyplayv3.PlayByPlayV3, game_id=game_id)
        # Parquet chokes on mixed object columns; normalize the text ones.
        for c in ["scoreHome", "scoreAway", "description", "actionType",
                  "subType", "clock", "shotResult", "location"]:
            if c in df:
                df[c] = df[c].astype("string")
        return df
    return cached_df("play_by_play", _fetch, params={"game_id": game_id},
                     force=force)


def team_records(season: str, *, force: bool = False) -> pd.DataFrame:
    """Team W/L (to compute opponent win% for 'vs good teams' splits)."""
    def _fetch() -> pd.DataFrame:
        df = league_team_stats(season, measure="Base", force=force)
        return df[["TEAM_ID", "TEAM_NAME", "W", "L"]].copy()
    return cached_df("team_records", _fetch, params={"season": season}, force=force)


def league_player_tracking(season: str, *, pt_measure: str = "Possessions",
                           force: bool = False) -> pd.DataFrame:
    """League-wide SportVU tracking stats, one row per player.

    pt_measure: Possessions (touches, time of poss, sec/dribbles per touch),
    Passing (passes made/received, potential assists), Drives, CatchShoot, ...
    """
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import leaguedashptstats
        return _get(
            leaguedashptstats.LeagueDashPtStats,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
            pt_measure_type=pt_measure,
            player_or_team="Player",
            per_mode_simple="PerGame",
        )
    return cached_df("league_player_tracking", _fetch,
                     params={"season": season, "pt": pt_measure}, force=force)


def player_shot_defend(player_id: int, season: str, *, team_id: int = 0,
                       force: bool = False) -> pd.DataFrame:
    """Defended-shot tracking: FG% shooters post against this defender vs
    their normal FG%, by zone (PCT_PLUSMINUS < 0 = shooters do worse)."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import playerdashptshotdefend
        return _get(
            playerdashptshotdefend.PlayerDashPtShotDefend,
            player_id=player_id,
            team_id=team_id,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
        )
    return cached_df("player_shot_defend", _fetch,
                     params={"player_id": player_id, "season": season},
                     force=force)


def season_matchups(def_player_id: int, season: str, *,
                    force: bool = False) -> pd.DataFrame:
    """Season matchup totals with this player as the DEFENDER: one row per
    offensive player he guarded (partial possessions, points allowed,
    matchup FG%, matchup TOV) — the on-ball defense lens."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import leagueseasonmatchups
        return _get(
            leagueseasonmatchups.LeagueSeasonMatchups,
            def_player_id_nullable=def_player_id,
            season=season,
            season_type_playoffs=config.SEASON_TYPE,
        )
    return cached_df("season_matchups", _fetch,
                     params={"def_player_id": def_player_id, "season": season},
                     force=force)


def league_hustle(season: str, *, force: bool = False) -> pd.DataFrame:
    """League hustle tracking totals (deflections, loose balls, charges,
    contested shots, box-outs) — the off-ball activity lens."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import leaguehustlestatsplayer
        return _get(
            leaguehustlestatsplayer.LeagueHustleStatsPlayer,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
            per_mode_time="Totals",
        )
    return cached_df("league_hustle", _fetch, params={"season": season},
                     force=force)


def synergy_playtype(season: str, *, play_type: str, grouping: str = "defensive",
                     force: bool = False) -> pd.DataFrame:
    """Synergy play-type table (league-wide, player rows). Not all seasons /
    types are served — callers should catch exceptions and skip gracefully."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import synergyplaytypes
        return _get(
            synergyplaytypes.SynergyPlayTypes,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
            play_type_nullable=play_type,
            type_grouping_nullable=grouping,
            player_or_team_abbreviation="P",
            per_mode_simple="Totals",
        )
    return cached_df("synergy_playtype", _fetch,
                     params={"season": season, "pt": play_type, "g": grouping},
                     force=force)


def player_passing(player_id: int, season: str, *, team_id: int = 0,
                   force: bool = False) -> pd.DataFrame:
    """Passes made/received, touches, points created by assists — for
    'passes per touch' and playmaking-in-the-flow metrics."""
    def _fetch() -> pd.DataFrame:
        from nba_api.stats.endpoints import playerdashptpass
        return _get(
            playerdashptpass.PlayerDashPtPass,
            team_id=team_id,
            player_id=player_id,
            season=season,
            season_type_all_star=config.SEASON_TYPE,
        )
    return cached_df("player_passing", _fetch,
                     params={"player_id": player_id, "season": season}, force=force)
