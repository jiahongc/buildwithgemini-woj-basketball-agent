"""
Live ESPN NBA Data Provider.
Fetches real-time scores, active schedules, team rosters, current game logs,
and player career statistics with sub-second response times.
"""

import json
import logging
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


class EspnLiveProvider:
    """Fast, reliable provider for live NBA data via ESPN public REST APIs."""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def _get_json(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.warning(f"Error requesting ESPN endpoint {url}: {e}")
            return None

    def search_player(self, name: str) -> List[Dict[str, Any]]:
        """Search for an athlete to retrieve ESPN athlete ID."""
        encoded = urllib.parse.quote(name)
        url = f"https://site.web.api.espn.com/apis/search/v2?query={encoded}&limit=5"
        data = self._get_json(url)
        if not data:
            return []

        results = []
        for item in data.get("results", []):
            if item.get("displayName") == "Players":
                for c in item.get("contents", []):
                    # UID format is usually s:40~l:46~a:12345
                    raw_id = c.get("uid", "").split(":")[-1] if "a:" in c.get("uid", "") else c.get("id")
                    results.append({
                        "id": str(raw_id),
                        "name": c.get("displayName"),
                        "team": c.get("subtitle", "NBA"),
                        "image_url": c.get("image", {}).get("default"),
                        "link": c.get("link", {}).get("web"),
                        "source": "ESPN",
                    })
        if not results:
            from nba_api.stats.static import players as static_players
            matches = static_players.find_players_by_full_name(name)
            for mp in matches[:5]:
                results.append({
                    "id": str(mp["id"]),
                    "name": mp["full_name"],
                    "team": "NBA",
                    "source": "NBA Official Database",
                })
        return results

    def get_live_scoreboard(self) -> List[Dict[str, Any]]:
        """Fetch today's games, live scores, and game statuses."""
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        data = self._get_json(url)
        if not data or "events" not in data:
            return []

        games = []
        for ev in data.get("events", []):
            status = ev.get("status", {}).get("type", {}).get("description", "Scheduled")
            competitions = ev.get("competitions", [{}])[0]
            competitors = competitions.get("competitors", [])

            home_team, away_team = None, None
            for comp in competitors:
                team_info = {
                    "id": comp.get("id"),
                    "name": comp.get("team", {}).get("displayName"),
                    "abbreviation": comp.get("team", {}).get("abbreviation"),
                    "logo": comp.get("team", {}).get("logo"),
                    "score": comp.get("score"),
                    "record": comp.get("records", [{}])[0].get("summary", "") if comp.get("records") else "",
                }
                if comp.get("homeAway") == "home":
                    home_team = team_info
                else:
                    away_team = team_info

            games.append({
                "game_id": ev.get("id"),
                "date": ev.get("date"),
                "status": status,
                "short_name": ev.get("shortName"),
                "home_team": home_team,
                "away_team": away_team,
                "source": "ESPN",
            })
        return games

    def get_teams(self) -> List[Dict[str, Any]]:
        """Fetch all 30 NBA teams with metadata, falling back to static database if remote is unavailable."""
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"
        data = self._get_json(url)
        if data:
            teams = []
            for entry in data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []):
                t = entry.get("team", {})
                teams.append({
                    "id": t.get("id"),
                    "name": t.get("displayName"),
                    "abbreviation": t.get("abbreviation"),
                    "city": t.get("location"),
                    "color": t.get("color"),
                    "logo": t.get("logos", [{}])[0].get("href") if t.get("logos") else None,
                    "standing_summary": t.get("standingSummary", ""),
                    "source": "ESPN",
                })
            if teams:
                return teams

        # Fallback to local static NBA data
        from nba_api.stats.static import teams as static_teams
        return [
            {
                "id": str(t["id"]),
                "name": t["full_name"],
                "abbreviation": t["abbreviation"],
                "city": t["city"],
                "color": "000000",
                "logo": f"https://cdn.nba.com/logos/nba/{t['id']}/global/L/logo.svg",
                "standing_summary": "Active NBA Franchise",
                "source": "NBA Official Database",
            }
            for t in static_teams.get_teams()
        ]

    def get_team_roster(self, team_id: str) -> List[Dict[str, Any]]:
        """Fetch current roster for a team."""
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster"
        data = self._get_json(url)
        if not data:
            return []

        roster = []
        for athlete in data.get("athletes", []):
            roster.append({
                "id": athlete.get("id"),
                "name": athlete.get("fullName"),
                "position": athlete.get("position", {}).get("name") if isinstance(athlete.get("position"), dict) else athlete.get("position"),
                "jersey": athlete.get("jersey"),
                "height": athlete.get("displayHeight"),
                "weight": athlete.get("displayWeight"),
                "headshot": athlete.get("headshot", {}).get("href") if isinstance(athlete.get("headshot"), dict) else None,
                "source": "ESPN",
            })
        return roster

    def get_athlete_gamelog(self, athlete_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Fetch recent game logs for an athlete."""
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{athlete_id}/gamelog"
        data = self._get_json(url)
        if not data:
            return []

        events_map = data.get("events", {})
        season_types = data.get("seasonTypes", [])
        logs = []

        # Find regular season category
        for st in season_types:
            for cat in st.get("categories", []):
                for item in cat.get("events", []):
                    event_id = item.get("eventId")
                    ev_info = events_map.get(event_id, {})
                    raw_stats = item.get("stats", [])
                    # Labels: ['MIN', 'FG', 'FG%', '3PT', '3P%', 'FT', 'FT%', 'REB', 'AST', 'BLK', 'STL', 'PF', 'TO', 'PTS']
                    if len(raw_stats) >= 14:
                        opp_info = ev_info.get("opponent", {})
                        logs.append({
                            "event_id": event_id,
                            "date": ev_info.get("gameDate", "")[:10],
                            "opponent": opp_info.get("displayName") or opp_info.get("abbreviation", "Opponent"),
                            "result": ev_info.get("gameResult"),
                            "score": ev_info.get("score"),
                            "min": raw_stats[0],
                            "fg": raw_stats[1],
                            "fg_pct": raw_stats[2],
                            "three_pt": raw_stats[3],
                            "three_pct": raw_stats[4],
                            "ft": raw_stats[5],
                            "ft_pct": raw_stats[6],
                            "reb": raw_stats[7],
                            "ast": raw_stats[8],
                            "blk": raw_stats[9],
                            "stl": raw_stats[10],
                            "pf": raw_stats[11],
                            "to": raw_stats[12],
                            "pts": raw_stats[13],
                            "source": "ESPN",
                        })
                    if len(logs) >= limit:
                        return logs
        return logs

    def get_athlete_career_stats(self, athlete_id: str, playoff: bool = False) -> List[Dict[str, Any]]:
        """Fetch year-by-year regular season or postseason stats for an athlete."""
        seasontype = "3" if playoff else "2"
        url = f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/{athlete_id}/stats?seasontype={seasontype}"
        data = self._get_json(url)
        if not data or "categories" not in data:
            return []

        seasons = []
        # First category is usually 'averages' (Regular Season Averages)
        for cat in data.get("categories", []):
            if "averages" in cat.get("name", "").lower():
                for stat_entry in cat.get("statistics", []):
                    season_name = stat_entry.get("season", {}).get("displayName", "")
                    team_name = stat_entry.get("team", {}).get("displayName", "Total")
                    raw = stat_entry.get("stats", [])
                    # Labels: ['GP', 'GS', 'MIN', 'FG', 'FG%', '3PT', '3P%', 'FT', 'FT%', 'OR', 'DR', 'REB', 'AST', 'BLK', 'STL', 'PF', 'TO', 'PTS']
                    if len(raw) >= 18:
                        seasons.append({
                            "season": season_name,
                            "team": team_name,
                            "gp": raw[0],
                            "gs": raw[1],
                            "min": raw[2],
                            "fg": raw[3],
                            "fg_pct": raw[4],
                            "three_pt": raw[5],
                            "three_pct": raw[6],
                            "ft": raw[7],
                            "ft_pct": raw[8],
                            "reb": raw[11],
                            "ast": raw[12],
                            "blk": raw[13],
                            "stl": raw[14],
                            "to": raw[16],
                            "pts": raw[17],
                            "source": "ESPN",
                        })
        return seasons
