"""
JohnnyBets Chat Agent

Refactored LangGraph agent for the web API with streaming support.
Wraps the existing chat_agent functionality for HTTP/SSE delivery.
"""
import os
import sys
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from uuid import uuid4

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add parent directory for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import existing tools from src/
from src.tools.kalshi import KalshiClient
from src.tools.odds_api import OddsAPIClient
from src.tools.x_search import XSearchClient
from src.analysis.contextual_props import ContextualPropsAnalyzer
from src.tools.nfl_data import NFLDataFetcher
from src.analysis.edge_validator import validate_bet
from src.tools.nhl_data import NHLDataFetcher, get_nhl_fetcher
from src.analysis.goalie_props import GoaliePropsAnalyzer
from src.analysis.team_matchup import TeamMatchupAnalyzer
from src.tools.nhl_referees import NHLRefereeDatabase
from src.tools.mlb_data import (
    analyze_pitcher_props as _analyze_pitcher_props,
    get_pitcher_profile as _get_pitcher_profile,
    get_lineup_vs_pitcher as _get_lineup_vs_pitcher,
    get_park_factors as _get_park_factors,
    analyze_bullpen_usage as _analyze_bullpen_usage,
    get_weather_impact as _get_weather_impact,
)
# NBA imports
from src.tools.nba_data import NBADataFetcher, get_nba_fetcher
from src.tools.nba_referees import NBARefereeDatabase
from src.analysis.nba_props import NBAPropsAnalyzer
from src.analysis.nba_tempo import PaceTempoAnalyzer
from src.analysis.nba_load_management import LoadManagementTracker


# =============================================================================
# TOOL DEFINITIONS (Re-export from src/chat_agent.py for now)
# =============================================================================

