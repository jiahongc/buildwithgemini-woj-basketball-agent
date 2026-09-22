# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Woj — AI Basketball Intelligence Agent.
Equipped with live NBA data, historical statistics (1950-2026), advanced analytics (TS%, rTS%, BPM, VORP),
era-adjusted reasoning, evidence-first debate capabilities, and cross-session Vertex AI Memory Bank integration.
"""

import json
from typing import Any, Dict, List, Optional

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from app.data.historical_db import calculate_relative_ts, get_era_baseline
from app.data.query_engine import aggregate_game_logs
from app.data.unified_provider import UnifiedBasketballDataProvider

MODEL = "gemini-3.6-flash"

# Initialize unified basketball data provider
_provider = UnifiedBasketballDataProvider()


# ---------------------------------------------------------------------------
# Cross-Session Long-Term Memory Callback
# ---------------------------------------------------------------------------
async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, send the session to Vertex AI Memory Bank for extraction."""
    await callback_context.add_session_to_memory()
    return None


# ---------------------------------------------------------------------------
# Basketball Tool Definitions
# ---------------------------------------------------------------------------
def search_nba_players(query: str) -> str:
    """Search for NBA players by name across historical archives and current rosters.

    Args:
        query: Player name or partial name to search for (e.g. 'LeBron', 'Curry', 'Wembanyama').

    Returns:
        JSON string of matching player profiles with IDs and data source tags.
    """
    results = _provider.searchPlayer(query)
    return json.dumps(results[:6], indent=2)


def get_player_season_stats(player_name: str, season: Optional[str] = None) -> str:
    """Retrieve traditional per-game statistics (PTS, REB, AST, STL, BLK, FG%, 3P%, FT%, TS%) for an NBA player.

    Args:
        player_name: Name of the player (e.g., 'Stephen Curry', 'Nikola Jokic').
        season: Optional season format (e.g., '2015-16', '2016', '2023-24'). Defaults to current/most recent.

    Returns:
        JSON string containing the player's season averages and source badge.
    """
    stats = _provider.getPlayerSeasonStats(player_name, season=season)
    if not stats:
        return json.dumps({"error": f"No season stats found for {player_name} in season {season or 'recent'}"})
    return json.dumps(stats, indent=2)


def get_player_advanced_metrics(player_name: str, season: Optional[str] = None) -> str:
    """Retrieve advanced analytical metrics (PER, TS%, relative TS% [rTS%], eFG%, USG%, BPM, OBPM, DBPM, VORP, Win Shares, WS/48).

    Args:
        player_name: Name of the player (e.g., 'LeBron James', 'Michael Jordan', 'Shai Gilgeous-Alexander').
        season: Optional season format (e.g., '2012-13', '1990-91', '2024-25').

    Returns:
        JSON string of advanced analytics with era-relative efficiency adjustments and source citations.
    """
    stats = _provider.getPlayerAdvancedStats(player_name, season=season)
    if not stats:
        return json.dumps({"error": f"No advanced metrics found for {player_name} in season {season or 'recent'}"})
    return json.dumps(stats, indent=2)


def get_player_game_log(
    player_name: str,
    last_n_games: int = 10,
    season: Optional[str] = None,
    opponent: Optional[str] = None,
) -> str:
    """Retrieve game-by-game box scores and aggregate rolling statistics.

    Args:
        player_name: Name of the player (e.g., 'Jalen Brunson', 'Luka Doncic').
        last_n_games: Number of recent games to inspect (default 10).
        season: Optional season (e.g., '2023-24', '2013').
        opponent: Optional opponent team name to filter head-to-head match-ups (e.g., 'Celtics', 'Lakers').

    Returns:
        JSON string containing rolling window averages (PPG, RPG, APG, TS%, Record) and individual game logs.
    """
    logs = _provider.getPlayerGameLog(player_name, season=season, last_n=last_n_games, opponent=opponent)
    summary = aggregate_game_logs(logs, last_n=last_n_games)
    return json.dumps({
        "player": player_name,
        "window_summary": {k: v for k, v in summary.items() if k != "games_detail"},
        "game_logs": summary.get("games_detail", []),
        "source": "Basketball Reference & ESPN Game Logs",
    }, indent=2)


def compare_players_head_to_head(
    player1: str,
    player2: str,
    season1: Optional[str] = None,
    season2: Optional[str] = None,
) -> str:
    """Compare two NBA players side-by-side with era context, relative True Shooting (rTS%), and advanced metrics.

    Args:
        player1: First player name (e.g., 'Stephen Curry').
        player2: Second player name (e.g., 'Shai Gilgeous-Alexander').
        season1: Season for first player (e.g., '2015-16' or '2016').
        season2: Season for second player (e.g., '2024-25' or '2025').

    Returns:
        JSON string containing side-by-side comparison, relative efficiency deltas, and era baselines.
    """
    comp = _provider.comparePlayers([player1, player2], [season1, season2])
    return json.dumps(comp, indent=2)


def get_nba_standings() -> str:
    """Retrieve NBA conference standings for Eastern and Western Conferences.

    Returns:
        JSON string of team standings, win-loss summaries, and conference divisions.
    """
    standings = _provider.getStandings()
    return json.dumps(standings, indent=2)


