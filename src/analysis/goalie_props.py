"""
Goalie Props Analyzer - The "Goalie Alpha" Logic for NHL Prop Betting.

This module analyzes goalie props using:
- Save % vs shot volume (auto-under on goalies facing <25 shots)
- Back-to-back performance splits (goalies drop 2-3% SV% on B2B)
- xG Save % (fades "lucky" goalies overperforming their expected)
- Rest days analysis (performance by days of rest)

Designed to integrate with the sports betting agent for NHL goalie prop analysis.
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
from tools.nhl_data import NHLDataFetcher, GoalieProfile, TeamProfile, get_nhl_fetcher


@dataclass
class GoaliePropProjection:
    """A projected goalie prop with contextual analysis."""
    goalie: str
    team: str
    prop_type: str                    # "saves", "goals_against", "save_pct"
    standard_projection: float
    contextual_projection: float
    current_line: Optional[float] = None
    edge: Optional[float] = None
    confidence: str = "Medium"
    reasoning: str = ""
    adjustments: List[str] = field(default_factory=list)
    recommendation: str = "PASS"       # "OVER", "UNDER", "PASS"
    
    def __post_init__(self):
        if self.current_line is not None:
            self.edge = self.contextual_projection - self.current_line


@dataclass
class GoalieMatchupAnalysis:
    """Full goalie matchup analysis."""
    goalie: str
    team: str
    opponent: str
    goalie_profile: GoalieProfile
    opponent_profile: Optional[TeamProfile]
    is_back_to_back: bool
    expected_shots: float
    projections: List[GoaliePropProjection]
    risk_factors: List[str]
    edge_factors: List[str]


class GoaliePropsAnalyzer:
    """
    Analyzes goalie props using contextual data.
    
    Key features:
    1. SV% vs shot volume - Low shot games = under on saves
    2. B2B penalty - Goalies drop 2-3% SV% on back-to-backs
    3. xG Save % - Fades lucky goalies overperforming expected
    4. Opponent analysis - Shot volume and quality tendencies
    """
    
    # Thresholds for betting signals
    LOW_SHOT_THRESHOLD = 25           # Games with <25 shots = under on saves
    HIGH_SHOT_THRESHOLD = 35          # Games with 35+ shots = over consideration
    B2B_SV_PENALTY = 0.025            # Expected SV% drop on back-to-backs (2.5%)
    LUCK_FADE_THRESHOLD = 0.015       # Fade goalies with luck_factor > 1.5%
    EDGE_THRESHOLD = 2.0              # Minimum edge for recommendation
    
    def __init__(self, seasons: List[int] = None):
        """Initialize with NHL data fetcher (singleton to avoid duplicate downloads)."""
        self.fetcher = get_nhl_fetcher(seasons)
        self.console = Console()
    
    def analyze_goalie_props(
        self,
        goalie_name: str,
        opponent: str,
        is_back_to_back: bool = False,
        expected_shots: float = None,
        saves_line: float = None,
        goals_against_line: float = None,
        season: int = None
    ) -> GoalieMatchupAnalysis:
        """
        Full goalie prop analysis for betting.
        
        Args:
            goalie_name: Goalie name (flexible matching)
            opponent: Opponent team abbreviation
            is_back_to_back: Whether goalie played yesterday
            expected_shots: Expected shots on goal (if known from projections)
            saves_line: Current saves prop line
            goals_against_line: Current goals against prop line
            season: Season year
            
        Returns:
            GoalieMatchupAnalysis with projections and recommendations
        """
        season = season or self.fetcher.seasons[0]
        
        self.console.print(f"\n[bold cyan]🥅 Analyzing {goalie_name} vs {opponent}[/bold cyan]")
        if is_back_to_back:
            self.console.print("[yellow]⚠️ BACK-TO-BACK ALERT[/yellow]")
        
        # Get goalie profile
        goalie_profile = self.fetcher.get_goalie_profile(goalie_name, season)
        if not goalie_profile:
            return GoalieMatchupAnalysis(
                goalie=goalie_name,
                team="UNK",
                opponent=opponent,
                goalie_profile=None,
                opponent_profile=None,
                is_back_to_back=is_back_to_back,
                expected_shots=expected_shots or 30,
                projections=[],
                risk_factors=["Goalie not found in database"],
                edge_factors=[]
            )
        
        # Get opponent profile
        opponent_profile = self.fetcher.get_team_profile(opponent, season)
        
        # Estimate expected shots if not provided
        if expected_shots is None:
            if opponent_profile:
                # Use opponent's average shots for per game
                expected_shots = opponent_profile.corsi_for_per_game * 0.4  # Rough shots:corsi ratio
                if expected_shots < 20:
                    expected_shots = 30  # Fallback to league average
            else:
                expected_shots = 30  # League average
        
        self.console.print(Panel(
            f"[bold]{goalie_profile.name}[/bold] ({goalie_profile.team})\n\n"
            f"• Games Played: {goalie_profile.games_played}\n"
            f"• Save %: {goalie_profile.save_pct:.3f} ({goalie_profile.save_pct*100:.1f}%)\n"
            f"• xG Save %: {goalie_profile.xg_save_pct:.3f} ({goalie_profile.xg_save_pct*100:.1f}%)\n"
            f"• Luck Factor: {goalie_profile.luck_factor:+.3f} "
            f"{'🍀 OVERPERFORMING' if goalie_profile.luck_factor > 0.01 else '📉 Underperforming' if goalie_profile.luck_factor < -0.01 else '➡️ Neutral'}\n"
            f"• Shots Against/Game: {goalie_profile.shots_against_per_game:.1f}\n"
            f"• HD Save %: {goalie_profile.high_danger_sv_pct:.3f}",
            title="Goalie Profile"
        ))
        
        # Display B2B splits if available
        if goalie_profile.b2b_games > 0:
            b2b_penalty = goalie_profile.get_b2b_penalty()
            self.console.print(Panel(
                f"[bold]Back-to-Back Analysis[/bold]\n\n"
                f"• B2B Games: {goalie_profile.b2b_games}\n"
                f"• B2B Save %: {goalie_profile.b2b_save_pct:.3f} ({goalie_profile.b2b_save_pct*100:.1f}%)\n"
                f"• Rested Games: {goalie_profile.rested_games}\n"
                f"• Rested Save %: {goalie_profile.rested_save_pct:.3f} ({goalie_profile.rested_save_pct*100:.1f}%)\n"
                f"• B2B Penalty: {b2b_penalty*100:+.2f}% SV%",
                title="🔄 Rest Splits"
            ))
        
        # Identify risk and edge factors
        risk_factors = []
        edge_factors = []
        
        # 1. Back-to-back check
        if is_back_to_back:
            risk_factors.append(f"B2B: Expected {self.B2B_SV_PENALTY*100:.1f}% SV% drop")
            if goalie_profile.b2b_games > 3:
                actual_penalty = goalie_profile.get_b2b_penalty()
                if actual_penalty > 0.02:
                    risk_factors.append(f"Historical B2B penalty: {actual_penalty*100:.1f}%")
        
        # 2. Luck regression check
        if goalie_profile.luck_factor > self.LUCK_FADE_THRESHOLD:
            risk_factors.append(
                f"Luck fade: SV% {goalie_profile.luck_factor*100:+.1f}% above expected"
            )
        elif goalie_profile.luck_factor < -self.LUCK_FADE_THRESHOLD:
            edge_factors.append(
                f"Bounce-back candidate: SV% {goalie_profile.luck_factor*100:.1f}% below expected"
            )
        
        # 3. Shot volume check
        if expected_shots < self.LOW_SHOT_THRESHOLD:
            risk_factors.append(f"Low shot game ({expected_shots:.0f} expected) = under on saves")
        elif expected_shots > self.HIGH_SHOT_THRESHOLD:
            edge_factors.append(f"High shot game ({expected_shots:.0f} expected) = over on saves")
        
        # 4. Opponent quality
        if opponent_profile:
            if opponent_profile.xg_for_per_game > 3.2:
                risk_factors.append(f"{opponent} is high xG team ({opponent_profile.xg_for_per_game:.2f}/game)")
            elif opponent_profile.xg_for_per_game < 2.5:
                edge_factors.append(f"{opponent} is low xG team ({opponent_profile.xg_for_per_game:.2f}/game)")
            
            if opponent_profile.hd_pct > 52:
                risk_factors.append(f"{opponent} generates high-danger chances (HD%: {opponent_profile.hd_pct:.1f})")
        
        # Generate projections
        projections = self._generate_projections(
            goalie_profile=goalie_profile,
            opponent_profile=opponent_profile,
            is_back_to_back=is_back_to_back,
            expected_shots=expected_shots,
            saves_line=saves_line,
            goals_against_line=goals_against_line,
        )
        
        return GoalieMatchupAnalysis(
            goalie=goalie_profile.name,
            team=goalie_profile.team,
            opponent=opponent,
            goalie_profile=goalie_profile,
            opponent_profile=opponent_profile,
            is_back_to_back=is_back_to_back,
            expected_shots=expected_shots,
            projections=projections,
            risk_factors=risk_factors,
            edge_factors=edge_factors,
        )
    
    def _generate_projections(
        self,
        goalie_profile: GoalieProfile,
        opponent_profile: Optional[TeamProfile],
        is_back_to_back: bool,
        expected_shots: float,
        saves_line: float = None,
        goals_against_line: float = None,
    ) -> List[GoaliePropProjection]:
        """Generate prop projections with contextual adjustments."""
        projections = []
        adjustments = []
        
        # Base save %
        base_sv_pct = goalie_profile.save_pct
        contextual_sv_pct = base_sv_pct
        
        # 1. B2B adjustment
        if is_back_to_back:
            if goalie_profile.b2b_games > 3:
                # Use actual B2B performance
                contextual_sv_pct = goalie_profile.b2b_save_pct
                adjustments.append(f"B2B historical: {goalie_profile.b2b_save_pct:.3f}")
            else:
                # Use league average penalty
                contextual_sv_pct -= self.B2B_SV_PENALTY
                adjustments.append(f"B2B penalty: -{self.B2B_SV_PENALTY*100:.1f}%")
        
        # 2. Luck regression (move toward xG SV%)
        if abs(goalie_profile.luck_factor) > 0.01:
            # Regress 30% toward expected
            regression = goalie_profile.luck_factor * 0.3
            contextual_sv_pct -= regression
            adjustments.append(f"xG regression: {-regression*100:+.1f}%")
        
        # 3. Opponent quality adjustment
        if opponent_profile:
            if opponent_profile.xg_for_per_game > 3.2:
                contextual_sv_pct -= 0.01  # Tough matchup
                adjustments.append(f"vs high xG team: -1%")
            elif opponent_profile.xg_for_per_game < 2.5:
                contextual_sv_pct += 0.01  # Easy matchup
                adjustments.append(f"vs low xG team: +1%")
        
        # Calculate projections
        # Saves projection
        standard_saves = expected_shots * base_sv_pct
        contextual_saves = expected_shots * contextual_sv_pct
        
        saves_proj = GoaliePropProjection(
            goalie=goalie_profile.name,
            team=goalie_profile.team,
            prop_type="Saves",
            standard_projection=round(standard_saves, 1),
            contextual_projection=round(contextual_saves, 1),
            current_line=saves_line,
            confidence=self._calculate_confidence(standard_saves, contextual_saves),
            reasoning=f"Expected {expected_shots:.0f} shots × {contextual_sv_pct:.3f} SV%",
            adjustments=adjustments.copy(),
        )
        
        if saves_line:
            saves_proj.edge = saves_proj.contextual_projection - saves_line
            if saves_proj.edge > self.EDGE_THRESHOLD:
                saves_proj.recommendation = "OVER"
            elif saves_proj.edge < -self.EDGE_THRESHOLD:
                saves_proj.recommendation = "UNDER"
        
        projections.append(saves_proj)
        
        # Goals Against projection
        standard_ga = expected_shots * (1 - base_sv_pct)
        contextual_ga = expected_shots * (1 - contextual_sv_pct)
        
        ga_proj = GoaliePropProjection(
            goalie=goalie_profile.name,
            team=goalie_profile.team,
            prop_type="Goals Against",
            standard_projection=round(standard_ga, 1),
            contextual_projection=round(contextual_ga, 1),
            current_line=goals_against_line,
            confidence=self._calculate_confidence(standard_ga, contextual_ga),
            reasoning=f"Expected {expected_shots:.0f} shots × {(1-contextual_sv_pct):.3f} GA%",
            adjustments=adjustments.copy(),
        )
        
        if goals_against_line:
            ga_proj.edge = ga_proj.contextual_projection - goals_against_line
            if ga_proj.edge > 0.3:  # More than 0.3 goals = over
                ga_proj.recommendation = "OVER"
            elif ga_proj.edge < -0.3:
                ga_proj.recommendation = "UNDER"
        
        projections.append(ga_proj)
        
        return projections
    
    def _calculate_confidence(self, standard: float, contextual: float) -> str:
        """Calculate confidence level based on deviation from standard."""
        if standard == 0:
            return "Low"
        
        deviation = abs(contextual - standard) / standard
        
        if deviation > 0.10:
            return "High"
        elif deviation > 0.05:
            return "Medium"
        else:
            return "Low"
    
    def print_analysis(self, analysis: GoalieMatchupAnalysis):
        """Print analysis in a formatted output."""
        # Projections table
        table = Table(title=f"🥅 {analysis.goalie} Prop Projections vs {analysis.opponent}")
        
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
    
    def to_json(self, analysis: GoalieMatchupAnalysis) -> str:
        """Convert analysis to JSON for agent tool response."""
        return json.dumps({
            "status": "success",
            "goalie": analysis.goalie,
            "team": analysis.team,
            "opponent": analysis.opponent,
            "is_back_to_back": analysis.is_back_to_back,
            "expected_shots": analysis.expected_shots,
            "goalie_profile": {
                "games_played": analysis.goalie_profile.games_played,
                "save_pct": analysis.goalie_profile.save_pct,
                "xg_save_pct": analysis.goalie_profile.xg_save_pct,
                "luck_factor": analysis.goalie_profile.luck_factor,
                "shots_against_per_game": analysis.goalie_profile.shots_against_per_game,
                "high_danger_sv_pct": analysis.goalie_profile.high_danger_sv_pct,
                "b2b_games": analysis.goalie_profile.b2b_games,
                "b2b_save_pct": analysis.goalie_profile.b2b_save_pct,
                "rested_save_pct": analysis.goalie_profile.rested_save_pct,
                "b2b_penalty": analysis.goalie_profile.get_b2b_penalty(),
                "is_overperforming": analysis.goalie_profile.is_overperforming(),
            } if analysis.goalie_profile else None,
            "opponent_profile": {
                "xg_for_per_game": analysis.opponent_profile.xg_for_per_game,
                "corsi_pct": analysis.opponent_profile.corsi_pct,
                "hd_pct": analysis.opponent_profile.hd_pct,
                "style": analysis.opponent_profile.get_style(),
            } if analysis.opponent_profile else None,
            "projections": [
                {
                    "prop_type": p.prop_type,
                    "standard_projection": p.standard_projection,
                    "contextual_projection": p.contextual_projection,
                    "current_line": p.current_line,
                    "edge": p.edge,
                    "confidence": p.confidence,
                    "recommendation": p.recommendation,
                    "reasoning": p.reasoning,
                    "adjustments": p.adjustments,
                }
                for p in analysis.projections
            ],
            "risk_factors": analysis.risk_factors,
            "edge_factors": analysis.edge_factors,
        }, indent=2)


def analyze_goalie(
    goalie: str,
    opponent: str,
    is_b2b: bool = False,
    expected_shots: float = None,
    saves_line: float = None,
    ga_line: float = None
) -> GoalieMatchupAnalysis:
    """
    Convenience function for goalie analysis.
    
    Args:
        goalie: Goalie name
        opponent: Opponent team
        is_b2b: Is this a back-to-back?
        expected_shots: Expected shots on goal
        saves_line: Current saves prop line
        ga_line: Current goals against prop line
        
    Returns:
        GoalieMatchupAnalysis
    """
    analyzer = GoaliePropsAnalyzer()
    analysis = analyzer.analyze_goalie_props(
        goalie_name=goalie,
        opponent=opponent,
        is_back_to_back=is_b2b,
        expected_shots=expected_shots,
        saves_line=saves_line,
        goals_against_line=ga_line,
    )
    analyzer.print_analysis(analysis)
    return analysis


if __name__ == "__main__":
    # Example: Igor Shesterkin B2B analysis
    analyze_goalie(
        goalie="Shesterkin",
        opponent="TOR",
        is_b2b=True,
        expected_shots=32,
        saves_line=28.5,
        ga_line=2.5
    )

