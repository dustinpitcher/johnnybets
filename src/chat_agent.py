"""
Interactive Sports Betting Agent with Chat Interface

This agent can:
- Fetch market data from Kalshi and sportsbooks
- Analyze betting opportunities
- Chat interactively to refine strategy
- Save strategies and reports to files
"""
import os
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

# Load environment
load_dotenv("/Users/dustinpitcher/ai_workspace/.env")

# Import our tools
from projects.active.sports_betting.src.tools.kalshi import KalshiClient
from projects.active.sports_betting.src.tools.odds_api import OddsAPIClient
from projects.active.sports_betting.src.tools.x_search import XSearchClient
from projects.active.sports_betting.src.tools.file_tools import (
    save_strategy, save_report, list_saved_files, read_saved_file
)
from projects.active.sports_betting.src.analysis.contextual_props import ContextualPropsAnalyzer, MatchupAnalysis
from projects.active.sports_betting.src.tools.nfl_data import NFLDataFetcher
from projects.active.sports_betting.src.analysis.edge_validator import EdgeValidator, validate_bet

# NHL Tools
from projects.active.sports_betting.src.tools.nhl_data import NHLDataFetcher, GoalieProfile, TeamProfile
from projects.active.sports_betting.src.analysis.goalie_props import GoaliePropsAnalyzer
from projects.active.sports_betting.src.analysis.team_matchup import TeamMatchupAnalyzer
from projects.active.sports_betting.src.tools.nhl_referees import NHLRefereeDatabase


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

@tool
def fetch_kalshi_markets(sport: str = "nfl", market_type: str = "all", limit: int = 50) -> str:
    """
    Fetch prediction market data from Kalshi using official series tickers.
    
    Kalshi organizes sports markets by series:
    - KXSB: Super Bowl winner futures (highest volume, $5-7M+ per team)
    - KXNFLGAME: Single game moneylines ($1-11M volume per game)
    - KXNFLSPREAD: Game spreads
    - KXNFLTOTAL: Game totals (over/under)
    - KXAFC/KXNFC: Conference championships
    
    Args:
        sport: Sport to fetch (nfl, nba, etc.)
        market_type: Type of markets - "futures" (Super Bowl), "games" (single game ML),
                     "spreads", "totals", or "all" for everything
        limit: Maximum markets per category
        
    Returns:
        JSON string of market data with volume and pricing
    """
    import requests
    
    try:
        base_url = 'https://api.elections.kalshi.com/trade-api/v2'
        
        # Define series tickers for each sport/market type
        NFL_SERIES = {
            "futures": ["KXSB"],  # Super Bowl
            "games": ["KXNFLGAME"],  # Single game moneylines
            "spreads": ["KXNFLSPREAD"],
            "totals": ["KXNFLTOTAL"],
            "conference": ["KXAFC", "KXNFC", "KXNFLAFCCHAMP", "KXNFLNFCCHAMP"],
            "divisions": ["KXNFLAFCNORTH", "KXNFLAFCSOUTH", "KXNFLAFCEAST", "KXNFLAFCWEST",
                         "KXNFLNFCNORTH", "KXNFLNFCSOUTH", "KXNFLNFCEAST", "KXNFLNFCWEST"],
        }
        
        NBA_SERIES = {
            "futures": ["KXNBA"],
            "games": ["KXNBAGAME"],
            "conference": ["KXNBAEAST", "KXNBAWEST"],
        }
        
        # Select which series to query based on sport and market_type
        if sport.lower() == "nfl":
            series_map = NFL_SERIES
        elif sport.lower() == "nba":
            series_map = NBA_SERIES
        else:
            return json.dumps({"status": "error", "message": f"Sport '{sport}' not supported. Use 'nfl' or 'nba'."})
        
        # Determine which series to fetch
        if market_type == "all":
            series_to_fetch = []
            for series_list in series_map.values():
                series_to_fetch.extend(series_list)
        elif market_type in series_map:
            series_to_fetch = series_map[market_type]
        else:
            return json.dumps({"status": "error", "message": f"market_type '{market_type}' not recognized. Use: futures, games, spreads, totals, or all"})
        
        # Fetch markets from each series
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
                        "no_bid": m.get("no_bid"),
                        "no_ask": m.get("no_ask"),
                        "volume": vol,
                        "volume_24h": vol_24h,
                        "open_interest": m.get("open_interest", 0),
                        "last_price": m.get("last_price"),
                        "close_time": m.get("close_time"),
                    })
        
        # Sort by volume (highest first)
        all_markets.sort(key=lambda x: x.get("volume", 0), reverse=True)
        
        result = {
            "status": "success",
            "current_time_utc": datetime.now(timezone.utc).isoformat(),
            "sport": sport.upper(),
            "market_type": market_type,
            "series_queried": series_results,
            "total_markets": len(all_markets),
            "markets": all_markets[:30],  # Top 30 by volume
        }
        
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


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
        
        # Summarize for readability
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
def find_arbitrage_opportunities(sport: str = "nfl") -> str:
    """
    Scan sportsbooks for arbitrage opportunities where implied probabilities
    sum to less than 100%, indicating a guaranteed profit opportunity.
    
    Only scans games that have NOT started yet.
    
    Args:
        sport: Sport to scan
        
    Returns:
        JSON string of arbitrage opportunities found
    """
    try:
        client = OddsAPIClient()
        all_games = client.get_odds(sport=sport)
        games = client.filter_future_games(all_games)  # Only future games
        
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
            
            # Calculate implied probabilities
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
def save_betting_strategy(name: str, content: str) -> str:
    """
    Save a betting strategy to a file for future reference.
    
    Args:
        name: Name/title of the strategy
        content: Full strategy description, rules, and conditions
        
    Returns:
        Path to the saved file
    """
    try:
        filepath = save_strategy(name, content)
        return f"Strategy saved to: {filepath}"
    except Exception as e:
        return f"Error saving strategy: {e}"