def get_league_leaders(metric: str = "PTS", limit: int = 10) -> str:
    """Retrieve NBA league leaders sorted by a statistical category.

    Args:
        metric: Category to rank by: 'PTS' (scoring), 'AST' (assists), 'REB' (rebounds), or 'TS%' (efficiency).
        limit: Number of leaders to return (default 10).

    Returns:
        JSON string listing the top league leaders with stat averages and team information.
    """
    leaders = _provider.getLeagueLeaders(metric=metric, limit=limit)
    return json.dumps(leaders, indent=2)


def get_live_scores_and_schedule() -> str:
    """Retrieve live NBA scores, game statuses, and upcoming schedules for today's slate.

    Returns:
        JSON string with game matchups, current scores, and status descriptions.
    """
    scores = _provider.getGame("") if False else _provider.espn.get_live_scoreboard()
    return json.dumps(scores, indent=2)


def get_team_roster(team_name: str) -> str:
    """Retrieve the active roster and player information for any NBA team.

    Args:
        team_name: Name, city, or abbreviation of the team (e.g., 'Warriors', 'Knicks', 'BOS').

    Returns:
        JSON string with team players, positions, jersey numbers, and measurements.
    """
    roster = _provider.getTeamRoster(team_name)
    return json.dumps(roster, indent=2)


def get_era_context(year: int) -> str:
    """Retrieve historical NBA era baselines for league pace, average True Shooting (TS%), 3-point attempt rate, and offensive rating.

    Args:
        year: Season end year (e.g., 1993, 2004, 2016, 2024). Supported from 1950 to 2026.

    Returns:
        JSON string of league baseline statistics and era description.
    """
    baseline = get_era_baseline(year)
    return json.dumps(baseline, indent=2)


# ---------------------------------------------------------------------------
# Woj System Prompt & Agent Initialization
# ---------------------------------------------------------------------------
WOJ_INSTRUCTION = """
You are Woj — an AI basketball intelligence agent.
(Disclaimer: The name is inspired by the ultimate NBA insider concept, but you do NOT impersonate, claim to be, or speak on behalf of any real person).

YOUR MISSION:
Deliver encyclopedic basketball knowledge, live and historical NBA statistics, advanced analytics, era-adjusted reasoning, and sharp evidence-first basketball debate.

CORE PERSONA & VOICE:
- Knowledgeable, analytical, confident, curious, and direct.
- Never needlessly agreeable. If the user makes a basketball claim contradicted by evidence or historical context (e.g., "Kobe was inefficient", "Russell Westbrook had no impact in 2017", "90s players couldn't shoot"), challenge it respectfully with hard data.
- Avoid generic AI conversational filler ("That's a fantastic question!", "You make a great point!", "Certainly, I'd be happy to help!"). Dive straight into the analysis.
- Be nuanced: distinguish clearly between what the numbers prove, what they suggest, and what remains subjective or film-dependent.

CRITICAL ACCURACY & EVIDENCE RULES:
1. NEVER FABRICATE STATISTICS. Always invoke your tools (`get_player_season_stats`, `get_player_advanced_metrics`, `compare_players_head_to_head`, `get_player_game_log`, `get_league_leaders`, etc.) to retrieve verified numbers.
2. ALWAYS CITE SOURCES: Mention where data originates (e.g., "[Source: Basketball Reference]", "[Source: NBA Official Database]", "[Source: ESPN]").
3. ERA AWARENESS & RELATIVE TRUE SHOOTING (rTS%):
   - Never compare raw raw shooting percentages across eras without era context.
   - 56% TS% in 2004 was elite (+4.4% rTS above the 51.6% league average in the dead-ball era).
   - In 2024, league average TS% is ~58.0%, so 56% TS% is -2.0% rTS.
   - Account for pace (e.g., 1998 pace: 90.3 possessions vs 2024 pace: 99.1 possessions).
4. EVIDENCE-FIRST DEBATE ARCHITECTURE:
   When engaging in debates, player comparisons, or hot takes:
   - Step 1: Deconstruct the claim into testable components.
   - Step 2: Retrieve and present concrete statistical evidence (traditional, advanced, and window splits).
   - Step 3: Analyze situational context (spacing, defensive schemes, roster construction, playoff defenses).
   - Step 4: Fairly articulate the strongest counterargument.
   - Step 5: Deliver a clear, authoritative conclusion.

CROSS-SESSION MEMORY:
- You have long-term memory via Vertex AI Memory Bank.
- Remember the user's favorite teams, favorite players, past debate positions, and analytical preferences across conversations. Personalize your insights accordingly.
"""

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=WOJ_INSTRUCTION,
    tools=[
        PreloadMemoryTool(),
        search_nba_players,
        get_player_season_stats,
        get_player_advanced_metrics,
        get_player_game_log,
        compare_players_head_to_head,
        get_nba_standings,
        get_league_leaders,
        get_live_scores_and_schedule,
        get_team_roster,
        get_era_context,
    ],
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
