"""
NBA Player Props Analyzer - The "Alpha" Logic for NBA Prop Betting.

This module calculates contextual splits to find edges in NBA player props:
- Defense vs Position (DvP) analysis
- Pace-adjusted projections
- Usage rate with minutes projection
- Game script splits (blowout vs close games)
- Recent form weighting

Designed to integrate with the sports betting agent for NBA prop analysis.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.nba_data import NBADataFetcher, NBADefenseProfile, NBAPlayerProfile, NBATeamPace, get_nba_fetcher


@dataclass
class NBAPropProjection:
    """A projected NBA prop line with contextual analysis."""
    player: str
    position: str
    prop_type: str                 # "PTS", "AST", "REB", "3PM", "PTS+REB+AST"
    standard_projection: float
    contextual_projection: float
    current_line: Optional[float] = None
    edge: Optional[float] = None
    confidence: str = "Medium"
    reasoning: str = ""
    adjustments: List[str] = field(default_factory=list)
    hit_rate_estimate: float = 50.0  # Estimated over hit rate
    recommendation: str = "PASS"      # "OVER", "UNDER", "PASS"
    
    def __post_init__(self):
        if self.current_line is not None:
            self.edge = round(self.contextual_projection - self.current_line, 1)
            # Calculate hit rate estimate based on edge
            if abs(self.edge) > 0:
                edge_pct = (self.edge / self.current_line) * 100 if self.current_line > 0 else 0
                self.hit_rate_estimate = min(75, max(25, 50 + edge_pct * 2))


@dataclass
class NBAMatchupAnalysis:
    """Full matchup analysis for a player prop."""
    player: str
    player_profile: Optional[NBAPlayerProfile]
    opponent: str
    opponent_defense: Optional[NBADefenseProfile]
    pace_data: Optional[Dict[str, Any]]
    projections: List[NBAPropProjection]
    risk_factors: List[str]
    edge_factors: List[str]


class NBAPropsAnalyzer:
    """
    Analyzes NBA player props using contextual data.
    
    Key features:
    1. DvP (Defense vs Position) - Opponent's weakness vs player position
    2. Pace adjustment - Fast/slow game environments
    3. Usage & minutes projection
    4. Game script expectations (blowouts reduce star minutes)
    5. Recent form weighting
    """
    
    # Thresholds for betting signals
    EDGE_THRESHOLD = 2.0           # Minimum edge for recommendation
    HIGH_CONFIDENCE_EDGE = 4.0     # Edge for high confidence
    PACE_ADJUSTMENT_FACTOR = 0.04  # 4% per pace differential from league avg
    
    # Prop type mappings
    PROP_TYPES = {
        "PTS": "pts_per_game",
        "AST": "ast_per_game",
        "REB": "reb_per_game",
        "3PM": "three_pt_made",  # Calculated separately
        "PTS+REB+AST": "pra",    # Combined
        "PTS+AST": "pts_ast",
        "PTS+REB": "pts_reb",
    }
    
    def __init__(self, season: str = None):
        """Initialize with NBA data fetcher."""
        self.fetcher = get_nba_fetcher(season)
        self.console = Console()
    
    def analyze_player_prop(
        self,
        player_name: str,
        position: str,
        opponent: str,
        prop_type: str,
        prop_line: float,
        pace_factor: str = "normal",  # "fast", "slow", "normal"
        expected_blowout: bool = False,
    ) -> NBAMatchupAnalysis:
        """
        Analyze a player prop with full contextual data.
        
        Args:
            player_name: Player name (e.g., "Jalen Brunson")
            position: Position (PG, SG, SF, PF, C)
            opponent: Opponent team abbreviation (e.g., "BOS")
            prop_type: Type of prop (PTS, AST, REB, 3PM, PTS+REB+AST)
            prop_line: The betting line (e.g., 28.5)
            pace_factor: Expected pace ("fast", "slow", "normal")
            expected_blowout: Whether blowout is expected (reduces minutes)
            
        Returns:
            NBAMatchupAnalysis with projections and recommendations
        """
        prop_type = prop_type.upper()
        position = position.upper()
        opponent = opponent.upper()
        
        self.console.print(f"\n[bold cyan]🏀 Analyzing {player_name} {prop_type} O/U {prop_line} vs {opponent}[/bold cyan]")
        
        # Get player profile
        player_profile = self.fetcher.get_player_profile(player_name)
        if not player_profile:
            return NBAMatchupAnalysis(
                player=player_name,
                player_profile=None,
                opponent=opponent,
                opponent_defense=None,
                pace_data=None,
                projections=[],
                risk_factors=["Player not found in database"],
                edge_factors=[]
            )
        
        # Get opponent defense profile
        opponent_defense = self.fetcher.get_defense_profile(opponent)
        
        # Get pace data
        player_team_pace = self.fetcher.get_team_pace(player_profile.team)
        opponent_pace = self.fetcher.get_team_pace(opponent)
        
        pace_data = None
        if player_team_pace and opponent_pace:
            pace_data = self.fetcher.calculate_matchup_pace(player_profile.team, opponent)
        
        # Display player profile
        self.console.print(Panel(
            f"[bold]{player_profile.name}[/bold] ({player_profile.team})\n"
            f"Position: {player_profile.position}\n\n"
            f"Season Averages:\n"
            f"• PTS: {player_profile.pts_per_game:.1f}\n"
            f"• AST: {player_profile.ast_per_game:.1f}\n"
            f"• REB: {player_profile.reb_per_game:.1f}\n"
            f"• MIN: {player_profile.min_per_game:.1f}\n"
            f"• Usage: {player_profile.usage_rate:.1f}%\n\n"
            f"Recent Form (L5):\n"
            f"• PTS: {player_profile.last_5_pts:.1f} ({player_profile.get_trend('pts').upper()})\n"
            f"• AST: {player_profile.last_5_ast:.1f} ({player_profile.get_trend('ast').upper()})\n"
            f"• REB: {player_profile.last_5_reb:.1f} ({player_profile.get_trend('reb').upper()})",
            title="Player Profile"
        ))
        
        # Display opponent defense
        if opponent_defense:
            self.console.print(Panel(
                f"[bold]{opponent} Defense[/bold]\n\n"
                f"• DEF Rating: {opponent_defense.def_rating:.1f}\n"
                f"• Opp PTS/Game: {opponent_defense.opp_pts_per_game:.1f}\n"
                f"• Opp FG%: {opponent_defense.opp_fg_pct:.1%}\n"
                f"• Blocks/Game: {opponent_defense.blocks_per_game:.1f}\n"
                f"• Steals/Game: {opponent_defense.steals_per_game:.1f}\n"
                f"• Style: {opponent_defense.get_style().replace('_', ' ').title()}\n\n"
                f"DvP vs {position}: {opponent_defense.get_dvp_adjustment(position):+.1f} pts",
                title="Opponent Defense"
            ))
        
        # Calculate projections
        risk_factors = []
        edge_factors = []
        adjustments = []
        
        # 1. Get base projection from season average
        base_projection = self._get_base_projection(player_profile, prop_type)
        contextual_projection = base_projection
        
        # 2. Apply DvP adjustment
        if opponent_defense:
            dvp_adj = opponent_defense.get_dvp_adjustment(position)
            if prop_type == "PTS":
                contextual_projection += dvp_adj
                if dvp_adj > 2:
                    edge_factors.append(f"DvP edge: {opponent} gives up +{dvp_adj:.1f} to {position}s")
                    adjustments.append(f"DvP: +{dvp_adj:.1f}")
                elif dvp_adj < -2:
                    risk_factors.append(f"Tough matchup: {opponent} locks down {position}s ({dvp_adj:+.1f})")
                    adjustments.append(f"DvP: {dvp_adj:.1f}")
            elif prop_type in ["AST", "REB"]:
                # Smaller DvP impact on AST/REB
                adjusted_dvp = dvp_adj * 0.3
                contextual_projection += adjusted_dvp
                adjustments.append(f"DvP (adj): {adjusted_dvp:+.1f}")
        
        # 3. Apply pace adjustment
        if pace_data:
            pace_adj = pace_data.get('combined_adjustment', 0)
            tempo_class = pace_data.get('tempo_class', 'neutral')
            
            # Pace impacts scoring most, less so AST/REB
            if prop_type == "PTS":
                pace_multiplier = 1 + (pace_adj * self.PACE_ADJUSTMENT_FACTOR / 10)
                contextual_projection *= pace_multiplier
                
                if tempo_class == "track_meet":
                    edge_factors.append(f"Track meet: Both teams top-10 pace")
                    adjustments.append(f"Pace boost: +{(pace_multiplier - 1) * 100:.1f}%")
                elif tempo_class == "grind":
                    risk_factors.append(f"Slow game expected: Both teams bottom-10 pace")
                    adjustments.append(f"Pace drag: {(pace_multiplier - 1) * 100:.1f}%")
            elif prop_type in ["AST", "REB"]:
                # Smaller pace impact
                pace_multiplier = 1 + (pace_adj * self.PACE_ADJUSTMENT_FACTOR / 20)
                contextual_projection *= pace_multiplier
        
        # Override with explicit pace factor
        if pace_factor == "fast":
            contextual_projection *= 1.05
            adjustments.append("Expected fast game: +5%")
        elif pace_factor == "slow":
            contextual_projection *= 0.95
            adjustments.append("Expected slow game: -5%")
        
        # 4. Apply recent form weighting (30% weight to L5)
        recent_stat = self._get_recent_stat(player_profile, prop_type)
        if recent_stat > 0:
            form_weighted = (base_projection * 0.7) + (recent_stat * 0.3)
            form_adjustment = form_weighted - base_projection
            
            # Only apply if significant
            if abs(form_adjustment) > 1:
                contextual_projection += form_adjustment * 0.3  # Dampen the adjustment
                trend = player_profile.get_trend(self._prop_to_trend_key(prop_type))
                if trend == "hot":
                    edge_factors.append(f"Hot streak: L5 avg {recent_stat:.1f} vs season {base_projection:.1f}")
                    adjustments.append(f"Form (hot): +{form_adjustment * 0.3:.1f}")
                elif trend == "cold":
                    risk_factors.append(f"Cold streak: L5 avg {recent_stat:.1f} vs season {base_projection:.1f}")
                    adjustments.append(f"Form (cold): {form_adjustment * 0.3:.1f}")
        
        # 5. Apply blowout risk
        if expected_blowout:
            # Stars typically lose 5-8 minutes in blowouts
            minutes_reduction = 0.85  # ~15% reduction in production
            contextual_projection *= minutes_reduction
            risk_factors.append("Blowout risk: Star may sit 4th quarter")
            adjustments.append("Blowout: -15%")
        
        # 6. Apply minutes projection (if available)
        if player_profile.min_per_game > 0:
            # Flag if player is on minutes restriction
            if player_profile.min_per_game < 28:
                risk_factors.append(f"Low minutes: Only {player_profile.min_per_game:.1f} MPG")
        
        # Build projection
        edge = contextual_projection - prop_line
        
        # Determine confidence and recommendation
        if abs(edge) >= self.HIGH_CONFIDENCE_EDGE:
            confidence = "High"
            recommendation = "OVER" if edge > 0 else "UNDER"
        elif abs(edge) >= self.EDGE_THRESHOLD:
            confidence = "Medium"
            recommendation = "OVER" if edge > 0 else "UNDER"
        else:
            confidence = "Low"
            recommendation = "PASS"
        
        projection = NBAPropProjection(
            player=player_name,
            position=position,
            prop_type=prop_type,
            standard_projection=round(base_projection, 1),
            contextual_projection=round(contextual_projection, 1),
            current_line=prop_line,
            confidence=confidence,
            reasoning=f"DvP + Pace + Form adjustments vs {opponent}",
            adjustments=adjustments,
            recommendation=recommendation,
        )
        
        return NBAMatchupAnalysis(
            player=player_name,
            player_profile=player_profile,
            opponent=opponent,
            opponent_defense=opponent_defense,
            pace_data=pace_data,
            projections=[projection],
            risk_factors=risk_factors,
            edge_factors=edge_factors,
        )
    
    def _get_base_projection(self, profile: NBAPlayerProfile, prop_type: str) -> float:
        """Get base season average for prop type."""
        if prop_type == "PTS":
            return profile.pts_per_game
        elif prop_type == "AST":
            return profile.ast_per_game
        elif prop_type == "REB":
            return profile.reb_per_game
        elif prop_type == "PTS+REB+AST":
            return profile.pts_per_game + profile.reb_per_game + profile.ast_per_game
        elif prop_type == "PTS+AST":
            return profile.pts_per_game + profile.ast_per_game
        elif prop_type == "PTS+REB":
            return profile.pts_per_game + profile.reb_per_game
        elif prop_type == "3PM":
            # Estimate from FG3 attempts (typically 35-40% of attempts made)
            return profile.three_pt_pct * 8  # Rough estimate based on attempts
        else:
            return 0
    
    def _get_recent_stat(self, profile: NBAPlayerProfile, prop_type: str) -> float:
        """Get L5 average for prop type."""
        if prop_type == "PTS":
            return profile.last_5_pts
        elif prop_type == "AST":
            return profile.last_5_ast
        elif prop_type == "REB":
            return profile.last_5_reb
        elif prop_type == "PTS+REB+AST":
            return profile.last_5_pts + profile.last_5_reb + profile.last_5_ast
        elif prop_type == "PTS+AST":
            return profile.last_5_pts + profile.last_5_ast
        elif prop_type == "PTS+REB":
            return profile.last_5_pts + profile.last_5_reb
        else:
            return 0
    
    def _prop_to_trend_key(self, prop_type: str) -> str:
        """Convert prop type to trend key."""
        if prop_type in ["PTS", "PTS+REB+AST", "PTS+AST", "PTS+REB"]:
            return "pts"
        elif prop_type == "AST":
            return "ast"
        elif prop_type == "REB":
            return "reb"
        return "pts"
    
    def print_analysis(self, analysis: NBAMatchupAnalysis):
        """Print analysis in a formatted output."""
        # Projections table
        if analysis.projections:
            table = Table(title=f"🏀 {analysis.player} Prop Projections vs {analysis.opponent}")
            
            table.add_column("Prop", style="cyan")
            table.add_column("Season Avg", justify="right")
            table.add_column("Projected", justify="right", style="green")
            table.add_column("Line", justify="right")
            table.add_column("Edge", justify="right", style="bold")
            table.add_column("Conf.", justify="center")
            table.add_column("Action", style="yellow")
            
            for p in analysis.projections:
                edge_str = f"{p.edge:+.1f}" if p.edge else "N/A"
                line_str = f"{p.current_line:.1f}" if p.current_line else "N/A"
                
                action_style = {
                    "OVER": "✅ OVER",
                    "UNDER": "✅ UNDER",
                    "PASS": "⏸️ PASS"
                }
                
                table.add_row(
                    p.prop_type,
                    f"{p.standard_projection:.1f}",
                    f"{p.contextual_projection:.1f}",
                    line_str,
                    edge_str,
                    p.confidence,
                    action_style.get(p.recommendation, p.recommendation)
                )
            
            self.console.print(table)
            
            # Adjustments
            for p in analysis.projections:
                if p.adjustments:
                    self.console.print(f"\n[bold]📊 Adjustments Applied:[/bold]")
                    for adj in p.adjustments:
                        self.console.print(f"  • {adj}")
        
        # Risk factors
        if analysis.risk_factors:
            self.console.print("\n[bold red]⚠️ Risk Factors:[/bold red]")
            for risk in analysis.risk_factors:
                self.console.print(f"  • {risk}")
        
        # Edge factors
        if analysis.edge_factors:
            self.console.print("\n[bold green]✅ Edge Factors:[/bold green]")
            for edge in analysis.edge_factors:
                self.console.print(f"  • {edge}")
    
    def to_json(self, analysis: NBAMatchupAnalysis) -> str:
        """Convert analysis to JSON for agent tool response."""
        return json.dumps({
            "status": "success",
            "player": analysis.player,
            "opponent": analysis.opponent,
            "player_profile": {
                "team": analysis.player_profile.team,
                "position": analysis.player_profile.position,
                "games_played": analysis.player_profile.games_played,
                "pts_per_game": analysis.player_profile.pts_per_game,
                "ast_per_game": analysis.player_profile.ast_per_game,
                "reb_per_game": analysis.player_profile.reb_per_game,
                "min_per_game": analysis.player_profile.min_per_game,
                "usage_rate": analysis.player_profile.usage_rate,
                "last_5_pts": analysis.player_profile.last_5_pts,
                "last_5_ast": analysis.player_profile.last_5_ast,
                "last_5_reb": analysis.player_profile.last_5_reb,
                "pts_trend": analysis.player_profile.get_trend("pts"),
            } if analysis.player_profile else None,
            "opponent_defense": {
                "def_rating": analysis.opponent_defense.def_rating,
                "opp_pts_per_game": analysis.opponent_defense.opp_pts_per_game,
                "style": analysis.opponent_defense.get_style(),
                "dvp_by_position": analysis.opponent_defense.dvp_by_position,
            } if analysis.opponent_defense else None,
            "pace_data": analysis.pace_data,
            "projections": [
                {
                    "prop_type": p.prop_type,
                    "standard_projection": p.standard_projection,
                    "contextual_projection": p.contextual_projection,
                    "current_line": p.current_line,
                    "edge": p.edge,
                    "confidence": p.confidence,
                    "recommendation": p.recommendation,
                    "hit_rate_estimate": p.hit_rate_estimate,
                    "reasoning": p.reasoning,
                    "adjustments": p.adjustments,
                }
                for p in analysis.projections
            ],
            "risk_factors": analysis.risk_factors,
            "edge_factors": analysis.edge_factors,
        }, indent=2)


def analyze_nba_prop(
    player: str,
    position: str,
    opponent: str,
    prop_type: str,
    line: float,
    pace: str = "normal",
    blowout_risk: bool = False
) -> NBAMatchupAnalysis:
    """
    Convenience function for NBA prop analysis.
    
    Args:
        player: Player name
        position: Position (PG, SG, SF, PF, C)
        opponent: Opponent team
        prop_type: Prop type (PTS, AST, REB, etc.)
        line: Betting line
        pace: Expected pace (fast, slow, normal)
        blowout_risk: Whether blowout is expected
        
    Returns:
        NBAMatchupAnalysis
    """
    analyzer = NBAPropsAnalyzer()
    analysis = analyzer.analyze_player_prop(
        player_name=player,
        position=position,
        opponent=opponent,
        prop_type=prop_type,
        prop_line=line,
        pace_factor=pace,
        expected_blowout=blowout_risk,
    )
    analyzer.print_analysis(analysis)
    return analysis


if __name__ == "__main__":
    # Example: Jalen Brunson PTS prop vs Celtics
    analysis = analyze_nba_prop(
        player="Jalen Brunson",
        position="PG",
        opponent="BOS",
        prop_type="PTS",
        line=28.5,
        pace="normal",
    )