@tool
def save_analysis_report(content: str, report_type: str = "analysis") -> str:
    """
    Save an analysis report to a file.
    
    Args:
        content: The report content (markdown format recommended)
        report_type: Type of report (analysis, arb, daily, weekly)
        
    Returns:
        Path to the saved file
    """
    try:
        filepath = save_report(content, report_type)
        return f"Report saved to: {filepath}"
    except Exception as e:
        return f"Error saving report: {e}"


@tool
def list_saved_strategies() -> str:
    """
    List all previously saved strategies.
    
    Returns:
        List of saved strategy files
    """
    files = list_saved_files("strategies")
    if not files:
        return "No strategies saved yet."
    return "Saved strategies:\n" + "\n".join(f"  - {f}" for f in sorted(files))


@tool
def read_strategy(filename: str) -> str:
    """
    Read a previously saved strategy.
    
    Args:
        filename: Name of the strategy file to read
        
    Returns:
        Content of the strategy file
    """
    content = read_saved_file(filename, "strategies")
    if content is None:
        return f"Strategy file not found: {filename}"
    return content


@tool
def list_saved_reports() -> str:
    """
    List all previously saved analysis reports.
    
    Returns:
        List of saved report files
    """
    files = list_saved_files("reports")
    if not files:
        return "No reports saved yet."
    return "Saved reports:\n" + "\n".join(f"  - {f}" for f in sorted(files))


@tool
def read_report(filename: str) -> str:
    """
    Read a previously saved analysis report.
    
    Args:
        filename: Name of the report file to read
        
    Returns:
        Content of the report file
    """
    content = read_saved_file(filename, "reports")
    if content is None:
        return f"Report file not found: {filename}"
    return content


@tool
def search_x_twitter(query: str) -> str:
    """
    Search X/Twitter for real-time sports betting intel using Grok.
    Great for finding breaking news, injury updates, insider reports, and line movement chatter.
    
    Args:
        query: What to search for (e.g., "Chiefs injury report", "Bills vs Ravens weather")
        
    Returns:
        Summary of relevant X/Twitter posts and insights
    """
    try:
        client = XSearchClient()
        return client.search(query, context="sports betting analysis")
    except ValueError as e:
        return f"X search unavailable: {e}"
    except Exception as e:
        return f"X search error: {e}"


@tool
def get_injury_updates(team: str) -> str:
    """
    Get the latest injury news and practice reports for a team from X/Twitter.
    
    Args:
        team: Team name (e.g., "Chiefs", "Bills", "Eagles")
        
    Returns:
        Latest injury intel from X
    """
    try:
        client = XSearchClient()
        return client.get_injury_report(team)
    except Exception as e:
        return f"Error fetching injury updates: {e}"


@tool
def get_line_movement_buzz(matchup: str) -> str:
    """
    Search X for sharp money action and line movement discussion.
    
    Args:
        matchup: The game matchup (e.g., "Chiefs vs Ravens", "Bills Eagles")
        
    Returns:
        Sharp betting chatter and line movement intel from X
    """
    try:
        client = XSearchClient()
        return client.get_line_movement_intel(matchup)
    except Exception as e:
        return f"Error fetching line movement: {e}"


