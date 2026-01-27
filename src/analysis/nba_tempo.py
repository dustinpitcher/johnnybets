"""
NBA Pace & Tempo Analyzer - Game Totals Edge Finding.

This module analyzes NBA game pace/tempo for betting edges:
- Projected game pace (possessions per 48)
- Tempo edge calculation
- Adjusted total recommendations
- Historical pace matchup outcomes

Totals can swing 5-10 points based on pace mismatches.
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
from tools.nba_data import NBADataFetcher, NBATeamPace, get_nba_fetcher


@dataclass
class TempoMatchupAnalysis:
    """Complete tempo analysis for a game."""
    home_team: str
    away_team: str
    
    # Pace data
    home_pace: float
    home_pace_rank: int
    away_pace: float
    away_pace_rank: int
    
    # Projections
    projected_pace: float
    league_avg_pace: float
    pace_differential: float      # vs league average
    
    # Total analysis
    tempo_class: str              # "track_meet", "grind", "neutral"
    total_adjustment: float       # +/- points vs neutral
    total_lean: str               # "OVER", "UNDER", "PASS"
    confidence: str               # "High", "Medium", "Low"
    
    # Scoring context
    home_pts_per_game: float
    away_pts_per_game: float
    home_opp_pts: float
    away_opp_pts: float
    projected_total: float
    
    # Factors
    edge_factors: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)


class PaceTempoAnalyzer:
    """
    Analyzes game pace and tempo for betting edges.
    
    Key features:
    1. Projected possessions per 48 minutes
    2. Tempo edge (both teams' pace ratings)
    3. Adjusted total recommendation
    4. Historical pace matchup analysis
    """
    
    # League averages (approximate for 2025-26)
    LEAGUE_AVG_PACE = 100.0
    LEAGUE_AVG_TOTAL = 225.0
    
    # Pace thresholds
    FAST_PACE_THRESHOLD = 10      # Top 10 = fast
    SLOW_PACE_THRESHOLD = 21      # Bottom 10 = slow
    
    # Total adjustment per pace point differential
    PACE_TO_POINTS_FACTOR = 2.2   # Each pace point = ~2.2 total points
    
    def __init__(self, season: str = None):
        """Initialize with NBA data fetcher."""
        self.fetcher = get_nba_fetcher(season)
        self.console = Console()
    
    def analyze_matchup(
        self,
        home_team: str,
        away_team: str,
        current_total: float = None,
        ref_crew_known: bool = False,
    ) -> TempoMatchupAnalysis:
        """
        Analyze pace/tempo for a game matchup.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            current_total: Current betting total (for edge calculation)
            ref_crew_known: Whether ref crew is known (for future integration)
            
        Returns:
            TempoMatchupAnalysis with projections
        """
        home_team = home_team.upper()
        away_team = away_team.upper()
        
        self.console.print(f"\n[bold cyan]🏃 Pace Analysis: {away_team} @ {home_team}[/bold cyan]")
        
        # Get pace data for both teams
        home_pace = self.fetcher.get_team_pace(home_team)
        away_pace = self.fetcher.get_team_pace(away_team)
        
        if not home_pace or not away_pace:
            return TempoMatchupAnalysis(
                home_team=home_team,
                away_team=away_team,
                home_pace=100,
                home_pace_rank=15,
                away_pace=100,
                away_pace_rank=15,
                projected_pace=100,
                league_avg_pace=self.LEAGUE_AVG_PACE,
                pace_differential=0,
                tempo_class="neutral",
                total_adjustment=0,
                total_lean="PASS",
                confidence="Low",
                home_pts_per_game=110,
                away_pts_per_game=110,
                home_opp_pts=110,
                away_opp_pts=110,
                projected_total=220,
                risk_factors=["Could not load pace data for one or both teams"],
            )
        
        # Calculate projected pace (average of both teams)
        projected_pace = (home_pace.pace + away_pace.pace) / 2
        pace_differential = projected_pace - self.LEAGUE_AVG_PACE
        
        # Display pace profiles
        self.console.print(Panel(
            f"[bold]{home_team}[/bold] (Home)\n"
            f"• Pace: {home_pace.pace:.1f} (Rank: {home_pace.pace_rank})\n"
            f"• OFF Rating: {home_pace.off_rating:.1f}\n"
            f"• DEF Rating: {home_pace.def_rating:.1f}\n"
            f"• PTS/Game: {home_pace.pts_per_game:.1f}\n"
            f"• Opp PTS: {home_pace.opp_pts_per_game:.1f}\n\n"
            f"[bold]{away_team}[/bold] (Away)\n"
            f"• Pace: {away_pace.pace:.1f} (Rank: {away_pace.pace_rank})\n"
            f"• OFF Rating: {away_pace.off_rating:.1f}\n"
            f"• DEF Rating: {away_pace.def_rating:.1f}\n"
            f"• PTS/Game: {away_pace.pts_per_game:.1f}\n"
            f"• Opp PTS: {away_pace.opp_pts_per_game:.1f}",
            title="Team Pace Profiles"
        ))
        
        # Determine tempo class
        edge_factors = []
        risk_factors = []
        
        if home_pace.is_fast_pace() and away_pace.is_fast_pace():
            tempo_class = "track_meet"
            edge_factors.append(f"🏃 TRACK MEET: Both teams top-10 pace (Ranks: {home_pace.pace_rank}, {away_pace.pace_rank})")
        elif home_pace.is_slow_pace() and away_pace.is_slow_pace():
            tempo_class = "grind"
            edge_factors.append(f"🐢 GRIND: Both teams bottom-10 pace (Ranks: {home_pace.pace_rank}, {away_pace.pace_rank})")
        elif home_pace.is_fast_pace() or away_pace.is_fast_pace():
            tempo_class = "pace_up"
            fast_team = home_team if home_pace.is_fast_pace() else away_team
            edge_factors.append(f"⬆️ {fast_team} should pace-up the game")
        elif home_pace.is_slow_pace() or away_pace.is_slow_pace():
            tempo_class = "pace_down"
            slow_team = home_team if home_pace.is_slow_pace() else away_team
            risk_factors.append(f"⬇️ {slow_team} tends to slow games down")
        else:
            tempo_class = "neutral"
        
        # Calculate total adjustment
        total_adjustment = pace_differential * self.PACE_TO_POINTS_FACTOR
        
        # Calculate projected total based on team averages
        # Method: Average of (home scoring + away scoring) adjusted for pace
        avg_home_total = home_pace.pts_per_game + home_pace.opp_pts_per_game
        avg_away_total = away_pace.pts_per_game + away_pace.opp_pts_per_game
        raw_projected_total = (avg_home_total + avg_away_total) / 2
        
        # Apply pace adjustment
        pace_adjusted_total = raw_projected_total + (total_adjustment * 0.5)  # Dampen adjustment
        
        # Determine lean
        if current_total:
            edge = pace_adjusted_total - current_total
            if tempo_class == "track_meet" and edge > 3:
                total_lean = "OVER"
                confidence = "High"
            elif tempo_class == "grind" and edge < -3:
                total_lean = "UNDER"
                confidence = "High"
            elif abs(edge) > 5:
                total_lean = "OVER" if edge > 0 else "UNDER"
                confidence = "Medium"
            elif abs(edge) > 2:
                total_lean = "OVER" if edge > 0 else "UNDER"
                confidence = "Low"
            else:
                total_lean = "PASS"
                confidence = "Low"
        else:
            # No current line to compare
            if tempo_class == "track_meet":
                total_lean = "OVER"
                confidence = "Medium"
            elif tempo_class == "grind":
                total_lean = "UNDER"
                confidence = "Medium"
            else:
                total_lean = "PASS"
                confidence = "Low"
        
        # Add context factors
        if home_pace.off_rating > 115 and away_pace.off_rating > 115:
            edge_factors.append("Both teams have elite offenses (115+ OFF RTG)")
        
        if home_pace.def_rating > 115 and away_pace.def_rating > 115:
            edge_factors.append("Both teams have poor defenses (115+ DEF RTG) - OVER friendly")
        
        if home_pace.def_rating < 108 and away_pace.def_rating < 108:
            risk_factors.append("Both teams have elite defenses (<108 DEF RTG) - UNDER friendly")
        
        return TempoMatchupAnalysis(
            home_team=home_team,
            away_team=away_team,
            home_pace=home_pace.pace,
            home_pace_rank=home_pace.pace_rank,
            away_pace=away_pace.pace,
            away_pace_rank=away_pace.pace_rank,
            projected_pace=round(projected_pace, 1),
            league_avg_pace=self.LEAGUE_AVG_PACE,
            pace_differential=round(pace_differential, 1),
            tempo_class=tempo_class,
            total_adjustment=round(total_adjustment, 1),
            total_lean=total_lean,
            confidence=confidence,
            home_pts_per_game=home_pace.pts_per_game,
            away_pts_per_game=away_pace.pts_per_game,
            home_opp_pts=home_pace.opp_pts_per_game,
            away_opp_pts=away_pace.opp_pts_per_game,
            projected_total=round(pace_adjusted_total, 1),
            edge_factors=edge_factors,
            risk_factors=risk_factors,
        )
    
    def print_analysis(self, analysis: TempoMatchupAnalysis):
        """Print analysis in formatted output."""
        # Summary table
        table = Table(title=f"🏀 {analysis.away_team} @ {analysis.home_team} Tempo Analysis")
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        
        table.add_row("Home Pace", f"{analysis.home_pace:.1f} (Rank: {analysis.home_pace_rank})")
        table.add_row("Away Pace", f"{analysis.away_pace:.1f} (Rank: {analysis.away_pace_rank})")
        table.add_row("Projected Pace", f"{analysis.projected_pace:.1f}")
        table.add_row("vs League Avg", f"{analysis.pace_differential:+.1f}")
        table.add_row("Tempo Class", analysis.tempo_class.replace("_", " ").upper())
        table.add_row("Total Adjustment", f"{analysis.total_adjustment:+.1f} pts")
        table.add_row("Projected Total", f"{analysis.projected_total:.1f}")
        
        self.console.print(table)
        
        # Recommendation
        action_color = "green" if analysis.total_lean in ["OVER", "UNDER"] else "yellow"
        self.console.print(f"\n[bold {action_color}]📊 LEAN: {analysis.total_lean}[/bold {action_color}] ({analysis.confidence} confidence)")
        
        # Edge factors
        if analysis.edge_factors:
            self.console.print("\n[bold green]✅ Edge Factors:[/bold green]")
            for edge in analysis.edge_factors:
                self.console.print(f"  • {edge}")
        
        # Risk factors
        if analysis.risk_factors:
            self.console.print("\n[bold red]⚠️ Risk Factors:[/bold red]")
            for risk in analysis.risk_factors:
                self.console.print(f"  • {risk}")
    
    def to_json(self, analysis: TempoMatchupAnalysis) -> str:
        """Convert analysis to JSON for agent tool response."""
        return json.dumps({
            "status": "success",
            "home_team": analysis.home_team,
            "away_team": analysis.away_team,
            "pace_analysis": {
                "home_pace": analysis.home_pace,
                "home_pace_rank": analysis.home_pace_rank,
                "away_pace": analysis.away_pace,
                "away_pace_rank": analysis.away_pace_rank,
                "projected_pace": analysis.projected_pace,
                "league_avg_pace": analysis.league_avg_pace,
                "pace_differential": analysis.pace_differential,
            },
            "total_analysis": {
                "tempo_class": analysis.tempo_class,
                "total_adjustment": analysis.total_adjustment,
                "projected_total": analysis.projected_total,
                "lean": analysis.total_lean,
                "confidence": analysis.confidence,
            },
            "scoring_context": {
                "home_pts_per_game": analysis.home_pts_per_game,
                "away_pts_per_game": analysis.away_pts_per_game,
                "home_opp_pts": analysis.home_opp_pts,
                "away_opp_pts": analysis.away_opp_pts,
            },
            "edge_factors": analysis.edge_factors,
            "risk_factors": analysis.risk_factors,
        }, indent=2)
    
    def get_best_pace_matchups(self, lean: str = "OVER") -> List[Dict[str, Any]]:
        """
        Find best pace matchups across the league.
        
        Args:
            lean: "OVER" for fast matchups, "UNDER" for slow matchups
            
        Returns:
            List of matchup suggestions
        """
        all_pace = self.fetcher.get_all_team_pace()
        
        if lean == "OVER":
            # Get fastest teams
            fast_teams = [p for p in all_pace if p.is_fast_pace()]
            return [{"team": p.team, "pace": p.pace, "rank": p.pace_rank} for p in fast_teams[:5]]
        else:
            # Get slowest teams
            slow_teams = [p for p in all_pace if p.is_slow_pace()]
            return [{"team": p.team, "pace": p.pace, "rank": p.pace_rank} for p in slow_teams[:5]]


def analyze_tempo(
    home: str,
    away: str,
    total: float = None
) -> TempoMatchupAnalysis:
    """
    Convenience function for tempo analysis.
    
    Args:
        home: Home team abbreviation
        away: Away team abbreviation
        total: Current betting total
        
    Returns:
        TempoMatchupAnalysis
    """
    analyzer = PaceTempoAnalyzer()
    analysis = analyzer.analyze_matchup(
        home_team=home,
        away_team=away,
        current_total=total,
    )
    analyzer.print_analysis(analysis)
    return analysis


if __name__ == "__main__":
    # Example: IND vs SAC - classic track meet
    analysis = analyze_tempo(
        home="SAC",
        away="IND",
        total=236.5
    )
