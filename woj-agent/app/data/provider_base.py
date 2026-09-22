"""
Basketball Data Provider Abstraction.
Defines normalized methods for retrieving NBA data across multiple backends.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BasketballDataProvider(ABC):
    """Normalized interface for basketball data providers."""

    @abstractmethod
    def searchPlayer(self, query: str) -> List[Dict[str, Any]]:
        """Search for players by name.
        Returns list of player summaries: [{'id': ..., 'name': ..., 'team': ..., 'active': ...}]
        """
        pass

    @abstractmethod
    def getPlayer(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Get player profile metadata (name, position, height, weight, draft, current team, etc.)."""
        pass

    @abstractmethod
    def getPlayerSeasonStats(self, player_id: str, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get traditional per-game season stats for a given season or current season.
        Returns dict with PTS, REB, AST, STL, BLK, FG%, 3P%, FT%, MIN, GP, etc.
        """
        pass

    @abstractmethod
    def getPlayerCareerStats(self, player_id: str) -> List[Dict[str, Any]]:
        """Get career year-by-year regular season stats."""
        pass

    @abstractmethod
    def getPlayerGameLog(
        self,
        player_id: str,
        season: Optional[str] = None,
        last_n: Optional[int] = None,
        opponent: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get game logs for a player, optionally filtered by last N games or opponent."""
        pass

    @abstractmethod
    def getPlayerSplits(self, player_id: str, season: Optional[str] = None) -> Dict[str, Any]:
        """Get situational splits (home/away, vs conference, monthly)."""
        pass

    @abstractmethod
    def getPlayerAdvancedStats(self, player_id: str, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get advanced analytics: TS%, eFG%, USG%, PER, BPM, OBPM, DBPM, VORP, Win Shares, rTS%."""
        pass

    @abstractmethod
    def getPlayerPlayoffStats(self, player_id: str) -> List[Dict[str, Any]]:
        """Get year-by-year playoff stats for a player."""
        pass

    @abstractmethod
    def getTeam(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get team profile info."""
        pass

    @abstractmethod
    def getTeamStats(self, team_id: str, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get traditional team stats (PPG, RPG, APG, OPP PPG, etc.)."""
        pass

    @abstractmethod
    def getTeamAdvancedStats(self, team_id: str, season: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get team advanced stats (ORTG, DRTG, Net Rating, Pace)."""
        pass

    @abstractmethod
    def getTeamRoster(self, team_id: str) -> List[Dict[str, Any]]:
        """Get active team roster."""
        pass

    @abstractmethod
    def getTeamSchedule(self, team_id: str) -> List[Dict[str, Any]]:
        """Get upcoming schedule and recent results for a team."""
        pass

    @abstractmethod
    def getGame(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Get single game summary and status."""
        pass

    @abstractmethod
    def getBoxScore(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Get full box score for a game."""
        pass

    @abstractmethod
    def getStandings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get NBA conference standings (Eastern & Western)."""
        pass

    @abstractmethod
    def getLeagueLeaders(
        self, metric: str = "PTS", limit: int = 10, min_ppg: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get league leaders for a specific statistical category."""
        pass

    @abstractmethod
    def comparePlayers(
        self,
        player_ids: List[str],
        seasons: Optional[List[Optional[str]]] = None,
        game_window: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Compare multiple players side-by-side."""
        pass

    @abstractmethod
    def compareTeams(self, team_ids: List[str], season: Optional[str] = None) -> Dict[str, Any]:
        """Compare teams side-by-side."""
        pass

    @abstractmethod
    def searchBasketballData(self, query: str) -> Dict[str, Any]:
        """General multi-entity basketball search (players, teams, historical events)."""
        pass