@tool  
def get_breaking_sports_news(sport: str = "NFL") -> str:
    """
    Get breaking sports news that could affect betting lines.
    
    Args:
        sport: Sport to check (NFL, NBA, MLB, NHL)
        
    Returns:
        Breaking news summary from X/Twitter
    """
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
    
    This tool uses DATA-DRIVEN defense profiling (not hardcoded) to compare a player's 
    performance against statistically similar defensive profiles.
    
    Uses 3 years of play-by-play data from nflverse to calculate:
    - Standard season averages
    - Performance vs DATA-DRIVEN similar defensive profiles
    - Weather adjustments (wind, temperature)
    - Game script splits (winning, losing, close)
    - Altitude adjustments (for Denver games)
    
    Args:
        player_name: Player name (e.g., "J.Allen", "Josh Allen", "Lamar Jackson")
        position: Position - QB, RB, WR, or TE
        opponent: Opponent team abbreviation (e.g., "DEN", "KC", "BAL")
        passing_yards_line: Current passing yards prop line (for QBs)
        passing_tds_line: Current passing TDs prop line (for QBs)
        rushing_yards_line: Current rushing yards prop line (for RBs)
        wind_mph: Expected game wind speed in mph (optional)
        temp_f: Expected game temperature in Fahrenheit (optional)
        expected_game_script: Expected game flow - "winning", "losing", or "close" (default)
        
    Returns:
        JSON with defense profile, similar teams, weather splits, and recommended actions
        
    Example:
        analyze_player_props("J.Allen", "QB", "DEN", passing_yards_line=265.5, wind_mph=15, temp_f=25)
    """
    try:
        analyzer = ContextualPropsAnalyzer(years=[2023, 2024, 2025])
        
        # Build current lines dict
        current_lines = {}
        if passing_yards_line:
            current_lines["passing_yards"] = passing_yards_line
        if passing_tds_line:
            current_lines["passing_tds"] = passing_tds_line
        if rushing_yards_line:
            current_lines["rushing_yards"] = rushing_yards_line
        
        # Build weather dict if provided
        weather = None
        if wind_mph is not None or temp_f is not None:
            weather = {}
            if wind_mph is not None:
                weather["wind"] = wind_mph
            if temp_f is not None:
                weather["temp"] = temp_f
        
        # Run full analysis
        analysis = analyzer.full_matchup_analysis(
            player_name=player_name,
            position=position.upper(),
            opponent=opponent,
            current_lines=current_lines,
            game_weather=weather,
            expected_script=expected_game_script
        )
        
        # Format results for LLM consumption
        results = {
            "status": "success",
            "player": player_name,
            "position": position,
            "opponent": opponent,
            "analysis_version": "2.0 (data-driven)",
            
            # Opponent defense profile (calculated from data)
            "opponent_defense_profile": {
                "total_plays_analyzed": analysis.opponent_profile.total_plays,
                "sack_rate": analysis.opponent_profile.sack_rate,
                "completion_pct_allowed": analysis.opponent_profile.completion_pct_allowed,
                "avg_air_yards_allowed": analysis.opponent_profile.avg_air_yards_allowed,
                "yards_per_attempt_allowed": analysis.opponent_profile.yards_per_attempt_allowed,
                "style": {
                    "is_aggressive": analysis.opponent_profile.is_aggressive,
                    "is_zone_heavy": analysis.opponent_profile.is_zone_heavy,
                    "is_blitz_heavy": analysis.opponent_profile.is_blitz_heavy,
                }
            },
            
            # Similar defenses (calculated by similarity algorithm)
            "similar_defenses": [
                {
                    "team": team,
                    "similarity": f"{sim:.0%}",
                    "sack_rate": prof.sack_rate,
                    "air_yards_allowed": prof.avg_air_yards_allowed
                }
                for team, sim, prof in analysis.similar_defenses
            ],
            
            # Weather splits
            "weather_splits": analysis.weather_splits,
            
            # Game script splits
            "game_script_splits": analysis.game_script_splits,
            
            # Projections
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
                "reasoning": p.reasoning,
                "adjustments_applied": p.adjustments if hasattr(p, 'adjustments') else [],
                "recommended_action": (
                    "OVER" if p.edge and p.edge > 5 else
                    "UNDER" if p.edge and p.edge < -5 else
                    "PASS"
                )
            }
            results["projections"].append(proj)
        
        return json.dumps(results, indent=2)
        
    except Exception as e:
        import traceback
        return json.dumps({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc(),
            "hint": "Make sure player name is correct (e.g., 'J.Allen' or 'Josh Allen')"
        }, indent=2)


@tool
def get_defense_profile(team: str) -> str:
    """
    Get a data-driven defensive profile for an NFL team.
    
    Calculates from actual play-by-play data:
    - Sack rate (blitz indicator)
    - Completion % allowed
    - Average air yards allowed (deep vs short coverage)
    - Yards per attempt allowed
    - Style classification (aggressive, zone-heavy, blitz-heavy)
    
    Args:
        team: Team abbreviation (e.g., "DEN", "KC", "BUF")
        
    Returns:
        JSON with defensive metrics and style classification
        
    Example:
        get_defense_profile("DEN")
    """
    try:
        fetcher = NFLDataFetcher(years=[2023, 2024, 2025])
        profile = fetcher.calculate_defense_profile(team, tuple([2023, 2024, 2025]))
        
        # Find similar teams
        similar = fetcher.find_similar_defenses(team, top_n=5)
        
        return json.dumps({
            "status": "success",
            "team": team,
            "total_pass_plays_analyzed": profile.total_plays,
            "metrics": {
                "sack_rate_pct": profile.sack_rate,
                "completion_pct_allowed": profile.completion_pct_allowed,
                "avg_air_yards_allowed": profile.avg_air_yards_allowed,
                "yards_per_attempt_allowed": profile.yards_per_attempt_allowed,
                "pressure_proxy": profile.pressure_proxy,
            },
            "style_classification": {
                "is_aggressive_man": profile.is_aggressive,
                "is_zone_heavy": profile.is_zone_heavy,
                "is_blitz_heavy": profile.is_blitz_heavy,
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
    """
    Get player performance splits by weather conditions.
    
    Shows how a player performs in:
    - High wind (15+ mph)
    - Low wind (< 10 mph)
    - Cold weather (< 40°F)
    
    Args:
        player_name: Player name (e.g., "J.Allen", "Josh Allen")
        position: Position - QB, RB, WR, TE
        
    Returns:
        JSON with performance by weather condition
    """
    try:
        fetcher = NFLDataFetcher(years=[2023, 2024, 2025])
        splits = fetcher.get_player_weather_splits(player_name, position)
        
        return json.dumps({
            "status": "success",
            "player": player_name,
            "position": position,
            "weather_splits": splits
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def get_player_game_script_splits(player_name: str, position: str = "QB") -> str:
    """
    Get player performance splits by game script (winning, losing, close).
    
    Key insight: RBs get more carries when winning (protect lead), 
    QBs throw more when losing (catch up).
    
    Args:
        player_name: Player name (e.g., "J.Allen", "James Cook")
        position: Position - QB or RB
        
    Returns:
        JSON with performance by game script scenario
    """
    try:
        fetcher = NFLDataFetcher(years=[2023, 2024, 2025])
        splits = fetcher.get_player_game_script_splits(player_name, position)
        
        return json.dumps({
            "status": "success",
            "player": player_name,
            "position": position,
            "game_script_splits": splits,
            "insight": (
                "RBs typically get more volume when team is winning (running out clock). "
                "QBs typically throw more when trailing (catch-up mode)."
            )
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
    """
    **ANTI-SLOP VALIDATOR** - Use this AFTER analysis to validate if a bet has real edge.
    
    This tool checks:
    1. Mathematical +EV given the juice
    2. Whether you're on the PUBLIC side (often a fade signal)
    3. Historical ATS for the spot type (playoff favorites lose money!)
    4. Weather narrative traps (cold/snow effects are often priced in)
    
    ALWAYS use this before making final recommendations to avoid AI slop.
    
    Args:
        bet_type: "spread", "total", or "prop"
        is_favorite: True if betting the favorite (spreads only)
        is_playoff: True if playoff game (important - favorites cover <45% in playoffs!)
        is_home: True if betting home team
        public_pct: % of public money on this side (>60% = public side = warning)
        weather_condition: "cold_35F", "wind_15mph", "snow", "rain" if applicable
        juice: The vig (e.g., -110, -120)
        historical_hit_rate: For totals - the actual hit rate from your data analysis
        projection: For props - your calculated projection
        line: For props - the betting line
        is_over: For totals/props - True if betting OVER
        sample_size: Number of games in your prop analysis sample
        
    Returns:
        Markdown report with edge validation and recommendation
    """
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
            if historical_hit_rate is None:
                return "ERROR: For totals, you must provide historical_hit_rate from your data analysis"
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
                return "ERROR: For props, you must provide both projection and line"
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
            return f"ERROR: Unknown bet_type '{bet_type}'. Use 'spread', 'total', or 'prop'"
        
        return result.to_markdown()
        
    except Exception as e:
        return f"ERROR validating edge: {str(e)}"


# ============================================================================
# NHL TOOLS
# ============================================================================

@tool
def analyze_goalie_props(
    goalie_name: str,
    opponent: str,
    is_back_to_back: bool = False,
    expected_shots: float = None,
    saves_line: float = None,
    goals_against_line: float = None
) -> str:
    """
    Analyze NHL goalie props using advanced metrics (Goalie Alpha Tool).
    
    This tool provides:
    - Save % vs shot volume analysis (auto-under on <25 shot games)
    - Back-to-back performance splits (goalies drop 2-3% SV% on B2B)
    - xG Save % (fades "lucky" goalies overperforming expected)
    - Opponent shot quality analysis
    
    Args:
        goalie_name: Goalie name (e.g., "Shesterkin", "Igor Shesterkin")
        opponent: Opponent team abbreviation (e.g., "TOR", "BOS", "NYR")
        is_back_to_back: True if goalie played yesterday (critical for fade signal)
        expected_shots: Expected shots on goal (if known from projections)
        saves_line: Current saves prop line for edge calculation
        goals_against_line: Current goals against prop line for edge calculation
        
    Returns:
        JSON with goalie profile, projections, risk factors, and recommendations
        
    Example:
        analyze_goalie_props("Shesterkin", "TOR", is_back_to_back=True, saves_line=28.5)
    """
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
        import traceback
        return json.dumps({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc(),
            "hint": "Check goalie name spelling and opponent abbreviation"
        }, indent=2)


@tool
def get_nhl_team_profile(team: str) -> str:
    """
    Get NHL team analytics profile with Corsi, xG, and possession metrics.
    
    Returns team-level advanced stats including:
    - Corsi% (shot attempt share - possession proxy)
    - Expected Goals For/Against per game
    - High-Danger Chances % 
    - Goals For/Against per game
    - Power Play and Penalty Kill %
    - Team style classification
    
    Args:
        team: Team abbreviation (e.g., "NYR", "TOR", "BOS", "COL")
        
    Returns:
        JSON with team analytics profile
        
    Example:
        get_nhl_team_profile("NYR")
    """
    try:
        fetcher = NHLDataFetcher()
        profile = fetcher.get_team_profile(team)
        
        if not profile:
            return json.dumps({
                "status": "error",
                "message": f"Team not found: {team}"
            })
        
        return json.dumps({
            "status": "success",
            "team": profile.team,
            "games_played": profile.games_played,
            "possession": {
                "corsi_for_per_game": profile.corsi_for_per_game,
                "corsi_against_per_game": profile.corsi_against_per_game,
                "corsi_pct": profile.corsi_pct,
            },
            "expected_goals": {
                "xg_for_per_game": profile.xg_for_per_game,
                "xg_against_per_game": profile.xg_against_per_game,
                "xg_diff_per_game": profile.xg_diff_per_game,
            },
            "high_danger": {
                "hd_chances_for": profile.hd_chances_for,
                "hd_chances_against": profile.hd_chances_against,
                "hd_pct": profile.hd_pct,
            },
            "goals": {
                "goals_for_per_game": profile.goals_for_per_game,
                "goals_against_per_game": profile.goals_against_per_game,
            },
            "special_teams": {
                "power_play_pct": profile.pp_pct,
                "penalty_kill_pct": profile.pk_pct,
            },
            "style": profile.get_style(),
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def analyze_nhl_matchup(home_team: str, away_team: str) -> str:
    """
    Analyze NHL team matchup with Corsi/xG edge identification.
    
    Compares two teams and identifies edges in:
    - Possession (Corsi%)
    - Expected Goals differential
    - High-Danger Chances
    - Special Teams
    
    Also projects total goals and provides spread lean.
    
    NOTE: This is a scaffold implementation - full analysis coming in future update.
    
    Args:
        home_team: Home team abbreviation (e.g., "NYR")
        away_team: Away team abbreviation (e.g., "TOR")
        
    Returns:
        JSON with matchup analysis, edges, and projections
        
    Example:
        analyze_nhl_matchup("NYR", "TOR")
    """
    try:
        analyzer = TeamMatchupAnalyzer()
        analysis = analyzer.analyze_matchup(home_team, away_team)
        return analyzer.to_json(analysis)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def get_referee_tendencies(referee_1: str = None, referee_2: str = None) -> str:
    """
    Get NHL referee penalty and total tendencies for betting analysis.
    
    Analyzes referee tendencies including:
    - Penalties per game (tight vs loose callers)
    - Over/under rate (do their games go over?)
    - Power play frequency
    
    Key insight: Some refs consistently call 8-9 penalties/game (overs hit 58%+ with these crews).
    
    NOTE: This is a scaffold implementation with sample data. 
    Full referee database integration coming in future update.
    
    Args:
        referee_1: First referee name (optional)
        referee_2: Second referee name (optional)
        
    Returns:
        JSON with referee profiles and betting recommendations
        
    Example:
        get_referee_tendencies("Wes McCauley", "Chris Rooney")
    """
    try:
        db = NHLRefereeDatabase()
        analysis = db.analyze_game_refs(referee_1, referee_2)
        return json.dumps(analysis, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


@tool
def get_nhl_goalie_profile(goalie_name: str) -> str:
    """
    Get detailed goalie profile with save %, xG save %, and B2B splits.
    
    Returns comprehensive goalie metrics:
    - Save % and xG Save % (expected based on shot quality)
    - Luck factor (actual - expected, positive = overperforming)
    - High-danger save %
    - Shots against per game (workload)
    - Back-to-back performance splits
    
    Args:
        goalie_name: Goalie name (e.g., "Shesterkin", "Hellebuyck")
        
    Returns:
        JSON with goalie profile and betting-relevant metrics
        
    Example:
        get_nhl_goalie_profile("Shesterkin")
    """
    try:
        fetcher = NHLDataFetcher()
        profile = fetcher.get_goalie_profile(goalie_name)
        
        if not profile:
            return json.dumps({
                "status": "error",
                "message": f"Goalie not found: {goalie_name}"
            })
        
        return json.dumps({
            "status": "success",
            "goalie": profile.name,
            "team": profile.team,
            "games_played": profile.games_played,
            "save_metrics": {
                "save_pct": profile.save_pct,
                "xg_save_pct": profile.xg_save_pct,
                "luck_factor": profile.luck_factor,
                "is_overperforming": profile.is_overperforming(),
                "high_danger_sv_pct": profile.high_danger_sv_pct,
            },
            "workload": {
                "shots_against_per_game": profile.shots_against_per_game,
                "is_high_volume": profile.is_high_volume_goalie(),
            },
            "rest_splits": {
                "b2b_games": profile.b2b_games,
                "b2b_save_pct": profile.b2b_save_pct,
                "rested_games": profile.rested_games,
                "rested_save_pct": profile.rested_save_pct,
                "b2b_penalty": profile.get_b2b_penalty(),
            },
            "betting_notes": [
                f"Luck factor {profile.luck_factor:+.3f}: {'FADE - overperforming xG' if profile.luck_factor > 0.015 else 'BUY - underperforming xG' if profile.luck_factor < -0.015 else 'Neutral'}",
                f"B2B penalty: {profile.get_b2b_penalty()*100:.1f}% SV% drop" if profile.b2b_games > 0 else "No B2B data",
            ]
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)


# ============================================================================
# AGENT SETUP
# ============================================================================

SYSTEM_PROMPT = """You are an expert sports betting analyst assistant. You help identify arbitrage opportunities and value bets across NFL and NHL.

