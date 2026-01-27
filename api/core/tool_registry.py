"""
JohnnyBets Tool Registry

Central configuration for all agent tools. Each tool is a branded feature
with status management for free/premium/roadmap/idea classification.

Status Types:
- free: Included for all users (green badge)
- premium: Requires subscription - future (gold badge + lock)
- roadmap: Planned, in development (blue badge + ETA)
- idea: Under consideration (gray badge + vote button)
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


class ToolStatus(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    ROADMAP = "roadmap"
    IDEA = "idea"


class ToolCategory(str, Enum):
    GENERAL = "general"
    NFL = "nfl"
    NBA = "nba"
    NHL = "nhl"
    MLB = "mlb"


@dataclass
class Tool:
    """Represents a single tool/feature in the registry."""
    id: str
    name: str
    description: str
    category: ToolCategory
    status: ToolStatus
    icon: str
    sports: List[str]
    # For agent binding
    function_name: Optional[str] = None
    # For roadmap items
    eta: Optional[str] = None
    # For premium items (future)
    price_tier: Optional[str] = None
    # Voting for ideas
    votes: int = 0
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "status": self.status.value,
            "icon": self.icon,
            "sports": self.sports,
            "function_name": self.function_name,
            "eta": self.eta,
            "price_tier": self.price_tier,
            "votes": self.votes,
        }


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

TOOLS: Dict[str, Tool] = {
    # -------------------------------------------------------------------------
    # GENERAL TOOLS (All Sports)
    # -------------------------------------------------------------------------
    "fetch_sportsbook_odds": Tool(
        id="fetch_sportsbook_odds",
        name="Live Odds",
        description="Real-time odds from 10+ sportsbooks including DraftKings, FanDuel, BetMGM, and more. Automatically filters out started games.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.FREE,
        icon="chart-line",
        sports=["nfl", "nhl", "mlb", "nba"],
        function_name="fetch_sportsbook_odds",
    ),
    "fetch_kalshi_markets": Tool(
        id="fetch_kalshi_markets",
        name="Prediction Markets",
        description="Kalshi prediction market data for Super Bowl futures, game moneylines, spreads, and totals with volume and pricing.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.FREE,
        icon="crystal-ball",
        sports=["nfl", "nba"],
        function_name="fetch_kalshi_markets",
    ),
    "find_arbitrage_opportunities": Tool(
        id="find_arbitrage_opportunities",
        name="Arbitrage Scanner",
        description="Scan sportsbooks for guaranteed profit opportunities where implied probabilities sum to less than 100%.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.FREE,
        icon="magnifying-glass-dollar",
        sports=["nfl", "nhl", "mlb", "nba"],
        function_name="find_arbitrage_opportunities",
    ),
    "search_x_twitter": Tool(
        id="search_x_twitter",
        name="X/Twitter Intel",
        description="Real-time sports betting intelligence from X. Find breaking news, injury updates, insider reports, and line movement chatter.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.FREE,
        icon="twitter",
        sports=["nfl", "nhl", "mlb", "nba"],
        function_name="search_x_twitter",
    ),
    "get_injury_updates": Tool(
        id="get_injury_updates",
        name="Injury Reports",
        description="Latest injury news and practice reports for any team from X/Twitter sources.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.FREE,
        icon="bandage",
        sports=["nfl", "nhl", "mlb", "nba"],
        function_name="get_injury_updates",
    ),
    "get_line_movement_buzz": Tool(
        id="get_line_movement_buzz",
        name="Line Movement Intel",
        description="Sharp money action and line movement discussion from X for any matchup.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.FREE,
        icon="trending-up",
        sports=["nfl", "nhl", "mlb", "nba"],
        function_name="get_line_movement_buzz",
    ),
    "get_breaking_sports_news": Tool(
        id="get_breaking_sports_news",
        name="Breaking News",
        description="Breaking sports news that could affect betting lines for any sport.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.FREE,
        icon="newspaper",
        sports=["nfl", "nhl", "mlb", "nba"],
        function_name="get_breaking_sports_news",
    ),
    "validate_betting_edge": Tool(
        id="validate_betting_edge",
        name="Edge Validator",
        description="Anti-slop validator that checks for real +EV, public side warnings, sharp money analysis, and CLV before recommending bets.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.FREE,
        icon="shield-check",
        sports=["nfl", "nba", "nhl", "mlb"],
        function_name="validate_betting_edge",
    ),
    "save_betting_strategy": Tool(
        id="save_betting_strategy",
        name="Save Strategy",
        description="Save betting strategies to files for future reference and tracking.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.FREE,
        icon="floppy-disk",
        sports=["nfl", "nhl", "mlb", "nba"],
        function_name="save_betting_strategy",
    ),
    "save_analysis_report": Tool(
        id="save_analysis_report",
        name="Save Report",
        description="Save analysis reports in markdown format for documentation.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.FREE,
        icon="file-text",
        sports=["nfl", "nhl", "mlb", "nba"],
        function_name="save_analysis_report",
    ),
    
    # -------------------------------------------------------------------------
    # NFL TOOLS
    # -------------------------------------------------------------------------
    "analyze_player_props": Tool(
        id="analyze_player_props",
        name="Prop Alpha",
        description="Contextual player prop analysis using 3 years of play-by-play data. Compares performance vs similar defensive profiles, weather conditions, and game scripts.",
        category=ToolCategory.NFL,
        status=ToolStatus.FREE,
        icon="user-chart",
        sports=["nfl"],
        function_name="analyze_player_props",
    ),
    "get_defense_profile": Tool(
        id="get_defense_profile",
        name="Defense Profiler",
        description="Data-driven defensive profile for any NFL team. Shows sack rate, completion % allowed, air yards, and style classification.",
        category=ToolCategory.NFL,
        status=ToolStatus.FREE,
        icon="shield",
        sports=["nfl"],
        function_name="get_defense_profile",
    ),
    "get_player_weather_splits": Tool(
        id="get_player_weather_splits",
        name="Weather Splits",
        description="Player performance splits by weather conditions including high wind, low wind, and cold weather games.",
        category=ToolCategory.NFL,
        status=ToolStatus.FREE,
        icon="cloud-sun",
        sports=["nfl"],
        function_name="get_player_weather_splits",
    ),
    "get_player_game_script_splits": Tool(
        id="get_player_game_script_splits",
        name="Game Script Splits",
        description="Player performance when team is winning, losing, or in close games. Key insight: RBs get more volume when winning.",
        category=ToolCategory.NFL,
        status=ToolStatus.FREE,
        icon="chart-bar",
        sports=["nfl"],
        function_name="get_player_game_script_splits",
    ),
    
    # -------------------------------------------------------------------------
    # NBA TOOLS
    # -------------------------------------------------------------------------
    "analyze_nba_player_prop": Tool(
        id="analyze_nba_player_prop",
        name="NBA Prop Alpha",
        description="NBA player prop analysis with Defense vs Position (DvP) rankings, pace adjustments, usage rate, game script splits, and recent form weighting.",
        category=ToolCategory.NBA,
        status=ToolStatus.FREE,
        icon="basketball",
        sports=["nba"],
        function_name="analyze_nba_player_prop",
    ),
    "analyze_nba_pace_tempo": Tool(
        id="analyze_nba_pace_tempo",
        name="Pace & Tempo Analyzer",
        description="Game total projections based on pace matchups. Identifies track meets (both fast) vs grinds (both slow). Totals can swing 5-10 points on pace mismatches.",
        category=ToolCategory.NBA,
        status=ToolStatus.FREE,
        icon="chart-line",
        sports=["nba"],
        function_name="analyze_nba_pace_tempo",
    ),
    "get_nba_load_management": Tool(
        id="get_nba_load_management",
        name="Load Management Tracker",
        description="Track rest days, B2B splits, fatigue index, and DNP risk. Critical for props when stars may sit or see reduced minutes.",
        category=ToolCategory.NBA,
        status=ToolStatus.FREE,
        icon="battery-half",
        sports=["nba"],
        function_name="get_nba_load_management",
    ),
    "get_nba_defense_profile": Tool(
        id="get_nba_defense_profile",
        name="NBA Defense Profile",
        description="Team defensive metrics with DvP rankings by position. Shows DEF rating, opponent FG%, blocks, steals, and style classification.",
        category=ToolCategory.NBA,
        status=ToolStatus.FREE,
        icon="shield",
        sports=["nba"],
        function_name="get_nba_defense_profile",
    ),
    "analyze_nba_refs": Tool(
        id="analyze_nba_refs",
        name="NBA Referee Tendencies",
        description="Referee crew foul rates, FT impact, and total leans. Some refs = unders (let them play), others = overs (whistle-happy).",
        category=ToolCategory.NBA,
        status=ToolStatus.FREE,
        icon="whistle",
        sports=["nba"],
        function_name="analyze_nba_refs",
    ),
    
    # -------------------------------------------------------------------------
    # NHL TOOLS
    # -------------------------------------------------------------------------
    "analyze_goalie_props": Tool(
        id="analyze_goalie_props",
        name="Goalie Alpha",
        description="NHL goalie prop analysis with B2B splits, xG Save %, opponent shot quality, and save projections. Key insight: goalies drop 2-3% SV% on back-to-backs.",
        category=ToolCategory.NHL,
        status=ToolStatus.FREE,
        icon="hockey-puck",
        sports=["nhl"],
        function_name="analyze_goalie_props",
    ),
    "get_nhl_goalie_profile": Tool(
        id="get_nhl_goalie_profile",
        name="Goalie Profile",
        description="Detailed goalie metrics including save %, xG save %, luck factor, high-danger save %, and B2B performance splits.",
        category=ToolCategory.NHL,
        status=ToolStatus.FREE,
        icon="user-shield",
        sports=["nhl"],
        function_name="get_nhl_goalie_profile",
    ),
    "get_nhl_team_profile": Tool(
        id="get_nhl_team_profile",
        name="Team Analytics",
        description="NHL team analytics with Corsi%, xG, high-danger chances, power play and penalty kill percentages, and style classification.",
        category=ToolCategory.NHL,
        status=ToolStatus.FREE,
        icon="users",
        sports=["nhl"],
        function_name="get_nhl_team_profile",
    ),
    "analyze_nhl_matchup": Tool(
        id="analyze_nhl_matchup",
        name="Matchup Analyzer",
        description="Head-to-head NHL matchup analysis with Corsi/xG edge identification, special teams comparison, and projected totals.",
        category=ToolCategory.NHL,
        status=ToolStatus.FREE,
        icon="swords",
        sports=["nhl"],
        function_name="analyze_nhl_matchup",
    ),
    "get_referee_tendencies": Tool(
        id="get_referee_tendencies",
        name="Referee Tendencies",
        description="NHL referee penalty and total tendencies. Some refs consistently call 8-9 penalties/game with overs hitting 58%+.",
        category=ToolCategory.NHL,
        status=ToolStatus.FREE,
        icon="whistle",
        sports=["nhl"],
        function_name="get_referee_tendencies",
    ),
    
    # -------------------------------------------------------------------------
    # MLB TOOLS
    # -------------------------------------------------------------------------
    "analyze_pitcher_props": Tool(
        id="analyze_pitcher_props",
        name="Pitcher Alpha",
        description="MLB pitcher prop analyzer with K projections, IP estimates, ERA context, defense-adjusted splits, pitch mix edges, and xwOBA vs lineup. Factors in park, weather, wind, and bullpen fatigue.",
        category=ToolCategory.MLB,
        status=ToolStatus.FREE,
        icon="baseball",
        sports=["mlb"],
        function_name="analyze_pitcher_props",
    ),
    "get_pitcher_profile": Tool(
        id="get_pitcher_profile",
        name="Pitcher Profile",
        description="Detailed pitcher metrics including K/9, BB/9, xERA, Stuff+, pitch mix breakdown, platoon splits, and recent form. Essential context for prop betting.",
        category=ToolCategory.MLB,
        status=ToolStatus.FREE,
        icon="user-chart",
        sports=["mlb"],
        function_name="get_pitcher_profile",
    ),
    "get_lineup_vs_pitcher": Tool(
        id="get_lineup_vs_pitcher",
        name="Lineup vs Pitcher",
        description="Analyze how a team's lineup matches up against a specific pitcher. Shows xwOBA, K rates, and barrel rates by batter with platoon context.",
        category=ToolCategory.MLB,
        status=ToolStatus.FREE,
        icon="swords",
        sports=["mlb"],
        function_name="get_lineup_vs_pitcher",
    ),
    "get_park_factors": Tool(
        id="get_park_factors",
        name="Park Factors",
        description="MLB park factors for runs, home runs, hits, and strikeouts. Coors Field vs Oracle Park can swing totals by 2+ runs.",
        category=ToolCategory.MLB,
        status=ToolStatus.FREE,
        icon="stadium",
        sports=["mlb"],
        function_name="get_park_factors",
    ),
    "analyze_bullpen_usage": Tool(
        id="analyze_bullpen_usage",
        name="Bullpen Analyzer",
        description="Track bullpen workload, high-leverage arm availability, and fatigue levels. Key for live betting and late-game totals.",
        category=ToolCategory.MLB,
        status=ToolStatus.FREE,
        icon="users-gear",
        sports=["mlb"],
        function_name="analyze_bullpen_usage",
    ),
    "get_weather_impact": Tool(
        id="get_weather_impact",
        name="Weather Impact",
        description="MLB weather analysis including wind direction/speed, temperature, humidity, and their impact on run scoring and home runs.",
        category=ToolCategory.MLB,
        status=ToolStatus.FREE,
        icon="cloud-sun",
        sports=["mlb"],
        function_name="get_weather_impact",
    ),
    
    # -------------------------------------------------------------------------
    # FUTURE PREMIUM TOOLS (IDEAS)
    # -------------------------------------------------------------------------
    "sharps_consensus": Tool(
        id="sharps_consensus",
        name="Sharps Consensus",
        description="Aggregated sharp bettor positions and professional money flow across sportsbooks.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.ROADMAP,
        icon="brain",
        sports=["nfl", "nhl", "mlb"],
        eta="Q2 2026",
    ),
    "line_movement_alerts": Tool(
        id="line_movement_alerts",
        name="Line Movement Alerts",
        description="Real-time alerts when lines move significantly, indicating sharp action or breaking news.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.ROADMAP,
        icon="bell",
        sports=["nfl", "nhl", "mlb"],
        eta="Q2 2026",
    ),
    "steam_move_detector": Tool(
        id="steam_move_detector",
        name="Steam Move Detector",
        description="Detect coordinated sharp betting action (steam moves) across multiple sportsbooks simultaneously.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.IDEA,
        icon="fire",
        sports=["nfl", "nhl", "mlb"],
    ),
    "closing_line_value": Tool(
        id="closing_line_value",
        name="CLV Tracker",
        description="Track your closing line value to measure betting skill over time. Beating the closing line = long-term profitability.",
        category=ToolCategory.GENERAL,
        status=ToolStatus.IDEA,
        icon="target",
        sports=["nfl", "nhl", "mlb"],
    ),
}


class ToolRegistry:
    """
    Registry for managing tools and their status.
    
    Provides methods to:
    - List tools by category, status, or sport
    - Get tool details
    - Check if a tool is available for a user (future: based on subscription)
    - Vote on idea tools
    """
    
    def __init__(self):
        self._tools = TOOLS.copy()
    
    def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get a single tool by ID."""
        return self._tools.get(tool_id)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all tools."""
        return list(self._tools.values())
    
    def get_tools_by_status(self, status: ToolStatus) -> List[Tool]:
        """Get tools filtered by status."""
        return [t for t in self._tools.values() if t.status == status]
    
    def get_tools_by_category(self, category: ToolCategory) -> List[Tool]:
        """Get tools filtered by category."""
        return [t for t in self._tools.values() if t.category == category]
    
    def get_tools_by_sport(self, sport: str) -> List[Tool]:
        """Get tools that support a specific sport."""
        sport_lower = sport.lower()
        return [t for t in self._tools.values() if sport_lower in t.sports]
    
    def get_free_tools(self) -> List[Tool]:
        """Get all free tools (available to everyone)."""
        return self.get_tools_by_status(ToolStatus.FREE)
    
    def get_premium_tools(self) -> List[Tool]:
        """Get all premium tools (future subscription required)."""
        return self.get_tools_by_status(ToolStatus.PREMIUM)
    
    def get_roadmap_tools(self) -> List[Tool]:
        """Get all roadmap tools (in development)."""
        return self.get_tools_by_status(ToolStatus.ROADMAP)
    
    def get_idea_tools(self) -> List[Tool]:
        """Get all idea tools (under consideration)."""
        return self.get_tools_by_status(ToolStatus.IDEA)
    
    def is_tool_available(self, tool_id: str, user_tier: str = "free") -> bool:
        """
        Check if a tool is available for a user based on their tier.
        
        Future: This will check subscription status for premium tools.
        Currently: All free tools are available, premium/roadmap/idea are not.
        """
        tool = self.get_tool(tool_id)
        if not tool:
            return False
        
        if tool.status == ToolStatus.FREE:
            return True
        
        if tool.status == ToolStatus.PREMIUM:
            # Future: Check user subscription
            return user_tier in ["premium", "pro", "enterprise"]
        
        # Roadmap and idea tools are not yet available
        return False
    
    def get_available_function_names(self, user_tier: str = "free") -> List[str]:
        """Get list of function names available to a user for agent binding."""
        available = []
        for tool in self._tools.values():
            if self.is_tool_available(tool.id, user_tier) and tool.function_name:
                available.append(tool.function_name)
        return available
    
    def vote_for_tool(self, tool_id: str) -> bool:
        """Vote for an idea tool. Returns True if successful."""
        tool = self.get_tool(tool_id)
        if tool and tool.status == ToolStatus.IDEA:
            tool.votes += 1
            tool.updated_at = datetime.utcnow()
            return True
        return False
    
    def to_api_response(self, tools: Optional[List[Tool]] = None) -> List[Dict[str, Any]]:
        """Convert tools to API response format."""
        if tools is None:
            tools = self.get_all_tools()
        return [t.to_dict() for t in tools]


# Global registry instance
registry = ToolRegistry()


# Convenience functions
def get_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return registry


def get_tool(tool_id: str) -> Optional[Tool]:
    """Get a tool by ID."""
    return registry.get_tool(tool_id)


def get_available_tools(user_tier: str = "free") -> List[Tool]:
    """Get all tools available to a user."""
    return [t for t in registry.get_all_tools() if registry.is_tool_available(t.id, user_tier)]

