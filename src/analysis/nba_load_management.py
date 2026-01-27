"""
NBA Load Management & Minutes Tracker - NBA's "Bullpen Analyzer".

This module tracks player load and projects minutes:
- Rest days analysis (0/1/2/3+ days)
- Back-to-back performance splits
- Fatigue index (games in last 7/14 days)
- Projected minutes based on rotation history
- "Phantom DNP" risk flags (load management patterns)
- Season phase awareness (stars rest more late season)

Critical for NBA prop betting where stars may sit or see reduced minutes.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.nba_data import NBADataFetcher, NBAPlayerProfile, get_nba_fetcher


@dataclass
class LoadProfile:
    """Player load management profile."""
    player: str
    team: str
    
    # Basic info
    age: int = 0
    games_played: int = 0
    season_phase: str = "regular"  # "early", "regular", "late", "playoff_push"
    
    # Rest analysis
    current_rest_days: int = 0     # Days since last game
    avg_rest_days: float = 0       # Average rest between games
    
    # B2B stats
    b2b_games_played: int = 0
    b2b_games_sat: int = 0         # DNPs on B2Bs
    b2b_pts_avg: float = 0
    b2b_min_avg: float = 0
    rested_pts_avg: float = 0
    rested_min_avg: float = 0
    b2b_performance_delta: float = 0  # % drop on B2Bs
    
    # Fatigue metrics
    games_last_7: int = 0
    games_last_14: int = 0
    minutes_last_7: float = 0
    fatigue_index: str = "LOW"     # "LOW", "MEDIUM", "HIGH", "EXTREME"
    
    # Minutes projection
    season_avg_min: float = 0
    recent_avg_min: float = 0      # Last 5 games
    projected_min: float = 0
    min_trend: str = "stable"      # "up", "down", "stable"
    
    # DNP risk
    dnp_risk: str = "LOW"          # "LOW", "MEDIUM", "HIGH"
    dnp_risk_factors: List[str] = field(default_factory=list)
    
    def is_high_volume(self) -> bool:
        """Check if player is high volume (30+ MPG)."""
        return self.season_avg_min >= 30
    
    def is_fatigued(self) -> bool:
        """Check if player shows fatigue signals."""
        return self.fatigue_index in ["HIGH", "EXTREME"]


@dataclass
class LoadManagementAnalysis:
    """Complete load management analysis."""
    player: str
    team: str
    load_profile: LoadProfile
    is_back_to_back: bool
    opponent: str
    
    # Projections
    projected_minutes: float
    minutes_confidence: str
    
    # Risk assessment
    overall_risk: str              # "PLAY", "CAUTION", "FADE"
    risk_factors: List[str]
    edge_factors: List[str]
    
    # Historical context
    b2b_hit_rate_over: float = 0   # % of B2Bs where player hits prop overs
    rested_hit_rate_over: float = 0


class LoadManagementTracker:
    """
    Tracks player load and projects minutes/availability.
    
    Key features:
    1. Rest days analysis with B2B splits
    2. Fatigue index calculation
    3. Minutes projection model
    4. DNP risk assessment
    5. Season phase awareness
    """
    
    # Fatigue thresholds
    FATIGUE_HIGH_GAMES_7 = 4       # 4+ games in 7 days = HIGH fatigue
    FATIGUE_EXTREME_GAMES_7 = 5    # 5 games in 7 days = EXTREME
    FATIGUE_HIGH_MINUTES_7 = 150   # 150+ minutes in 7 days
    
    # B2B performance expectations
    AVG_B2B_PTS_DROP = 0.08        # ~8% drop in scoring on B2Bs
    AVG_B2B_MIN_DROP = 0.05        # ~5% drop in minutes on B2Bs
    
    # DNP risk factors
    DNP_AGE_THRESHOLD = 33         # 33+ year olds more likely to rest
    DNP_HIGH_VOLUME_MIN = 34       # High volume players may rest
    
    def __init__(self, season: str = None):
        """Initialize with NBA data fetcher."""
        self.fetcher = get_nba_fetcher(season)
        self.console = Console()
    
    def _get_season_phase(self) -> str:
        """Determine current season phase."""
        now = datetime.now()
        month = now.month
        
        if month in [10, 11]:
            return "early"
        elif month in [12, 1, 2]:
            return "regular"
        elif month == 3:
            return "late"
        elif month in [4, 5, 6]:
            return "playoff_push"
        else:
            return "offseason"
    
    def _calculate_fatigue_index(
        self, 
        games_last_7: int, 
        minutes_last_7: float
    ) -> str:
        """Calculate fatigue index based on workload."""
        if games_last_7 >= self.FATIGUE_EXTREME_GAMES_7:
            return "EXTREME"
        elif games_last_7 >= self.FATIGUE_HIGH_GAMES_7 or minutes_last_7 >= self.FATIGUE_HIGH_MINUTES_7:
            return "HIGH"
        elif games_last_7 >= 3 or minutes_last_7 >= 100:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _assess_dnp_risk(
        self,
        profile: NBAPlayerProfile,
        is_b2b: bool,
        season_phase: str,
        fatigue_index: str,
        b2b_sat_rate: float,
    ) -> tuple[str, List[str]]:
        """Assess DNP (Did Not Play) risk."""
        risk_factors = []
        risk_score = 0
        
        # Age factor
        # Note: nba_api doesn't provide age directly, we'd need additional lookup
        # For now, we'll skip age-based assessment or use a placeholder
        
        # B2B factor
        if is_b2b:
            risk_score += 2
            risk_factors.append("Back-to-back game")
            
            # Historical B2B sit rate
            if b2b_sat_rate > 0.3:
                risk_score += 2
                risk_factors.append(f"Historically sits {b2b_sat_rate:.0%} of B2Bs")
        
        # Season phase factor
        if season_phase == "late" and profile.min_per_game > 32:
            risk_score += 1
            risk_factors.append("Late season + high usage = rest risk")
        
        # Fatigue factor
        if fatigue_index == "EXTREME":
            risk_score += 2
            risk_factors.append("EXTREME fatigue level")
        elif fatigue_index == "HIGH":
            risk_score += 1
            risk_factors.append("HIGH fatigue level")
        
        # High volume factor
        if profile.min_per_game >= self.DNP_HIGH_VOLUME_MIN:
            if is_b2b:
                risk_score += 1
                risk_factors.append(f"High volume ({profile.min_per_game:.1f} MPG) on B2B")
        
        # Determine risk level
        if risk_score >= 4:
            return "HIGH", risk_factors
        elif risk_score >= 2:
            return "MEDIUM", risk_factors
        else:
            return "LOW", risk_factors
    
    def analyze_load(
        self,
        player_name: str,
        team: str = None,
        is_back_to_back: bool = False,
        opponent: str = None,
    ) -> LoadManagementAnalysis:
        """
        Analyze player load and project minutes.
        
        Args:
            player_name: Player name
            team: Team abbreviation (optional, for context)
            is_back_to_back: Whether this is a B2B game
            opponent: Opponent team (optional)
            
        Returns:
            LoadManagementAnalysis with projections
        """
        self.console.print(f"\n[bold cyan]📊 Load Analysis: {player_name}[/bold cyan]")
        if is_back_to_back:
            self.console.print("[yellow]⚠️ BACK-TO-BACK GAME[/yellow]")
        
        # Get player profile
        player_profile = self.fetcher.get_player_profile(player_name)
        if not player_profile:
            return LoadManagementAnalysis(
                player=player_name,
                team=team or "UNK",
                load_profile=LoadProfile(player=player_name, team=team or "UNK"),
                is_back_to_back=is_back_to_back,
                opponent=opponent or "UNK",
                projected_minutes=0,
                minutes_confidence="Low",
                overall_risk="CAUTION",
                risk_factors=["Player not found in database"],
                edge_factors=[],
            )
        
        team = player_profile.team
        
        # Get rest day analysis
        rest_analysis = self.fetcher.get_player_rest_days(player_name)
        
        # Get season phase
        season_phase = self._get_season_phase()
        
        # Extract metrics from rest analysis
        b2b_games = rest_analysis.get("b2b_games", 0)
        b2b_pts = rest_analysis.get("b2b_avg_pts", player_profile.pts_per_game)
        b2b_min = rest_analysis.get("b2b_avg_min", player_profile.min_per_game)
        rested_pts = rest_analysis.get("rested_avg_pts", player_profile.pts_per_game)
        rested_min = rest_analysis.get("rested_avg_min", player_profile.min_per_game)
        games_last_7 = rest_analysis.get("games_last_7_days", 0)
        
        # Calculate fatigue
        minutes_last_7 = games_last_7 * player_profile.min_per_game
        fatigue_index = self._calculate_fatigue_index(games_last_7, minutes_last_7)
        
        # B2B performance delta
        if rested_pts > 0:
            b2b_pts_delta = (b2b_pts - rested_pts) / rested_pts
        else:
            b2b_pts_delta = -self.AVG_B2B_PTS_DROP
        
        # Minutes trend
        recent_min = player_profile.min_per_game  # Would use L5 if available
        if recent_min > player_profile.min_per_game * 1.05:
            min_trend = "up"
        elif recent_min < player_profile.min_per_game * 0.95:
            min_trend = "down"
        else:
            min_trend = "stable"
        
        # Project minutes
        projected_min = player_profile.min_per_game
        if is_back_to_back:
            projected_min *= (1 - self.AVG_B2B_MIN_DROP)
        if fatigue_index in ["HIGH", "EXTREME"]:
            projected_min *= 0.95
        
        # Assess DNP risk
        b2b_sat_rate = 0  # Would need historical data
        dnp_risk, dnp_factors = self._assess_dnp_risk(
            player_profile, is_back_to_back, season_phase, fatigue_index, b2b_sat_rate
        )
        
        # Build load profile
        load_profile = LoadProfile(
            player=player_name,
            team=team,
            games_played=player_profile.games_played,
            season_phase=season_phase,
            b2b_games_played=b2b_games,
            b2b_pts_avg=round(b2b_pts, 1),
            b2b_min_avg=round(b2b_min, 1),
            rested_pts_avg=round(rested_pts, 1),
            rested_min_avg=round(rested_min, 1),
            b2b_performance_delta=round(b2b_pts_delta * 100, 1),
            games_last_7=games_last_7,
            games_last_14=games_last_7 * 2,  # Approximate
            minutes_last_7=round(minutes_last_7, 1),
            fatigue_index=fatigue_index,
            season_avg_min=player_profile.min_per_game,
            recent_avg_min=recent_min,
            projected_min=round(projected_min, 1),
            min_trend=min_trend,
            dnp_risk=dnp_risk,
            dnp_risk_factors=dnp_factors,
        )
        
        # Display load profile
        self.console.print(Panel(
            f"[bold]{player_name}[/bold] ({team})\n\n"
            f"Season Phase: {season_phase.upper()}\n"
            f"Games Played: {player_profile.games_played}\n\n"
            f"[bold]Minutes:[/bold]\n"
            f"• Season Avg: {player_profile.min_per_game:.1f}\n"
            f"• Projected: {projected_min:.1f}\n"
            f"• Trend: {min_trend.upper()}\n\n"
            f"[bold]Fatigue:[/bold]\n"
            f"• Games Last 7 Days: {games_last_7}\n"
            f"• Minutes Last 7 Days: {minutes_last_7:.0f}\n"
            f"• Fatigue Index: {fatigue_index}\n\n"
            f"[bold]B2B Splits:[/bold]\n"
            f"• B2B Games: {b2b_games}\n"
            f"• B2B PTS Avg: {b2b_pts:.1f}\n"
            f"• Rested PTS Avg: {rested_pts:.1f}\n"
            f"• B2B Delta: {b2b_pts_delta * 100:+.1f}%",
            title="Load Profile"
        ))
        
        # Determine overall risk
        risk_factors = dnp_factors.copy()
        edge_factors = []
        
        if is_back_to_back:
            if b2b_pts_delta < -0.1:
                risk_factors.append(f"Significant B2B drop: {b2b_pts_delta * 100:.1f}%")
            elif b2b_pts_delta > 0:
                edge_factors.append(f"Player performs well on B2Bs: {b2b_pts_delta * 100:+.1f}%")
        
        if fatigue_index == "LOW":
            edge_factors.append("Well-rested player")
        
        if min_trend == "up":
            edge_factors.append("Minutes trending UP recently")
        elif min_trend == "down":
            risk_factors.append("Minutes trending DOWN recently")
        
        # Overall risk assessment
        if dnp_risk == "HIGH":
            overall_risk = "FADE"
        elif dnp_risk == "MEDIUM" or fatigue_index in ["HIGH", "EXTREME"]:
            overall_risk = "CAUTION"
        else:
            overall_risk = "PLAY"
        
        # Minutes confidence
        if dnp_risk == "LOW" and fatigue_index in ["LOW", "MEDIUM"]:
            min_confidence = "High"
        elif dnp_risk == "MEDIUM" or fatigue_index == "HIGH":
            min_confidence = "Medium"
        else:
            min_confidence = "Low"
        
        return LoadManagementAnalysis(
            player=player_name,
            team=team,
            load_profile=load_profile,
            is_back_to_back=is_back_to_back,
            opponent=opponent or "UNK",
            projected_minutes=round(projected_min, 1),
            minutes_confidence=min_confidence,
            overall_risk=overall_risk,
            risk_factors=risk_factors,
            edge_factors=edge_factors,
        )
    
    def print_analysis(self, analysis: LoadManagementAnalysis):
        """Print analysis in formatted output."""
        # Summary
        risk_color = {
            "PLAY": "green",
            "CAUTION": "yellow",
            "FADE": "red"
        }.get(analysis.overall_risk, "white")
        
        self.console.print(f"\n[bold {risk_color}]📊 OVERALL: {analysis.overall_risk}[/bold {risk_color}]")
        self.console.print(f"Projected Minutes: {analysis.projected_minutes:.1f} ({analysis.minutes_confidence} confidence)")
        
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
    
    def to_json(self, analysis: LoadManagementAnalysis) -> str:
        """Convert analysis to JSON for agent tool response."""
        lp = analysis.load_profile
        return json.dumps({
            "status": "success",
            "player": analysis.player,
            "team": analysis.team,
            "is_back_to_back": analysis.is_back_to_back,
            "opponent": analysis.opponent,
            "load_profile": {
                "season_phase": lp.season_phase,
                "games_played": lp.games_played,
                "fatigue_index": lp.fatigue_index,
                "games_last_7": lp.games_last_7,
                "minutes_last_7": lp.minutes_last_7,
                "b2b_games": lp.b2b_games_played,
                "b2b_pts_avg": lp.b2b_pts_avg,
                "b2b_min_avg": lp.b2b_min_avg,
                "rested_pts_avg": lp.rested_pts_avg,
                "rested_min_avg": lp.rested_min_avg,
                "b2b_performance_delta": lp.b2b_performance_delta,
                "season_avg_min": lp.season_avg_min,
                "min_trend": lp.min_trend,
                "dnp_risk": lp.dnp_risk,
                "dnp_risk_factors": lp.dnp_risk_factors,
            },
            "projections": {
                "projected_minutes": analysis.projected_minutes,
                "minutes_confidence": analysis.minutes_confidence,
            },
            "overall_risk": analysis.overall_risk,
            "risk_factors": analysis.risk_factors,
            "edge_factors": analysis.edge_factors,
        }, indent=2)


def analyze_load(
    player: str,
    team: str = None,
    is_b2b: bool = False,
    opponent: str = None
) -> LoadManagementAnalysis:
    """
    Convenience function for load management analysis.
    
    Args:
        player: Player name
        team: Team abbreviation
        is_b2b: Whether this is a back-to-back
        opponent: Opponent team
        
    Returns:
        LoadManagementAnalysis
    """
    tracker = LoadManagementTracker()
    analysis = tracker.analyze_load(
        player_name=player,
        team=team,
        is_back_to_back=is_b2b,
        opponent=opponent,
    )
    tracker.print_analysis(analysis)
    return analysis


if __name__ == "__main__":
    # Example: LeBron on a back-to-back
    analysis = analyze_load(
        player="LeBron James",
        team="LAL",
        is_b2b=True,
        opponent="DEN"
    )