Your capabilities:
1. **Fetch Market Data**: Use fetch_kalshi_markets and fetch_sportsbook_odds to get current odds
2. **Find Arbs**: Use find_arbitrage_opportunities to scan for guaranteed profit opportunities
3. **NFL Prop Alpha v2.0 (Data-Driven)**: A suite of tools for deep NFL prop analysis:
   - `analyze_player_props`: Full matchup analysis with defense profile, weather, game script
   - `get_defense_profile`: Get data-driven defensive metrics for any NFL team
   - `get_player_weather_splits`: How a player performs in wind, cold, etc.
   - `get_player_game_script_splits`: How a player performs when winning vs losing
4. **🏒 NHL Goalie Alpha**: Advanced goalie prop analysis tools:
   - `analyze_goalie_props`: Full goalie analysis with B2B splits, xGSV%, opponent quality
   - `get_nhl_goalie_profile`: Detailed goalie metrics (SV%, xGSV%, luck factor, B2B penalty)
   - Key insights: Goalies drop 2-3% SV% on back-to-backs; fade goalies with high luck factor
5. **🏒 NHL Corsi/xG Engine**: Team-level matchup analysis:
   - `get_nhl_team_profile`: Team Corsi%, xG, high-danger chances, special teams
   - `analyze_nhl_matchup`: Head-to-head matchup with edge identification
   - `get_referee_tendencies`: Referee penalty/over tendencies (scaffold - limited data)
