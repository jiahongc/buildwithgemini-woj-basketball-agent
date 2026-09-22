"""
Basketball Reference Web Scraper Data Provider.
Leverages `basketball_reference_web_scraper` to fetch deep historical box scores,
career totals, and advanced metrics (PER, BPM, VORP, WS/48, TS%, USG%).
Includes robust disk and in-memory caching to respect rate limits.
"""

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CACHE_DIR = os.environ.get("BBALL_CACHE_DIR", "/tmp/bball_ref_cache")
try:
    os.makedirs(CACHE_DIR, exist_ok=True)
except Exception:
    pass


class BasketballReferenceProvider:
    """Provider for Basketball Reference data via web scraper with persistent disk caching."""

    def __init__(self, cache_ttl_seconds: int = 86400 * 7):
        self.cache_ttl = cache_ttl_seconds
        self._memory_cache: Dict[str, Any] = {}

    def _get_cache_path(self, key: str) -> str:
        hashed = hashlib.md5(key.encode("utf-8")).hexdigest()
        return os.path.join(CACHE_DIR, f"{hashed}.json")

    def _read_cache(self, key: str) -> Optional[Any]:
        if key in self._memory_cache:
            return self._memory_cache[key]

        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                cached_time = payload.get("_cached_at", 0)
                # Historical seasons (>1 year old) never expire
                is_historical = payload.get("_historical", False)
                if is_historical or (time.time() - cached_time < self.cache_ttl):
                    data = payload.get("data")
                    self._memory_cache[key] = data
                    return data
            except Exception as e:
                logger.warning(f"Error reading cache for {key}: {e}")
        return None

    def _write_cache(self, key: str, data: Any, is_historical: bool = False):
        self._memory_cache[key] = data
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"_cached_at": time.time(), "_historical": is_historical, "data": data}, f)
        except Exception as e:
            logger.warning(f"Error writing cache for {key}: {e}")

    def search_player(self, term: str) -> List[Dict[str, Any]]:
        """Search for player by name to get slug/identifier."""
        cache_key = f"search_{term.lower().strip()}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        try:
            from basketball_reference_web_scraper import client

            raw = client.search(term=term)
            results = []
            for p in raw.get("players", []):
                results.append({
                    "id": p.get("identifier"),
                    "name": p.get("name"),
                    "slug": p.get("identifier"),
                    "source": "Basketball Reference",
                })
            self._write_cache(cache_key, results, is_historical=True)
            return results
        except Exception as e:
            logger.error(f"Error in bball ref search for '{term}': {e}")
            return []

    def get_player_advanced_season_totals(self, season_end_year: int) -> List[Dict[str, Any]]:
        """Get advanced season totals for all players in a season."""
        cache_key = f"adv_season_{season_end_year}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        try:
            from basketball_reference_web_scraper import client

            raw = client.players_advanced_season_totals(season_end_year=season_end_year)
            cleaned = []
            for item in raw:
                # Positions & teams are enums in basketball_reference_web_scraper
                pos_str = [p.name for p in item.get("positions", []) if hasattr(p, "name")]
                team_str = item.get("team").name if hasattr(item.get("team"), "name") else str(item.get("team"))
                cleaned.append({
                    "slug": item.get("slug"),
                    "name": item.get("name"),
                    "positions": pos_str,
                    "age": item.get("age"),
                    "team": team_str,
                    "games_played": item.get("games_played"),
                    "minutes_played": item.get("minutes_played"),
                    "per": item.get("player_efficiency_rating"),
                    "ts_pct": item.get("true_shooting_percentage"),
                    "three_par": item.get("three_point_attempt_rate"),
                    "ftr": item.get("free_throw_attempt_rate"),
                    "ast_pct": item.get("assist_percentage"),
                    "usg_pct": item.get("usage_percentage"),
                    "ows": item.get("offensive_win_shares"),
                    "dws": item.get("defensive_win_shares"),
                    "win_shares": item.get("win_shares"),
                    "ws_per_48": item.get("win_shares_per_48_minutes"),
                    "obpm": item.get("offensive_box_plus_minus"),
                    "dbpm": item.get("defensive_box_plus_minus"),
                    "bpm": item.get("box_plus_minus"),
                    "vorp": item.get("value_over_replacement_player"),
                    "source": "Basketball Reference",
                })
            # Seasons before current year are immutable historical data
            is_historical = season_end_year < 2026
            self._write_cache(cache_key, cleaned, is_historical=is_historical)
            return cleaned
        except Exception as e:
            logger.error(f"Error fetching advanced totals for {season_end_year}: {e}")
            return []

    def get_player_advanced_stats(self, slug_or_name: str, season_end_year: int) -> Optional[Dict[str, Any]]:
        """Retrieve advanced metrics for a specific player in a given season."""
        all_players = self.get_player_advanced_season_totals(season_end_year)
        target = slug_or_name.lower().strip()
        for p in all_players:
            if p.get("slug") == target or target in p.get("name", "").lower():
                return p
        return None

    def get_player_season_box_scores(
        self, player_slug: str, season_end_year: int, playoff: bool = False
    ) -> List[Dict[str, Any]]:
        """Fetch game-by-game box scores for a player in a season."""
        cache_key = f"boxscores_{player_slug}_{season_end_year}_{'playoff' if playoff else 'reg'}"
        cached = self._read_cache(cache_key)
        if cached is not None:
            return cached

        try:
            from basketball_reference_web_scraper import client

            if playoff:
                raw = client.playoff_player_box_scores(
                    player_identifier=player_slug, season_end_year=season_end_year
                )
            else:
                raw = client.regular_season_player_box_scores(
                    player_identifier=player_slug, season_end_year=season_end_year
                )

            games = []
            for g in raw:
                date_str = g.get("date").strftime("%Y-%m-%d") if hasattr(g.get("date"), "strftime") else str(g.get("date"))
                opp = g.get("opponent").name if hasattr(g.get("opponent"), "name") else str(g.get("opponent"))
                team = g.get("team").name if hasattr(g.get("team"), "name") else str(g.get("team"))
                outcome = g.get("outcome").name if hasattr(g.get("outcome"), "name") else str(g.get("outcome"))
                seconds = g.get("seconds_played", 0) or 0
                minutes = round(seconds / 60.0, 1)

                games.append({
                    "date": date_str,
                    "team": team,
                    "opponent": opp,
                    "outcome": outcome,
                    "minutes": minutes,
                    "pts": g.get("points_scored", 0),
                    "fgm": g.get("made_field_goals", 0),
                    "fga": g.get("attempted_field_goals", 0),
                    "tpm": g.get("made_three_point_field_goals", 0),
                    "tpa": g.get("attempted_three_point_field_goals", 0),
                    "ftm": g.get("made_free_throws", 0),
                    "fta": g.get("attempted_free_throws", 0),
                    "reb": (g.get("offensive_rebounds", 0) or 0) + (g.get("defensive_rebounds", 0) or 0),
                    "oreb": g.get("offensive_rebounds", 0),
                    "dreb": g.get("defensive_rebounds", 0),
                    "ast": g.get("assists", 0),
                    "stl": g.get("steals", 0),
                    "blk": g.get("blocks", 0),
                    "tov": g.get("turnovers", 0),
                    "pf": g.get("personal_fouls", 0),
                    "plus_minus": g.get("plus_minus", 0),
                    "game_score": g.get("game_score", 0.0),
                    "source": "Basketball Reference",
                })

            is_historical = season_end_year < 2026
            self._write_cache(cache_key, games, is_historical=is_historical)
            return games
        except Exception as e:
            logger.error(f"Error fetching box scores for {player_slug} in {season_end_year}: {e}")
            return []