@tool
def fetch_sportsbook_odds(sport: str = "nfl", max_hours: int = None) -> str:
    """
    Fetch odds from multiple sportsbooks via The Odds API.
    Includes DraftKings, FanDuel, BetMGM, MyBookie, and more.
    
    IMPORTANT: This tool automatically filters out games that have already started
    or start within 15 minutes. Only bettable future games are returned.
    
    Args:
        sport: Sport to fetch (nfl, nba, mlb, nhl)
        max_hours: Optional maximum hours until game start (e.g., 24 for today's games only)
        
    Returns:
        JSON string of odds data from multiple books (future games only)
    """
    try:
        client = OddsAPIClient()
        
        if sport.lower() == "nfl":
            games = client.get_nfl_odds(only_future=True, max_hours_until_start=max_hours)
        elif sport.lower() == "nba":
            games = client.get_nba_odds(only_future=True, max_hours_until_start=max_hours)
        else:
            all_games = client.get_odds(sport=sport)
            games = client.filter_future_games(all_games, max_hours_until_start=max_hours)
        
        summary = []
        for game in games:
            game_info = {
                "matchup": f"{game.get('away_team')} @ {game.get('home_team')}",
                "time": game.get("commence_time"),
                "time_until_start": game.get("_time_until_start"),
                "time_parse_warning": game.get("_time_parse_warning", False),
                "bookmakers": []
            }
            for book in game.get("bookmakers", [])[:5]:
                book_info = {"name": book.get("title"), "markets": {}}
                for market in book.get("markets", []):
                    book_info["markets"][market.get("key")] = market.get("outcomes")
                game_info["bookmakers"].append(book_info)
            summary.append(game_info)
        
        # Build note based on parameters
        note = "Only showing games that have NOT started yet (15+ min until kickoff)"
        if max_hours:
            note += f" and start within {max_hours} hours"
        
        return json.dumps({
            "status": "success",
            "current_time_utc": datetime.now(timezone.utc).isoformat(),
            "games_count": len(games),
            "note": note,
            "quota_remaining": client.remaining_requests,
            "games": summary
        }, indent=2, default=str)
    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "hint": "Get a free API key at https://the-odds-api.com/"
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def fetch_kalshi_markets(sport: str = "nfl", market_type: str = "all", limit: int = 50) -> str:
    """
    Fetch prediction market data from Kalshi.
    
    Args:
        sport: Sport to fetch (nfl, nba)
        market_type: Type of markets - "futures", "games", "spreads", "totals", or "all"
        limit: Maximum markets per category
        
    Returns:
        JSON string of market data with volume and pricing
    """
    import requests
    
    try:
        base_url = 'https://api.elections.kalshi.com/trade-api/v2'
        
        NFL_SERIES = {
            "futures": ["KXSB"],
            "games": ["KXNFLGAME"],
            "spreads": ["KXNFLSPREAD"],
            "totals": ["KXNFLTOTAL"],
            "conference": ["KXAFC", "KXNFC", "KXNFLAFCCHAMP", "KXNFLNFCCHAMP"],
        }
        
        NBA_SERIES = {
            "futures": ["KXNBA"],
            "games": ["KXNBAGAME"],
            "conference": ["KXNBAEAST", "KXNBAWEST"],
        }
        
        if sport.lower() == "nfl":
            series_map = NFL_SERIES
        elif sport.lower() == "nba":
            series_map = NBA_SERIES
        else:
            return json.dumps({"status": "error", "message": f"Sport '{sport}' not supported"})
        
        if market_type == "all":
            series_to_fetch = []
            for series_list in series_map.values():
                series_to_fetch.extend(series_list)
        elif market_type in series_map:
            series_to_fetch = series_map[market_type]
        else:
            return json.dumps({"status": "error", "message": f"market_type '{market_type}' not recognized"})
        
        all_markets = []
        series_results = {}
        
        for series_ticker in series_to_fetch:
            response = requests.get(f'{base_url}/markets', params={
                'limit': limit,
                'series_ticker': series_ticker,
                'status': 'open'
            })
            
            if response.status_code == 200:
                markets = response.json().get('markets', [])
                series_results[series_ticker] = len(markets)
                
                for m in markets:
                    vol = m.get('volume', 0) or 0
                    vol_24h = m.get('volume_24h', 0) or 0
                    
                    all_markets.append({
                        "ticker": m.get("ticker"),
                        "series": series_ticker,
                        "title": m.get("title"),
                        "yes_bid": m.get("yes_bid"),
                        "yes_ask": m.get("yes_ask"),
                        "volume": vol,
                        "volume_24h": vol_24h,
                        "last_price": m.get("last_price"),
                    })
        
        all_markets.sort(key=lambda x: x.get("volume", 0), reverse=True)
        
        return json.dumps({
            "status": "success",
            "current_time_utc": datetime.now(timezone.utc).isoformat(),
            "sport": sport.upper(),
            "market_type": market_type,
            "total_markets": len(all_markets),
            "markets": all_markets[:30],
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def find_arbitrage_opportunities(sport: str = "nfl") -> str:
    """
    Scan sportsbooks for arbitrage opportunities where implied probabilities
    sum to less than 100%, indicating a guaranteed profit opportunity.
    """
    try:
        client = OddsAPIClient()
        all_games = client.get_odds(sport=sport)
        games = client.filter_future_games(all_games)
        
        arbs = []
        for game in games:
            home = game.get("home_team")
            away = game.get("away_team")
            
            best_home = {"price": -99999, "book": None}
            best_away = {"price": -99999, "book": None}
            
            for book in game.get("bookmakers", []):
                for market in book.get("markets", []):
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            price = outcome.get("price", -99999)
                            if outcome.get("name") == home and price > best_home["price"]:
                                best_home = {"price": price, "book": book.get("title")}
                            elif outcome.get("name") == away and price > best_away["price"]:
                                best_away = {"price": price, "book": book.get("title")}
            
            def implied_prob(odds):
                if odds > 0:
                    return 100 / (odds + 100)
                else:
                    return abs(odds) / (abs(odds) + 100)
            
            if best_home["book"] and best_away["book"]:
                total_implied = implied_prob(best_home["price"]) + implied_prob(best_away["price"])
                
                if total_implied < 1.0:
                    arbs.append({
                        "game": f"{away} @ {home}",
                        "best_home": best_home,
                        "best_away": best_away,
                        "total_implied": round(total_implied * 100, 2),
                        "profit_margin": round((1 - total_implied) * 100, 2)
                    })
        
        return json.dumps({
            "status": "success",
            "arbs_found": len(arbs),
            "opportunities": arbs
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def search_x_twitter(query: str) -> str:
    """Search X/Twitter for sports betting intel - use only if necessary because the queries take a while.
    
    IMPORTANT: Use specialized tools FIRST, then use this only to fill gaps:
    1. get_injury_updates(team, sport) - for injury/practice reports
    2. get_line_movement_buzz(matchup) - for sharp money/steam moves
    3. get_breaking_sports_news(sport) - for breaking news
    
    Only use search_x_twitter for custom queries not covered by the above,
    such as specific player news, weather updates, or niche betting angles.
    
    Args:
        query: Custom search query (be specific, include sport context)
    """
    try:
        client = XSearchClient()
        return client.search(query, context="sports betting analysis")
    except ValueError as e:
        return f"X search unavailable: {e}"
    except Exception as e:
        return f"X search error: {e}"


@tool
def get_injury_updates(team: str, sport: str = None) -> str:
    """Get the latest injury news for a team from X/Twitter.
    
    Args:
        team: Team name (e.g., "Blackhawks", "CHI")
        sport: Optional sport for disambiguation (NHL, NBA, NFL, MLB)
    """
    try:
        client = XSearchClient()
        return client.get_injury_report(team, sport=sport)
    except Exception as e:
        return f"Error fetching injury updates: {e}"


@tool
def get_line_movement_buzz(matchup: str) -> str:
    """Search X for sharp money action and line movement discussion."""
    try:
        client = XSearchClient()
        return client.get_line_movement_intel(matchup)
    except Exception as e:
        return f"Error fetching line movement: {e}"


@tool
def get_breaking_sports_news(sport: str = "NFL") -> str:
    """Get breaking sports news that could affect betting lines."""
    try:
        client = XSearchClient()
        return client.get_breaking_news(sport)
    except Exception as e:
        return f"Error fetching news: {e}"


@tool
def analyze_player_props(
    player_name: str,
    position: str,
    opponent: str,
    passing_yards_line: float = None,
    passing_tds_line: float = None,
    rushing_yards_line: float = None,
    wind_mph: float = None,
    temp_f: float = None,
    expected_game_script: str = "close"
) -> str:
    """
    Analyze player props using contextual performance data (Prop Alpha v2.0).
    Uses DATA-DRIVEN defense profiling to compare player performance.
    """
    try:
        analyzer = ContextualPropsAnalyzer(years=[2023, 2024, 2025])
        
        current_lines = {}
        if passing_yards_line:
            current_lines["passing_yards"] = passing_yards_line
        if passing_tds_line:
            current_lines["passing_tds"] = passing_tds_line
        if rushing_yards_line:
            current_lines["rushing_yards"] = rushing_yards_line
        
        weather = None
        if wind_mph is not None or temp_f is not None:
            weather = {}
            if wind_mph is not None:
                weather["wind"] = wind_mph
            if temp_f is not None:
                weather["temp"] = temp_f
        
        analysis = analyzer.full_matchup_analysis(
            player_name=player_name,
            position=position.upper(),
            opponent=opponent,
            current_lines=current_lines,
            game_weather=weather,
            expected_script=expected_game_script
        )
        
        results = {
            "status": "success",
            "player": player_name,
            "opponent": opponent,
            "opponent_defense_profile": {
                "sack_rate": analysis.opponent_profile.sack_rate,
                "completion_pct_allowed": analysis.opponent_profile.completion_pct_allowed,
            },
            "similar_defenses": [
                {"team": team, "similarity": f"{sim:.0%}"}
                for team, sim, prof in analysis.similar_defenses
            ],
            "projections": []
        }
        
        for p in analysis.projections:
            proj = {
                "prop_type": p.prop_type,
                "season_average": round(p.standard_projection, 1),
                "contextual_projection": round(p.contextual_projection, 1),
                "current_line": p.current_line,
                "edge": round(p.edge, 1) if p.edge else None,
                "confidence": p.confidence,
                "recommended_action": (
                    "OVER" if p.edge and p.edge > 5 else
                    "UNDER" if p.edge and p.edge < -5 else
                    "PASS"
                )
            }
            results["projections"].append(proj)
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def get_defense_profile(team: str) -> str:
    """Get a data-driven defensive profile for an NFL team."""
    try:
        fetcher = NFLDataFetcher(years=[2023, 2024, 2025])
        profile = fetcher.calculate_defense_profile(team, tuple([2023, 2024, 2025]))
        similar = fetcher.find_similar_defenses(team, top_n=5)
        
        return json.dumps({
            "status": "success",
            "team": team,
            "metrics": {
                "sack_rate_pct": profile.sack_rate,
                "completion_pct_allowed": profile.completion_pct_allowed,
                "avg_air_yards_allowed": profile.avg_air_yards_allowed,
            },
            "similar_defenses": [
                {"team": t, "similarity": f"{s:.0%}"} 
                for t, s, _ in similar
            ]
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def get_player_weather_splits(player_name: str, position: str = "QB") -> str:
    """Get player performance splits by weather conditions."""
    try:
        fetcher = NFLDataFetcher(years=[2023, 2024, 2025])
        splits = fetcher.get_player_weather_splits(player_name, position)
        return json.dumps({
            "status": "success",
            "player": player_name,
            "weather_splits": splits
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def get_player_game_script_splits(player_name: str, position: str = "QB") -> str:
    """Get player performance splits by game script."""
    try:
        fetcher = NFLDataFetcher(years=[2023, 2024, 2025])
        splits = fetcher.get_player_game_script_splits(player_name, position)
        return json.dumps({
            "status": "success",
            "player": player_name,
            "game_script_splits": splits,
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def validate_betting_edge(
    bet_type: str,
    is_favorite: bool = False,
    is_playoff: bool = False,
    is_home: bool = False,
    public_pct: float = None,
    weather_condition: str = None,
    juice: int = -110,
    historical_hit_rate: float = None,
    projection: float = None,
    line: float = None,
    is_over: bool = True,
    sample_size: int = 20,
) -> str:
    """Anti-slop validator - validates if a bet has real edge."""
    try:
        if bet_type == "spread":
            result = validate_bet(
                "spread",
                spread=line or -3.0,
                juice=juice,
                is_favorite=is_favorite,
                is_playoff=is_playoff,
                is_home=is_home,
                public_pct=public_pct,
                weather_condition=weather_condition,
            )
        elif bet_type == "total":
            # Auto-calculate hit rate if we have projection vs line but no explicit hit rate
            if historical_hit_rate is None and projection is not None and line is not None:
                diff = line - projection
                # Heuristic: larger diff from projection = higher confidence
                if is_over:
                    # Over: when line is higher than projection, over is harder
                    estimated_rate = 50 + (diff * 3)
                else:
                    # Under: when line is higher than projection, under is easier
                    estimated_rate = 50 + (-diff * 3)
                historical_hit_rate = max(45, min(65, estimated_rate))  # Clamp to reasonable range
            
            if historical_hit_rate is None:
                return """ERROR: For totals, you must provide historical_hit_rate.

This should be derived from your data analysis:
- For pace/tempo analysis: Use the projected total vs line to estimate hit rate
- For weather unders: Use historical under hit rate in similar conditions
- Example: If projected total is 5.8 and line is 6.5, hit rate for under ~55-60%

Typical ranges: 50-52% = marginal edge, 53-56% = solid edge, 57%+ = strong edge

TIP: You can also provide 'projection' and 'line' and I'll estimate the hit rate."""
            result = validate_bet(
                "total",
                total=line or 40.5,
                is_over=is_over,
                juice=juice,
                historical_hit_rate=historical_hit_rate,
                weather_condition=weather_condition,
                public_pct=public_pct,
            )
        elif bet_type == "prop":
            if projection is None or line is None:
                return """ERROR: For props, you must provide both projection and line.

Required parameters:
- projection: Your projected value for the player stat (e.g., 285 passing yards)
- line: The betting line (e.g., 275.5)

Optional but recommended:
- is_over: True if betting OVER (default), False for UNDER
- juice: The vig (default -110)
- sample_size: Number of games in your sample (default 20)"""
            result = validate_bet(
                "prop",
                prop_type="player_prop",
                projection=projection,
                line=line,
                is_over=is_over,
                juice=juice,
                sample_size=sample_size,
            )
        else:
            return f"ERROR: Unknown bet_type '{bet_type}'"
        
        return result.to_markdown()
    except Exception as e:
        return f"ERROR validating edge: {str(e)}"


# NHL Tools
@tool
def analyze_goalie_props(
    goalie_name: str,
    opponent: str,
    is_back_to_back: bool = False,
    expected_shots: float = None,
    saves_line: float = None,
    goals_against_line: float = None
) -> str:
    """Analyze NHL goalie props with B2B splits, xGSV%, and opponent quality."""
    try:
        analyzer = GoaliePropsAnalyzer()
        analysis = analyzer.analyze_goalie_props(
            goalie_name=goalie_name,
            opponent=opponent,
            is_back_to_back=is_back_to_back,
            expected_shots=expected_shots,
            saves_line=saves_line,
            goals_against_line=goals_against_line,
        )
        return analyzer.to_json(analysis)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def get_nhl_goalie_profile(goalie_name: str) -> str:
    """Get detailed goalie profile with save %, xGSV%, and B2B splits."""
    try:
        fetcher = get_nhl_fetcher()  # Use singleton to share cache
        profile = fetcher.get_goalie_profile(goalie_name)
        
        if not profile:
            return json.dumps({"status": "error", "message": f"Goalie not found: {goalie_name}"})
        
        # Convert numpy types to native Python for JSON serialization
        return json.dumps({
            "status": "success",
            "goalie": str(profile.name),
            "team": str(profile.team),
            "games_played": int(profile.games_played),
            "save_pct": float(profile.save_pct),
            "xg_save_pct": float(profile.xg_save_pct),
            "luck_factor": float(profile.luck_factor),
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def get_nhl_team_profile(team: str) -> str:
    """Get NHL team analytics profile with Corsi, xG, and possession metrics."""
    try:
        fetcher = get_nhl_fetcher()  # Use singleton to share cache
        profile = fetcher.get_team_profile(team)
        
        if not profile:
            return json.dumps({"status": "error", "message": f"Team not found: {team}"})
        
        # Convert numpy types to native Python for JSON serialization
        return json.dumps({
            "status": "success",
            "team": str(profile.team),
            "games_played": int(profile.games_played),
            "corsi_pct": float(profile.corsi_pct),
            "xg_for_per_game": float(profile.xg_for_per_game),
            "xg_against_per_game": float(profile.xg_against_per_game),
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def analyze_nhl_matchup(home_team: str, away_team: str) -> str:
    """Analyze NHL team matchup with Corsi/xG edge identification."""
    try:
        analyzer = TeamMatchupAnalyzer()
        analysis = analyzer.analyze_matchup(home_team, away_team)
        return analyzer.to_json(analysis)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def get_referee_tendencies(referee_1: str = None, referee_2: str = None) -> str:
    """Get NHL referee penalty and total tendencies."""
    try:
        db = NHLRefereeDatabase()
        analysis = db.analyze_game_refs(referee_1, referee_2)
        return json.dumps(analysis, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


# =============================================================================
# NBA TOOLS
# =============================================================================

@tool
def analyze_nba_player_prop(
    player_name: str,
    position: str,
    opponent: str,
    prop_type: str,
    prop_line: float,
    pace_factor: str = "normal",
    expected_blowout: bool = False,
) -> str:
    """
    Analyze NBA player prop with DvP, pace, and game script context.
    
    Uses Defense vs Position (DvP) rankings, pace adjustments, usage rate,
    game script expectations, and recent form to project player performance.
    
    Args:
        player_name: Player name (e.g., "Jalen Brunson")
        position: Position (PG, SG, SF, PF, C)
        opponent: Opponent team abbreviation (e.g., "BOS")
        prop_type: Type of prop (PTS, AST, REB, 3PM, PTS+REB+AST)
        prop_line: The betting line (e.g., 28.5)
        pace_factor: Expected pace ("fast", "slow", "normal")
        expected_blowout: Whether blowout is expected (reduces star minutes)
        
    Returns:
        JSON with projections, edge analysis, and betting recommendations
    """
    try:
        analyzer = NBAPropsAnalyzer()
        analysis = analyzer.analyze_player_prop(
            player_name=player_name,
            position=position,
            opponent=opponent,
            prop_type=prop_type,
            prop_line=prop_line,
            pace_factor=pace_factor,
            expected_blowout=expected_blowout,
        )
        return analyzer.to_json(analysis)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def analyze_nba_pace_tempo(
    home_team: str,
    away_team: str,
    current_total: float = None,
) -> str:
    """
    Analyze pace matchup and projected game total.
    
    Calculates projected possessions per 48, tempo edge, and total adjustment.
    Identifies track meet (both fast) vs grind (both slow) matchups.
    
    Args:
        home_team: Home team abbreviation (e.g., "SAC")
        away_team: Away team abbreviation (e.g., "IND")
        current_total: Current betting total (optional, for edge calculation)
        
    Returns:
        JSON with pace analysis, projected total, and over/under lean
    """
    try:
        analyzer = PaceTempoAnalyzer()
        analysis = analyzer.analyze_matchup(
            home_team=home_team,
            away_team=away_team,
            current_total=current_total,
        )
        return analyzer.to_json(analysis)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def get_nba_load_management(
    player_name: str,
    team: str = None,
    is_back_to_back: bool = False,
    opponent: str = None,
) -> str:
    """
    Get load management analysis and projected minutes for NBA player.
    
    Tracks rest days, back-to-back splits, fatigue index, and DNP risk.
    Critical for prop betting when stars may sit or see reduced minutes.
    
    Args:
        player_name: Player name (e.g., "LeBron James")
        team: Team abbreviation (optional)
        is_back_to_back: Whether this is a B2B game
        opponent: Opponent team (optional, for context)
        
    Returns:
        JSON with load profile, projected minutes, and risk assessment
    """
    try:
        tracker = LoadManagementTracker()
        analysis = tracker.analyze_load(
            player_name=player_name,
            team=team,
            is_back_to_back=is_back_to_back,
            opponent=opponent,
        )
        return tracker.to_json(analysis)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def get_nba_defense_profile(team: str) -> str:
    """
    Get team's defensive profile with DvP rankings.
    
    Includes defensive rating, opponent FG%, blocks, steals, and 
    defense vs position adjustments for prop betting.
    
    Args:
        team: Team abbreviation (e.g., "BOS", "MIL")
        
    Returns:
        JSON with defensive metrics and DvP by position
    """
    try:
        fetcher = get_nba_fetcher()
        profile = fetcher.get_defense_profile(team)
        
        if not profile:
            return json.dumps({"status": "error", "message": f"Team not found: {team}"})
        
        return json.dumps({
            "status": "success",
            "team": profile.team,
            "games_played": profile.games_played,
            "def_rating": profile.def_rating,
            "opp_pts_per_game": profile.opp_pts_per_game,
            "opp_fg_pct": profile.opp_fg_pct,
            "opp_3pt_pct": profile.opp_3pt_pct,
            "blocks_per_game": profile.blocks_per_game,
            "steals_per_game": profile.steals_per_game,
            "style": profile.get_style(),
            "dvp_by_position": profile.dvp_by_position,
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def analyze_nba_refs(referee_names: str) -> str:
    """
    Analyze NBA referee crew tendencies for game totals.
    
    Provides foul rates, FT rate, total impact, and over/under tendencies.
    Crews like Scott Foster = under lean; whistle-happy refs = over lean.
    
    Args:
        referee_names: Comma-separated referee names (e.g., "Scott Foster, Tony Brothers")
        
    Returns:
        JSON with crew analysis, total lean, and foul expectations
    """
    try:
        db = NBARefereeDatabase()
        
        # Parse referee names
        refs = [r.strip() for r in referee_names.split(",") if r.strip()]
        
        if len(refs) >= 3:
            analysis = db.analyze_crew(refs[0], refs[1], refs[2])
        elif len(refs) == 2:
            analysis = db.analyze_crew(refs[0], refs[1])
        elif len(refs) == 1:
            analysis = db.analyze_crew(refs[0])
        else:
            return json.dumps({"status": "error", "message": "No referee names provided"})
        
        return json.dumps(analysis, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


# =============================================================================
# MLB TOOLS
# =============================================================================

@tool
def analyze_pitcher_props(
    pitcher_name: str,
    opponent: str,
    line_ks: float = None,
    line_ip: float = None,
    park: str = None,
) -> str:
    """
    Analyze MLB pitcher props with projections and betting edges.
    
    Provides K projections, IP estimates, ERA context, defense-adjusted splits,
    pitch mix analysis, and park/weather factors.
    
    Args:
        pitcher_name: Pitcher's full name (e.g., "Spencer Strider")
        opponent: Opposing team abbreviation (e.g., "NYY", "BOS")
        line_ks: Strikeouts line to analyze (optional, e.g., 7.5)
        line_ip: Innings pitched line to analyze (optional, e.g., 5.5)
        park: Stadium if different from opponent's home (optional)
    
    Returns:
        JSON with projections, edge analysis, and betting recommendations
    """
    return _analyze_pitcher_props(pitcher_name, opponent, line_ks, line_ip, park)


@tool
def get_pitcher_profile(pitcher_name: str) -> str:
    """
    Get detailed MLB pitcher profile and advanced metrics.
    
    Includes K/9, BB/9, xERA, Stuff+, pitch mix breakdown, platoon splits,
    and recent form. Essential context for prop betting.
    
    Args:
        pitcher_name: Pitcher's full name (e.g., "Gerrit Cole")
    
    Returns:
        JSON with traditional stats, advanced metrics, and platoon data
    """
    return _get_pitcher_profile(pitcher_name)


@tool
def get_lineup_vs_pitcher(pitcher_name: str, opponent: str) -> str:
    """
    Analyze how a team's lineup matches up against a specific pitcher.
    
    Shows xwOBA, K rates, and barrel rates by batter with platoon context.
    
    Args:
        pitcher_name: Pitcher's full name
        opponent: Team facing the pitcher (abbreviation)
    
    Returns:
        JSON with lineup matchup analysis and betting angles
    """
    return _get_lineup_vs_pitcher(pitcher_name, opponent)


@tool
def get_mlb_park_factors(team: str) -> str:
    """
    Get MLB park factors for a team's home stadium.
    
    Includes run factor, HR factor, hit factor, and strikeout factor.
    Coors Field vs Oracle Park can swing totals by 2+ runs.
    
    Args:
        team: Team abbreviation (e.g., "COL", "SF", "NYY")
    
    Returns:
        JSON with park factors and betting impact
    """
    return _get_park_factors(team)


@tool
def analyze_bullpen_usage(team: str) -> str:
    """
    Track bullpen workload, availability, and fatigue levels.
    
    Key for live betting and late-game totals. Shows which arms are 
    rested vs taxed and high-leverage availability.
    
    Args:
        team: Team abbreviation (e.g., "NYY", "LAD")
    
    Returns:
        JSON with bullpen status and betting implications
    """
    return _analyze_bullpen_usage(team)


@tool
def get_mlb_weather_impact(
    home_team: str,
    wind_mph: float = 0,
    wind_direction: str = "calm",
    temp_f: float = 70,
) -> str:
    """
    Calculate weather impact on MLB game totals and home runs.
    
    Factors in wind speed/direction, temperature, and park effects.
    Wind blowing out at Wrigley adds runs; cold weather suppresses scoring.
    
    Args:
        home_team: Home team abbreviation (e.g., "CHC")
        wind_mph: Wind speed in mph (default 0)
        wind_direction: "out", "in", or "calm" (default "calm")
        temp_f: Temperature in Fahrenheit (default 70)
    
    Returns:
        JSON with total adjustment and betting recommendations
    """
    return _get_weather_impact(home_team, wind_mph, wind_direction, temp_f)




# =============================================================================
# AGENT SETUP
# =============================================================================

SYSTEM_PROMPT = """You are JohnnyBets, an expert sports betting analyst assistant. You help identify arbitrage opportunities and value bets across NFL, NBA, NHL, and MLB.

Your capabilities:
1. **Live Odds**: Fetch real-time odds from 10+ sportsbooks
2. **Prediction Markets**: Access Kalshi prediction market data  
3. **Arbitrage Scanner**: Find guaranteed profit opportunities
4. **NFL Prop Alpha**: Contextual player prop analysis with defense profiling
5. **NBA Prop Alpha**: Player props with DvP, pace adjustments, and game script splits
6. **NBA Pace & Tempo**: Game total projections based on pace matchups
7. **NBA Load Management**: B2B splits, fatigue index, DNP risk assessment
8. **NBA Defense Profiles**: DvP rankings by position for prop edges
9. **NBA Referee Tendencies**: Foul rates, FT impact, and total leans
10. **NHL Goalie Alpha**: Goalie props with B2B splits and xGSV%
11. **NHL Analytics**: Team Corsi, xG, and matchup analysis
12. **MLB Pitcher Alpha**: K projections, IP estimates, Stuff+, pitch mix, park factors
13. **MLB Park & Weather**: Stadium factors, wind/temp impact on totals
14. **Bullpen Analyzer**: Relief arm availability and fatigue tracking
15. **X/Twitter Intel**: Real-time breaking news and line movement
16. **Edge Validator**: Anti-slop validation with sharp money analysis

## Key Principles
- Always fetch fresh data before making recommendations
- Never recommend bets on games that have started or start within 15 minutes
- Use the Edge Validator before making final recommendations
- For NBA props, check DvP matchups, pace factors, and load management
- For MLB pitcher props, check K projections, recent form, and park factors
- Distinguish signal from noise in X/Twitter data
- Be conversational and helpful

## Roster Accuracy Rules
- NEVER treat trade rumors as completed transactions - Until a trade is officially announced by the team or league, a player remains on their current team. Trade speculation on X/Twitter is NOT confirmation.
- When in doubt, verify roster status - If you see conflicting information about which team a player is on, explicitly state the uncertainty rather than assuming the rumor is true.
- Player-team associations must come from authoritative sources (official team rosters, league sources, nba_api data) - NOT trade rumors, speculation, or "sources say" posts.
- Flag rumors explicitly - When mentioning trade rumors, always prefix with "rumored" or "speculated" and note the player's CURRENT team.

## Current Session
- Current date: {current_date}
- Current time: {current_time}
- Session started: {session_time}
- Note: All game times from the Odds API are in UTC, convert to ET for users
"""


def get_all_tools():
    """Get all available tools for the agent."""
    return [
        # General / Cross-sport
        fetch_sportsbook_odds,
        fetch_kalshi_markets,
        find_arbitrage_opportunities,
        search_x_twitter,
        get_injury_updates,
        get_line_movement_buzz,
        get_breaking_sports_news,
        validate_betting_edge,
        # NFL
        analyze_player_props,
        get_defense_profile,
        get_player_weather_splits,
        get_player_game_script_splits,
        # NBA
        analyze_nba_player_prop,
        analyze_nba_pace_tempo,
        get_nba_load_management,
        get_nba_defense_profile,
        analyze_nba_refs,
        # NHL
        analyze_goalie_props,
        get_nhl_goalie_profile,
        get_nhl_team_profile,
        analyze_nhl_matchup,
        get_referee_tendencies,
        # MLB
        analyze_pitcher_props,
        get_pitcher_profile,
        get_lineup_vs_pitcher,
        get_mlb_park_factors,
        analyze_bullpen_usage,
        get_mlb_weather_impact,
    ]


def create_agent(model: str = None, reasoning: str = None):
    """
    Create the betting agent with all tools.
    
    Args:
        model: OpenRouter model to use
        reasoning: Reasoning mode (high, medium, low, none)
        
    Returns:
        Tuple of (agent, selected_model) - agent and the actual model used
    """
    selected_model = model or os.getenv("BETTING_AGENT_MODEL", "x-ai/grok-4.1-fast")
    
    extra_body = {}
    if reasoning and reasoning.lower() != "none":
        model_lower = selected_model.lower()
        if any(p in model_lower for p in ['openai/', 'gpt-5', 'x-ai/', 'grok']):
            extra_body["reasoning"] = {"effort": reasoning}
        elif any(p in model_lower for p in ['anthropic/', 'claude']):
            token_map = {"xhigh": 16000, "high": 8000, "medium": 4000, "low": 2000}
            extra_body["reasoning"] = {"max_tokens": token_map.get(reasoning, 4000)}
        elif any(p in model_lower for p in ['gemini', 'qwen']):
            token_map = {"xhigh": 16000, "high": 8000, "medium": 4000, "low": 2000}
            extra_body["reasoning"] = {"max_tokens": token_map.get(reasoning, 4000)}
    
    llm_kwargs = {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "model": selected_model,
        "temperature": 0.7,
        "streaming": True,
    }
    if extra_body:
        llm_kwargs["extra_body"] = extra_body
    
    llm = ChatOpenAI(**llm_kwargs)
    tools = get_all_tools()
    
    return create_react_agent(llm, tools), selected_model


@dataclass
class ChatSession:
    """Manages a chat session with the betting agent."""
    session_id: str = field(default_factory=lambda: str(uuid4()))
    messages: List[BaseMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    model: str = None
    reasoning: str = None
    _agent: Any = field(default=None, repr=False)
    last_tool_calls: List[Dict[str, Any]] = field(default_factory=list)  # Rich tool call data
    
    @property
    def last_tools_used(self) -> List[str]:
        """Backward compatibility: return just tool names."""
        return [tc.get("name", "") for tc in self.last_tool_calls]
    
    def __post_init__(self):
        # Initialize with system prompt using Eastern time
        from zoneinfo import ZoneInfo
        eastern = ZoneInfo("America/New_York")
        now_eastern = datetime.now(eastern)
        
        current_date = now_eastern.strftime('%A, %B %d, %Y')  # e.g., "Thursday, January 29, 2026"
        current_time = now_eastern.strftime('%I:%M %p ET')     # e.g., "06:45 PM ET"
        session_time = now_eastern.strftime('%Y-%m-%d %H:%M:%S ET')
        
        system_prompt = SYSTEM_PROMPT.format(
            current_date=current_date,
            current_time=current_time,
            session_time=session_time
        )
        self.messages = [SystemMessage(content=system_prompt)]
        
        # Create agent and capture actual model used (for trace logging)
        self._agent, actual_model = create_agent(model=self.model, reasoning=self.reasoning)
        self.model = actual_model  # Store actual model for trace logging
    
    async def chat(self, user_input: str) -> str:
        """Send a message and get a response."""
        import time
        self.messages.append(HumanMessage(content=user_input))
        
        response = await self._agent.ainvoke(
            {"messages": self.messages},
            config={"recursion_limit": 50}
        )
        
        # Extract tool calls with inputs and outputs
        # AIMessage contains tool_calls (inputs), ToolMessage contains output
        tool_calls_data = []
        tool_inputs = {}  # Map tool_call_id -> {name, inputs}
        
        for m in response["messages"]:
            # AIMessage with tool_calls contains the inputs
            if isinstance(m, AIMessage) and hasattr(m, "tool_calls") and m.tool_calls:
                for tc in m.tool_calls:
                    tool_id = tc.get("id", "")
                    tool_inputs[tool_id] = {
                        "name": tc.get("name", ""),
                        "inputs": tc.get("args", {}),
                    }
            
            # ToolMessage contains the output
            if isinstance(m, ToolMessage):
                tool_id = getattr(m, "tool_call_id", "")
                tool_name = getattr(m, "name", "") or tool_inputs.get(tool_id, {}).get("name", "unknown")
                inputs = tool_inputs.get(tool_id, {}).get("inputs", {})
                output = m.content if hasattr(m, "content") else ""
                
                tool_calls_data.append({
                    "name": tool_name,
                    "inputs": inputs,
                    "output": output,
                })
        
        self.last_tool_calls = tool_calls_data
        
        ai_messages = [m for m in response["messages"] if isinstance(m, AIMessage)]
        if ai_messages:
            final_response = ai_messages[-1].content
            self.messages.append(AIMessage(content=final_response))
            return final_response
        
        return "I couldn't generate a response. Please try again."
    
    async def chat_stream(self, user_input: str) -> AsyncGenerator[str, None]:
        """Send a message and stream the response."""
        import time
        self.messages.append(HumanMessage(content=user_input))
        
        full_response = ""
        tool_calls_data = []  # Rich tool call data
        active_tools = {}  # Map run_id -> {name, inputs, start_time}
        
        async for event in self._agent.astream_events(
            {"messages": self.messages},
            config={"recursion_limit": 50},
            version="v2"
        ):
            kind = event.get("event")
            
            if kind == "on_chat_model_stream":
                content = event.get("data", {}).get("chunk", {})
                if hasattr(content, "content") and content.content:
                    chunk = content.content
                    full_response += chunk
                    yield chunk
            
            elif kind == "on_tool_start":
                tool_name = event.get("name", "tool")
                run_id = event.get("run_id", "")
                inputs = event.get("data", {}).get("input", {})
                
                # Track active tool with start time
                active_tools[run_id] = {
                    "name": tool_name,
                    "inputs": inputs,
                    "start_time": time.time(),
                }
                yield f"\n\n*Using {tool_name}...*\n\n"
            
            elif kind == "on_tool_end":
                run_id = event.get("run_id", "")
                output = event.get("data", {}).get("output", "")
                
                # Match with start event and calculate latency
                if run_id in active_tools:
                    tool_info = active_tools.pop(run_id)
                    latency_ms = int((time.time() - tool_info["start_time"]) * 1000)
                    
                    tool_calls_data.append({
                        "name": tool_info["name"],
                        "inputs": tool_info["inputs"],
                        "output": str(output) if output else "",
                        "latency_ms": latency_ms,
                    })
        
        # Save the final response and tool calls
        if full_response:
            self.messages.append(AIMessage(content=full_response))
        self.last_tool_calls = tool_calls_data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "model": self.model,
            "reasoning": self.reasoning,
            "message_count": len(self.messages),
            "last_tools_used": self.last_tools_used,  # Backward compat
            "last_tool_calls": self.last_tool_calls,  # Rich data
        }


# Session storage (in-memory for now, will be replaced with DB)
_sessions: Dict[str, ChatSession] = {}


def get_session(session_id: str) -> Optional[ChatSession]:
    """Get a session by ID."""
    return _sessions.get(session_id)


def create_session(model: str = None, reasoning: str = None) -> ChatSession:
    """Create a new chat session."""
    session = ChatSession(model=model, reasoning=reasoning)
    _sessions[session.session_id] = session
    return session


def delete_session(session_id: str) -> bool:
    """Delete a session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False