6. **🚨 ANTI-SLOP VALIDATOR**: ALWAYS use `validate_betting_edge` BEFORE making final recommendations:
   - Calculates if you have actual +EV given the juice
   - Detects if you're on the PUBLIC side (often a fade signal)
   - Checks historical ATS for spot types (playoff favorites cover only 44.7%!)
   - Flags weather/narrative traps that books have already priced in
7. **X/Twitter Intel**: Use search_x_twitter, get_injury_updates, get_line_movement_buzz, and get_breaking_sports_news to get real-time information from X that could affect lines
8. **Analyze**: Compare prediction market prices with sportsbook lines to find value
9. **Save Work**: Use save_betting_strategy and save_analysis_report to persist findings

## Sentiment Analysis Guidelines

1. **X/Twitter sentiment is DATA, not advice** - Report sentiment objectively as information to analyze, never adopt trending opinions as your own recommendations.

2. **Heavy public consensus requires dual-hypothesis analysis** - When you detect strong public sentiment (70%+ one direction), investigate BOTH:
   - Hypothesis A (Fade): The public is wrong and there's value on the other side
   - Hypothesis B (Wisdom): The public has correctly identified something
   Weigh evidence for each before making a recommendation.

3. **Distinguish signal from noise**:
   - SIGNAL: Verified beat reporters, official team accounts, known insiders, injury reports, weather data
   - NOISE: Fan hype, emotional takes, "lock of the week" claims, memes, hot takes
   Only actionable intel should influence analysis.

