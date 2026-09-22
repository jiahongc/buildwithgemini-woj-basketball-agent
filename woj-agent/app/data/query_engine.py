"""
Advanced Basketball Statistical and Query Reasoning Engine.
Calculates derived metrics (TS%, eFG%, rTS%, AST/TO), computes custom window aggregations
(e.g., last 10 games, head-to-head vs opponent), and constructs era-aware player comparisons.
"""

from typing import Any, Dict, List, Optional
from app.data.historical_db import calculate_relative_ts, get_era_baseline


def calculate_ts_percentage(pts: float, fga: float, fta: float) -> float:
    """Calculate True Shooting Percentage (TS%). Formula: PTS / (2 * (FGA + 0.44 * FTA))."""
    denom = 2 * (fga + 0.44 * fta)
    if denom <= 0:
        return 0.0
    return round(pts / denom, 3)


def calculate_efg_percentage(fgm: float, three_pm: float, fga: float) -> float:
    """Calculate Effective Field Goal Percentage (eFG%). Formula: (FGM + 0.5 * 3PM) / FGA."""
    if fga <= 0:
        return 0.0
    return round((fgm + 0.5 * three_pm) / fga, 3)


def aggregate_game_logs(games: List[Dict[str, Any]], last_n: Optional[int] = None) -> Dict[str, Any]:
    """Aggregate a slice of game logs into per-game averages and efficiency metrics."""
    if not games:
        return {"games_count": 0, "pts": 0.0, "reb": 0.0, "ast": 0.0, "ts_pct": 0.0}

    selected = games[:last_n] if last_n else games
    total_games = len(selected)
    if total_games == 0:
        return {"games_count": 0}

    def _to_float(v: Any) -> float:
        try:
            return float(v)
        except (ValueError, TypeError):
            return 0.0

    total_pts = sum(_to_float(g.get("pts")) for g in selected)
    total_reb = sum(_to_float(g.get("reb")) for g in selected)
    total_ast = sum(_to_float(g.get("ast")) for g in selected)
    total_stl = sum(_to_float(g.get("stl", 0)) for g in selected)
    total_blk = sum(_to_float(g.get("blk", 0)) for g in selected)
    total_tov = sum(_to_float(g.get("tov") or g.get("to", 0)) for g in selected)
    total_min = sum(_to_float(g.get("minutes") or g.get("min", 0)) for g in selected)

    # Parse FG & FT attempts if available
    total_fga = 0.0
    total_fta = 0.0
    total_fgm = 0.0
    total_tpm = 0.0

    for g in selected:
        if "fga" in g:
            total_fga += _to_float(g.get("fga"))
            total_fgm += _to_float(g.get("fgm"))
            total_fta += _to_float(g.get("fta"))
            total_tpm += _to_float(g.get("tpm"))
        elif "fg" in g and "-" in str(g["fg"]):
            try:
                made, att = str(g["fg"]).split("-")
                total_fgm += float(made)
                total_fga += float(att)
            except Exception:
                pass
        if "ft" in g and "-" in str(g["ft"]):
            try:
                made, att = str(g["ft"]).split("-")
                total_fta += float(att)
            except Exception:
                pass
        if "three_pt" in g and "-" in str(g["three_pt"]):
            try:
                made, _ = str(g["three_pt"]).split("-")
                total_tpm += float(made)
            except Exception:
                pass

    ts = calculate_ts_percentage(total_pts, total_fga, total_fta) if total_fga > 0 else 0.0
    efg = calculate_efg_percentage(total_fgm, total_tpm, total_fga) if total_fga > 0 else 0.0

    wins = sum(1 for g in selected if str(g.get("result", "")).upper().startswith("W") or str(g.get("outcome", "")).upper() == "WIN")
    losses = total_games - wins

    return {
        "games_count": total_games,
        "record": f"{wins}-{losses}",
        "min_per_game": round(total_min / total_games, 1),
        "pts": round(total_pts / total_games, 1),
        "reb": round(total_reb / total_games, 1),
        "ast": round(total_ast / total_games, 1),
        "stl": round(total_stl / total_games, 1),
        "blk": round(total_blk / total_games, 1),
        "tov": round(total_tov / total_games, 1),
        "ast_to_tov": round(total_ast / max(total_tov, 1.0), 2),
        "ts_pct": ts,
        "efg_pct": efg,
        "games_detail": selected,
    }


def filter_games_by_opponent(games: List[Dict[str, Any]], opponent_query: str) -> List[Dict[str, Any]]:
    """Filter games played against a specific opponent (e.g., 'Boston' or 'Celtics')."""
    q = opponent_query.lower().strip()
    return [g for g in games if q in str(g.get("opponent", "")).lower()]


def build_player_comparison(
    p1_data: Dict[str, Any],
    p2_data: Dict[str, Any],
    p1_season: Optional[int] = None,
    p2_season: Optional[int] = None,
) -> Dict[str, Any]:
    """Generate side-by-side comparison with era context and delta flags."""
    year1 = p1_season or 2026
    year2 = p2_season or 2026

    base1 = get_era_baseline(year1)
    base2 = get_era_baseline(year2)

    ts1 = float(p1_data.get("ts_pct") or 0.550)
    ts2 = float(p2_data.get("ts_pct") or 0.550)

    rts1 = calculate_relative_ts(ts1, year1)
    rts2 = calculate_relative_ts(ts2, year2)

    return {
        "player1": {
            "name": p1_data.get("player") or p1_data.get("name"),
            "season": p1_data.get("season", f"{year1-1}-{str(year1)[-2:]}"),
            "pts": p1_data.get("pts"),
            "reb": p1_data.get("reb"),
            "ast": p1_data.get("ast"),
            "ts_pct": f"{ts1 * 100:.1f}%" if ts1 <= 1 else f"{ts1:.1f}%",
            "relative_ts": f"{rts1:+.1f}%",
            "bpm": p1_data.get("bpm"),
            "per": p1_data.get("per"),
            "vorp": p1_data.get("vorp"),
            "era_context": base1.get("era_label"),
            "source": p1_data.get("source", "Unified Provider"),
        },
        "player2": {
            "name": p2_data.get("player") or p2_data.get("name"),
            "season": p2_data.get("season", f"{year2-1}-{str(year2)[-2:]}"),
            "pts": p2_data.get("pts"),
            "reb": p2_data.get("reb"),
            "ast": p2_data.get("ast"),
            "ts_pct": f"{ts2 * 100:.1f}%" if ts2 <= 1 else f"{ts2:.1f}%",
            "relative_ts": f"{rts2:+.1f}%",
            "bpm": p2_data.get("bpm"),
            "per": p2_data.get("per"),
            "vorp": p2_data.get("vorp"),
            "era_context": base2.get("era_label"),
            "source": p2_data.get("source", "Unified Provider"),
        },
        "era_comparison": {
            "p1_era": f"{year1} (Lg TS%: {base1.get('lg_ts')*100:.1f}%, Pace: {base1.get('pace')})",
            "p2_era": f"{year2} (Lg TS%: {base2.get('lg_ts')*100:.1f}%, Pace: {base2.get('pace')})",
        },
    }
