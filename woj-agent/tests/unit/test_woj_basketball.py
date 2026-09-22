"""
Unit tests for Woj Basketball Intelligence Agent and Data Provider.
"""

import json
import pytest
from app.agent import root_agent, search_nba_players, get_player_season_stats, get_player_advanced_metrics, compare_players_head_to_head, get_era_context, search_web_and_nba_news
from app.data.historical_db import calculate_relative_ts, get_era_baseline
from app.data.query_engine import calculate_ts_percentage, calculate_efg_percentage, aggregate_game_logs
from app.data.unified_provider import UnifiedBasketballDataProvider
from app.app_utils.services import get_memory_service, MEMORY_BANK_ID


def test_agent_structure_and_memory():
    """Verify that root_agent has the expected name, PreloadMemoryTool, and callback."""
    assert root_agent.name == "root_agent"
    tool_names = [getattr(t, "name", str(t)) for t in root_agent.tools]
    assert "preload_memory" in tool_names
    assert root_agent.after_agent_callback is not None


def test_memory_bank_service_configuration():
    """Verify memory bank service initialization and memory bank ID."""
    assert MEMORY_BANK_ID == "1185759518882004992"
    service = get_memory_service()
    assert service is not None


def test_derived_stat_calculations():
    """Verify TS% and eFG% calculations."""
    # 30 pts, 20 FGA, 10 FTA -> 30 / (2 * (20 + 4.4)) = 30 / 48.8 = 0.615
    ts = calculate_ts_percentage(30, 20, 10)
    assert 0.614 <= ts <= 0.616

    # 10 FGM, 4 3PM, 20 FGA -> (10 + 2) / 20 = 0.600
    efg = calculate_efg_percentage(10, 4, 20)
    assert efg == 0.600


def test_era_baselines_and_relative_ts():
    """Verify era baseline lookups and relative TS% calculation."""
    base_2004 = get_era_baseline(2004)
    assert base_2004["lg_ts"] == 0.516
    assert base_2004["pace"] == 90.1

    base_2024 = get_era_baseline(2024)
    assert base_2024["lg_ts"] == 0.580

    # 56% TS in 2004 should be +4.4% relative
    rts_2004 = calculate_relative_ts(0.560, 2004)
    assert rts_2004 == pytest.approx(4.4, abs=0.1)

    # 56% TS in 2024 should be -2.0% relative
    rts_2024 = calculate_relative_ts(0.560, 2024)
    assert rts_2024 == pytest.approx(-2.0, abs=0.1)


def test_unified_provider_historical_and_tools():
    """Verify tool execution returns valid JSON."""
    p_json = search_nba_players("LeBron")
    players = json.loads(p_json)
    assert len(players) > 0
    assert any("LeBron" in p["name"] for p in players)

    adv_json = get_player_advanced_metrics("LeBron James", "2012-13")
    adv = json.loads(adv_json)
    assert adv["per"] == 31.6
    assert adv["ts_pct"] == 0.640

    comp_json = compare_players_head_to_head("Stephen Curry", "Shai Gilgeous-Alexander", "2016", "2025")
    comp = json.loads(comp_json)
    assert "player1" in comp
    assert "player2" in comp
    assert "era_comparison" in comp


def test_game_log_aggregation():
    """Verify aggregate_game_logs computes accurate averages."""
    sample_games = [
        {"pts": 30, "reb": 10, "ast": 5, "min": 35, "fga": 20, "fgm": 10, "fta": 8, "tpm": 2, "result": "W"},
        {"pts": 20, "reb": 6, "ast": 7, "min": 33, "fga": 16, "fgm": 7, "fta": 4, "tpm": 1, "result": "L"},
    ]
    summary = aggregate_game_logs(sample_games)
    assert summary["games_count"] == 2
    assert summary["pts"] == 25.0
    assert summary["reb"] == 8.0
    assert summary["ast"] == 6.0
    assert summary["record"] == "1-1"


def test_search_web_and_nba_news_tool():
    """Verify that search_web_and_nba_news returns informative results without raising exceptions."""
    result = search_web_and_nba_news("NBA 2026-27 season opener schedule")
    assert isinstance(result, str)
    assert len(result) > 20