4. **Reverse Line Movement (RLM) = Sharp Action** - When the betting line moves AGAINST public sentiment, this indicates sharp/professional money on the other side. Flag RLM as a high-value signal.

## Roster Accuracy Rules

1. **NEVER treat trade rumors as completed transactions** - Until a trade is officially announced by the team or league, a player remains on their current team. Trade speculation on X/Twitter is NOT confirmation.

2. **When in doubt, verify roster status** - If you see conflicting information about which team a player is on, explicitly state the uncertainty rather than assuming the rumor is true.

3. **Player-team associations must come from authoritative sources**:
   - AUTHORITATIVE: Official team rosters, NBA/NFL/MLB/NHL official sources, nba_api data
   - NOT AUTHORITATIVE: Trade rumors, speculation, "sources say" posts, fan accounts

4. **Flag rumors explicitly** - When mentioning trade rumors, always prefix with "rumored" or "speculated" and note the player's CURRENT team.

## Key Concepts

### General
- **Line Freezes**: When a book holds a line despite action, indicating strong opinion
- **Implied Probability**: Converting odds to probabilities for comparison
- **Situational Correlations**: Weather, injuries, matchups affecting outcomes
- **Sharp Money**: Following professional bettor action via line movement

### NFL Specific
- **Key Numbers**: NFL spreads of 3, 7, 10, 14 are critical due to scoring patterns
- **Contextual Props (Prop Alpha)**: Comparing player performance vs similar defensive profiles, not just season averages. E.g., "Josh Allen vs blitz-heavy man coverage" rather than "Josh Allen season average"

### NHL Specific
- **Goalie B2B Fade**: Goalies drop 2-3% SV% on back-to-backs. Example: Shesterkin B2B unders hit 62%
- **xG Save %**: Expected save % based on shot quality. Luck factor = actual SV% - xGSV%. Fade goalies with high luck factor (overperforming).
- **Shot Volume**: Games with <25 shots = auto-under on goalie saves
- **Corsi%**: Shot attempt share (possession proxy). Team with higher Corsi% controls pace.
- **High-Danger Chances**: Shots from the slot. HD% indicates quality chance generation.
- **Referee Tendencies**: Some refs consistently call 8-9 penalties/game (overs hit 58%+ with high-penalty crews)

