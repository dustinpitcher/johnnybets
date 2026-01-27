"""
Team Matchup Analyzer - Corsi/xG Engine for NHL Betting (Scaffold).

This module provides team-level matchup analysis using:
- Team Corsi% (shot attempt share / possession proxy)
- Expected Goals For/Against
- High-Danger Chances (HD CF%, HD CA%)
- Line combo analysis (placeholder for future)

Data source: MoneyPuck CSVs via NHLDataFetcher

Status: SCAFFOLD - Data structures and stubs implemented, 
        full analysis logic to be added in future iteration.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from rich.console import Console

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.nhl_data import NHLDataFetcher, TeamProfile, SkaterProfile, get_nhl_fetcher


@dataclass
class MatchupEdge:
    """Identifies which team has the edge in a specific category."""
    category: str                    # "possession", "xg", "high_danger", "special_teams"
    team_with_edge: str
    edge_magnitude: float           # How big the edge is (percentage points)
    confidence: str                 # "High", "Medium", "Low"
    notes: str = ""


@dataclass
class LineComboPrediction:
    """Placeholder for line combo analysis (future feature)."""
    line_number: int               # 1, 2, 3, 4
    center: str
    left_wing: str
    right_wing: str
    projected_xg: float
    projected_toi: float           # Time on ice (minutes)
    notes: str = ""


@dataclass
class TeamMatchupAnalysis:
    """Full team vs team matchup analysis."""
    home_team: str
    away_team: str
    home_profile: Optional[TeamProfile]
    away_profile: Optional[TeamProfile]
    edges: List[MatchupEdge]
    total_projection: Optional[float]      # Projected total goals
    spread_lean: Optional[str]             # Which team to lean
    spread_confidence: str
    notes: List[str]
    # Placeholder for future
    line_combos: Dict[str, List[LineComboPrediction]] = field(default_factory=dict)


class TeamMatchupAnalyzer:
    """
    Analyzes team matchups for NHL betting.
    
    SCAFFOLD: Core structure implemented, detailed analysis logic pending.
    
    Future features to add:
    - Line matchup analysis (top line vs shutdown D)
    - Special teams matchup breakdown
    - Recent form adjustments
    - Travel/schedule spots
    """
    
    def __init__(self, seasons: List[int] = None):
        """Initialize with NHL data fetcher (singleton to avoid duplicate downloads)."""
        self.fetcher = get_nhl_fetcher(seasons)
        self.console = Console()
    
    def analyze_matchup(
        self,
        home_team: str,
        away_team: str,
        season: int = None
    ) -> TeamMatchupAnalysis:
        """
        Analyze a team matchup for betting insights.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            season: Season year
            
        Returns:
            TeamMatchupAnalysis with edges and projections
        """
        season = season or self.fetcher.seasons[0]
        
        self.console.print(f"\n[bold cyan]🏒 Matchup Analysis: {away_team} @ {home_team}[/bold cyan]")
        
        # Get team profiles
        home_profile = self.fetcher.get_team_profile(home_team, season)
        away_profile = self.fetcher.get_team_profile(away_team, season)
        
        edges = []
        notes = []
        
        if not home_profile or not away_profile:
            notes.append("Warning: Could not load complete team profiles")
            return TeamMatchupAnalysis(
                home_team=home_team,
                away_team=away_team,
                home_profile=home_profile,
                away_profile=away_profile,
                edges=[],
                total_projection=None,
                spread_lean=None,
                spread_confidence="Low",
                notes=notes,
            )
        
        # Calculate edges
        edges = self._calculate_edges(home_team, away_team, home_profile, away_profile)
        
        # Project total
        total_projection = self._project_total(home_profile, away_profile)
        
        # Determine spread lean
        spread_lean, spread_confidence = self._determine_spread_lean(edges, home_profile, away_profile)
        
        # Add matchup notes
        notes.extend(self._generate_notes(home_team, away_team, home_profile, away_profile))
        
        return TeamMatchupAnalysis(
            home_team=home_team,
            away_team=away_team,
            home_profile=home_profile,
            away_profile=away_profile,
            edges=edges,
            total_projection=total_projection,
            spread_lean=spread_lean,
            spread_confidence=spread_confidence,
            notes=notes,
        )
    
    def _calculate_edges(
        self,
        home_team: str,
        away_team: str,
        home: TeamProfile,
        away: TeamProfile
    ) -> List[MatchupEdge]:
        """Calculate which team has edges in key categories."""
        edges = []
        
        # Possession edge (Corsi%)
        corsi_diff = home.corsi_pct - away.corsi_pct
        if abs(corsi_diff) > 2:
            edges.append(MatchupEdge(
                category="possession",
                team_with_edge=home_team if corsi_diff > 0 else away_team,
                edge_magnitude=abs(corsi_diff),
                confidence="High" if abs(corsi_diff) > 4 else "Medium",
                notes=f"Corsi%: {home_team} {home.corsi_pct:.1f}% vs {away_team} {away.corsi_pct:.1f}%"
            ))
        
        # xG edge
        xg_diff = home.xg_diff_per_game - away.xg_diff_per_game
        if abs(xg_diff) > 0.3:
            edges.append(MatchupEdge(
                category="xg",
                team_with_edge=home_team if xg_diff > 0 else away_team,
                edge_magnitude=abs(xg_diff),
                confidence="High" if abs(xg_diff) > 0.5 else "Medium",
                notes=f"xG Diff: {home_team} {home.xg_diff_per_game:+.2f} vs {away_team} {away.xg_diff_per_game:+.2f}"
            ))
        
        # High-danger edge
        hd_diff = home.hd_pct - away.hd_pct
        if abs(hd_diff) > 3:
            edges.append(MatchupEdge(
                category="high_danger",
                team_with_edge=home_team if hd_diff > 0 else away_team,
                edge_magnitude=abs(hd_diff),
                confidence="High" if abs(hd_diff) > 5 else "Medium",
                notes=f"HD%: {home_team} {home.hd_pct:.1f}% vs {away_team} {away.hd_pct:.1f}%"
            ))
        
        # Special teams (if data available)
        if home.pp_pct > 0 and away.pk_pct > 0:
            home_pp_edge = home.pp_pct - (100 - away.pk_pct)
            if abs(home_pp_edge) > 5:
                edges.append(MatchupEdge(
                    category="special_teams",
                    team_with_edge=home_team if home_pp_edge > 0 else away_team,
                    edge_magnitude=abs(home_pp_edge),
                    confidence="Medium",
                    notes=f"{home_team} PP {home.pp_pct:.1f}% vs {away_team} PK {away.pk_pct:.1f}%"
                ))
        
        return edges
    
    def _project_total(self, home: TeamProfile, away: TeamProfile) -> float:
        """Project total goals for the game."""
        # Simple projection: average of both teams' xGF + opponent xGA tendencies
        home_expected = (home.xg_for_per_game + away.xg_against_per_game) / 2
        away_expected = (away.xg_for_per_game + home.xg_against_per_game) / 2
        
        # Add home ice advantage (slight boost to home team)
        home_expected *= 1.02
        
        return round(home_expected + away_expected, 1)
    
    def _determine_spread_lean(
        self,
        edges: List[MatchupEdge],
        home: TeamProfile,
        away: TeamProfile
    ) -> tuple[Optional[str], str]:
        """Determine which team to lean on the spread."""
        if not edges:
            return None, "Low"
        
        # Count edges for each team
        home_edges = sum(1 for e in edges if e.team_with_edge == home.team)
        away_edges = len(edges) - home_edges
        
        # Weight by confidence
        home_score = sum(
            2 if e.confidence == "High" else 1 
            for e in edges if e.team_with_edge == home.team
        )
        away_score = sum(
            2 if e.confidence == "High" else 1 
            for e in edges if e.team_with_edge != home.team
        )
        
        if home_score > away_score + 1:
            return home.team, "Medium" if home_score > away_score + 2 else "Low"
        elif away_score > home_score + 1:
            return away.team, "Medium" if away_score > home_score + 2 else "Low"
        
        return None, "Low"
    
    def _generate_notes(
        self,
        home_team: str,
        away_team: str,
        home: TeamProfile,
        away: TeamProfile
    ) -> List[str]:
        """Generate betting-relevant notes about the matchup."""
        notes = []
        
        # Style matchup
        home_style = home.get_style()
        away_style = away.get_style()
        notes.append(f"Style: {home_team} ({home_style}) vs {away_team} ({away_style})")
        
        # Pace indicator
        combined_corsi = home.corsi_for_per_game + away.corsi_for_per_game
        if combined_corsi > 120:
            notes.append("High pace matchup - lean over on totals")
        elif combined_corsi < 100:
            notes.append("Low pace matchup - consider under on totals")
        
        # Goal differential
        if abs(home.goals_for_per_game - home.goals_against_per_game) > 0.5:
            if home.goals_for_per_game > home.goals_against_per_game:
                notes.append(f"{home_team} outscoring opponents by {home.goals_for_per_game - home.goals_against_per_game:.1f}/game")
            else:
                notes.append(f"{home_team} being outscored by {home.goals_against_per_game - home.goals_for_per_game:.1f}/game")
        
        return notes
    
    def to_json(self, analysis: TeamMatchupAnalysis) -> str:
        """Convert analysis to JSON for agent tool response."""
        return json.dumps({
            "status": "success",
            "scaffold_note": "This is a scaffold implementation - full analysis coming soon",
            "matchup": f"{analysis.away_team} @ {analysis.home_team}",
            "home_profile": {
                "team": analysis.home_profile.team,
                "corsi_pct": analysis.home_profile.corsi_pct,
                "xg_for": analysis.home_profile.xg_for_per_game,
                "xg_against": analysis.home_profile.xg_against_per_game,
                "xg_diff": analysis.home_profile.xg_diff_per_game,
                "hd_pct": analysis.home_profile.hd_pct,
                "style": analysis.home_profile.get_style(),
            } if analysis.home_profile else None,
            "away_profile": {
                "team": analysis.away_profile.team,
                "corsi_pct": analysis.away_profile.corsi_pct,
                "xg_for": analysis.away_profile.xg_for_per_game,
                "xg_against": analysis.away_profile.xg_against_per_game,
                "xg_diff": analysis.away_profile.xg_diff_per_game,
                "hd_pct": analysis.away_profile.hd_pct,
                "style": analysis.away_profile.get_style(),
            } if analysis.away_profile else None,
            "edges": [
                {
                    "category": e.category,
                    "team_with_edge": e.team_with_edge,
                    "magnitude": e.edge_magnitude,
                    "confidence": e.confidence,
                    "notes": e.notes,
                }
                for e in analysis.edges
            ],
            "total_projection": analysis.total_projection,
            "spread_lean": analysis.spread_lean,
            "spread_confidence": analysis.spread_confidence,
            "notes": analysis.notes,
        }, indent=2)


def analyze_teams(home: str, away: str) -> TeamMatchupAnalysis:
    """Convenience function for team matchup analysis."""
    analyzer = TeamMatchupAnalyzer()
    return analyzer.analyze_matchup(home, away)


if __name__ == "__main__":
    # Example: Rangers vs Maple Leafs
    analysis = analyze_teams("NYR", "TOR")
    analyzer = TeamMatchupAnalyzer()
    print(analyzer.to_json(analysis))