## Analysis Workflow

### General
1. Always fetch fresh data before making recommendations, don't recommend betting in progress games or games that start in 15 minutes or less. 
2. Check X for breaking news, injury updates, and sharp money chatter
3. Separate signal (insider info) from noise (fan sentiment)
4. If heavy public consensus detected, run dual-hypothesis analysis
5. Look for RLM as indicator of sharp disagreement with public
6. Compare Kalshi parlay prices with sportsbook SGP pricing
7. Identify where prediction markets disagree with traditional books

### NFL Workflow
8. **For player props**: Use analyze_player_props to get contextual projections and find edges where lines deviate from matchup-specific performance

### NHL Workflow
9. **For goalie props**: Use `analyze_goalie_props` with B2B flag and opponent:
   - Check if goalie is on a back-to-back (massive fade signal)
   - Check luck factor (xGSV% vs actual SV%)
   - Check opponent shot volume tendencies
10. **For game totals**: Use `analyze_nhl_matchup` for Corsi/xG edges, then check `get_referee_tendencies` if refs are known
11. **For moneylines/spreads**: Use team profiles to identify Corsi% and xG differential edges

### Validation (CRITICAL)
12. **🚨 VALIDATE BEFORE RECOMMENDING**: Before making ANY final bet recommendation, use `validate_betting_edge` to:
   - Confirm you have mathematical +EV (not just a good narrative)
   - Check if you're on the public side (>60% = warning)
   - Verify historical ATS for the spot type
   - Avoid weather/narrative traps that are already priced in

## Common Traps to Avoid

### NFL Traps
1. **Playoff Favorites**: Cover only 44.7% ATS. Default to considering the underdog.
2. **"Cold = Under"**: Weather impacts are ALREADY PRICED IN. Cold only drops totals by 1-2 points.
3. **Public Side**: When 70%+ of money is on one side but line isn't moving, books WANT that money.
4. **Narrative-Heavy Analysis**: "Dome QB in cold" sounds smart but lacks edge. Data > stories.

### NHL Traps
5. **Trusting Hot Goalies**: A goalie with .935 SV% but .910 xGSV% is overperforming (luck). Fade, don't chase.
6. **Ignoring B2B**: Never bet over on a B2B goalie without checking their historical B2B splits.
7. **Low Shot Games**: Betting over on goalie saves in games projected for <28 shots is a losing play.
8. **Assuming Possession = Goals**: High Corsi% teams don't always score. Check xG and finishing rates.

Be conversational and helpful. Ask clarifying questions if needed. Offer to save strategies when you develop actionable plans."""


def create_betting_agent(model: str = None, reasoning: str = None):
    """
    Create the interactive betting agent with tools.
    
    Args:
        model: OpenRouter model to use. Defaults to env var or gemini-3-pro-preview
        reasoning: Reasoning mode - "high", "medium", "low", or None (disabled)
                   See: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
        
    Available models for comparison:
        - "google/gemini-3-pro-preview:online"  (has real-time search)
        - "google/gemini-3-pro-preview"         (offline, no search)
        - "anthropic/claude-opus-4.5"           (offline, strong reasoning with max_tokens)
        - "openai/gpt-5.2"                      (offline, supports effort levels)
        - "x-ai/grok-4"                         (offline, supports effort levels)
        
    Reasoning support by provider:
        - OpenAI (GPT-5, o-series): effort levels (xhigh, high, medium, low, minimal, none)
        - Grok: effort levels
        - Anthropic: max_tokens for reasoning budget
        - Gemini thinking models: max_tokens
    """
    # Allow model override via env var or parameter
    # Default: Grok 4.1 Fast - great for betting analysis with reasoning support
    selected_model = model or os.getenv("BETTING_AGENT_MODEL", "x-ai/grok-4.1-fast")
    
    print(f"🤖 Using model: {selected_model}")
    if reasoning:
        print(f"🧠 Reasoning mode: {reasoning}")
    
    # Build extra_body for reasoning if enabled
    # See: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens
    extra_body = {}
    if reasoning and reasoning.lower() != "none":
        # Determine reasoning config based on model provider
        model_lower = selected_model.lower()
        
        if any(p in model_lower for p in ['openai/', 'gpt-5', 'gpt-4', 'o1', 'o3', 'x-ai/', 'grok']):
            # OpenAI and Grok use effort levels
            extra_body["reasoning"] = {"effort": reasoning}
        elif any(p in model_lower for p in ['anthropic/', 'claude']):
            # Anthropic uses max_tokens for reasoning budget
            token_map = {"xhigh": 16000, "high": 8000, "medium": 4000, "low": 2000, "minimal": 1000}
            max_tokens = token_map.get(reasoning, 4000)
            extra_body["reasoning"] = {"max_tokens": max_tokens}
        elif any(p in model_lower for p in ['gemini', 'qwen']):
            # Gemini and Qwen use max_tokens
            token_map = {"xhigh": 16000, "high": 8000, "medium": 4000, "low": 2000, "minimal": 1000}
            max_tokens = token_map.get(reasoning, 4000)
            extra_body["reasoning"] = {"max_tokens": max_tokens}
        else:
            # Default to effort for unknown models
            extra_body["reasoning"] = {"effort": reasoning}
    
    # Build LLM kwargs
    llm_kwargs = {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "model": selected_model,
        "temperature": 0.7,
    }
    if extra_body:
        llm_kwargs["extra_body"] = extra_body
    
    llm = ChatOpenAI(**llm_kwargs)
    
    tools = [
        # Market data
        fetch_kalshi_markets,
        fetch_sportsbook_odds,
        find_arbitrage_opportunities,
        # NFL Prop Alpha v2.0 - data-driven contextual player analysis
        analyze_player_props,
        get_defense_profile,
        get_player_weather_splits,
        get_player_game_script_splits,
        # NHL Analytics Tools
        analyze_goalie_props,      # Goalie micro-splits (B2B, xGSV%, shot volume)
        get_nhl_goalie_profile,    # Detailed goalie metrics
        get_nhl_team_profile,      # Team Corsi/xG profile
        analyze_nhl_matchup,       # Team vs team matchup analysis
        get_referee_tendencies,    # Referee penalty/over tendencies (scaffold)
        # ANTI-SLOP: Edge validation (use AFTER analysis)
        validate_betting_edge,
        # X/Twitter search (real-time intel)
        search_x_twitter,
        get_injury_updates,
        get_line_movement_buzz,
        get_breaking_sports_news,
        # File management
        save_betting_strategy,
        save_analysis_report,
        list_saved_strategies,
        read_strategy,
        list_saved_reports,
        read_report,
    ]
    
    agent = create_react_agent(llm, tools)
    return agent


# ============================================================================
# CHAT INTERFACE
# ============================================================================

def get_bootstrap_context() -> str:
    """Generate dynamic context for the agent including current time."""
    from datetime import timezone as tz
    now = datetime.now()
    utc_now = datetime.now(tz.utc)
    
    return f"""
## Current Context
- **Current Date**: {now.strftime('%A, %B %d, %Y')}
- **Current Local Time**: {now.strftime('%I:%M %p')} (user's local timezone)
- **Current UTC Time**: {utc_now.strftime('%Y-%m-%dT%H:%M:%SZ')}
- **Note**: All game times from the Odds API are in UTC. Convert appropriately.
- **Session Started**: {utc_now.strftime('%H:%M')} UTC

## Tool Behavior
- **Sportsbook odds tools** automatically filter out games that have already started or start within 15 minutes.
- Only bettable future games are returned by the tools.
- Do NOT recommend bets on any game where commence_time is before current UTC time.
"""


class ChatSession:
    """Manages an interactive chat session with the betting agent."""
    
    def __init__(self, model: str = None, reasoning: str = None):
        self.agent = create_betting_agent(model=model, reasoning=reasoning)
        # Bootstrap with system prompt + dynamic context (current time, etc.)
        full_system_prompt = SYSTEM_PROMPT + get_bootstrap_context()
        self.messages: List[BaseMessage] = [SystemMessage(content=full_system_prompt)]
    
    async def chat(self, user_input: str) -> str:
        """Send a message and get a response."""
        self.messages.append(HumanMessage(content=user_input))
        
        # Set recursion_limit to 50 for deep research queries
        response = await self.agent.ainvoke(
            {"messages": self.messages},
            config={"recursion_limit": 50}
        )
        
        # Extract the final response
        ai_messages = [m for m in response["messages"] if isinstance(m, AIMessage)]
        if ai_messages:
            final_response = ai_messages[-1].content
            self.messages.append(AIMessage(content=final_response))
            return final_response
        
        return "I couldn't generate a response. Please try again."


async def run_chat(model: str = None, reasoning: str = None):
    """Run the interactive chat loop."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    
    console = Console()
    session = ChatSession(model=model, reasoning=reasoning)
    
    console.print(Panel.fit(
        "[bold green]Sports Betting Agent[/bold green]\n"
        "Chat with me about betting strategies, arbitrage, and market analysis.\n"
        "Type 'quit' to exit, 'scan' to run a quick arb scan, or 'refresh' to fetch new data.",
        title="Welcome"
    ))
    
    # Initial greeting
    greeting = await session.chat(
        "Give me a brief greeting and ask what sport or analysis I'd like to focus on today. "
        "Mention that you can fetch live odds, find arbs, and save strategies."
    )
    console.print(Markdown(greeting))
    console.print()
    
    while True:
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ("quit", "exit", "q"):
                console.print("[yellow]Goodbye! Happy betting.[/yellow]")
                break
            
            # Quick commands
            if user_input.lower() == "scan":
                user_input = "Run an arbitrage scan on NFL games and show me any opportunities."
            elif user_input.lower() == "refresh":
                user_input = "Fetch fresh NFL odds from both Kalshi and the sportsbooks."
            
            console.print("[dim]Thinking...[/dim]")
            response = await session.chat(user_input)
            console.print()
            console.print(Markdown(response))
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]")


if __name__ == "__main__":
    asyncio.run(run_chat())

