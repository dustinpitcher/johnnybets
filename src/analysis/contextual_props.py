"""
Contextual Props Analyzer - The "Alpha" Logic for Prop Betting (v2.0 - Data-Driven).

This module calculates contextual splits to find edges in player props:
- QB performance vs DATA-DRIVEN defensive profiles (not hardcoded)
- Weather-adjusted projections
- Game script correlations (leading vs trailing)
- Altitude adjustments
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.nfl_data import NFLDataFetcher, DefenseProfile


@dataclass
class PropProjection:
    """A projected prop line with contextual analysis."""
    player: str
    prop_type: str
    standard_projection: float
    contextual_projection: float
    current_line: Optional[float] = None
    edge: Optional[float] = None
    confidence: str = "Medium"
    reasoning: str = ""
    adjustments: list = field(default_factory=list)
    
    def __post_init__(self):
        if self.current_line:
            self.edge = self.contextual_projection - self.current_line


@dataclass
class MatchupAnalysis:
    """Full matchup analysis with multiple data sources."""
    player: str
    opponent: str
    opponent_profile: DefenseProfile
    similar_defenses: list  # (team, similarity, profile) tuples
    weather_splits: dict
    game_script_splits: dict
    projections: list  # PropProjection list


class ContextualPropsAnalyzer:
    """
    Analyzes player props using DATA-DRIVEN contextual splits.
    
    v2.0 Changes:
    - Defense profiles calculated from actual play-by-play data
    - Similar defenses found via similarity scoring, not hardcoded lists
    - Weather adjustments based on historical performance
    - Game script integration
    """
    
    # Teams with notable altitude (Denver)
    ALTITUDE_TEAMS = {'DEN': 5280}  # feet
    
    def __init__(self, years: list[int] = None):
        """Initialize with data fetcher."""
        self.fetcher = NFLDataFetcher(years or [2023, 2024, 2025])
        self.console = Console()
    
    def analyze_qb_vs_defense_profile(
        self,
        qb_name: str,
        opponent_team: str,
        current_lines: dict = None,
        game_weather: dict = None  # {"wind": 15, "temp": 35}
    ) -> list[PropProjection]:
        """
        Analyze a QB's projected performance vs a specific opponent's defensive profile.
        
        Now uses DATA-DRIVEN defense profiling instead of hardcoded lists.
        
        Args:
            qb_name: QB name (e.g., "J.Allen" or "Josh Allen")
            opponent_team: Team abbreviation (e.g., "DEN")
            current_lines: Dict of prop lines e.g. {"passing_yards": 265.5, "passing_tds": 1.5}
            game_weather: Expected game weather {"wind": mph, "temp": F}
            
        Returns:
            List of PropProjection objects with edges identified
        """
        current_lines = current_lines or {}
        projections = []
        
        self.console.print(f"\n[bold cyan]🎯 Analyzing {qb_name} vs {opponent_team}[/bold cyan]")
        self.console.print("[dim]Using data-driven defense profiling...[/dim]\n")
        
        seasons = tuple(self.fetcher.years)
        
        # Get opponent's defense profile (CALCULATED FROM DATA)
        opponent_profile = self.fetcher.calculate_defense_profile(opponent_team, seasons)
        
        self.console.print(Panel(
            f"[bold]{opponent_team} Defense Profile[/bold] (from {opponent_profile.total_plays:,} pass plays)\n\n"
            f"• Sack Rate: {opponent_profile.sack_rate:.1f}%\n"
            f"• Completion % Allowed: {opponent_profile.completion_pct_allowed:.1f}%\n"
            f"• Avg Air Yards Allowed: {opponent_profile.avg_air_yards_allowed:.1f}\n"
            f"• Yards/Attempt Allowed: {opponent_profile.yards_per_attempt_allowed:.1f}\n\n"
            f"Style: {'🔥 Aggressive' if opponent_profile.is_aggressive else ''}"
            f"{'🛡️ Zone-Heavy' if opponent_profile.is_zone_heavy else ''}"
            f"{'⚡ Blitz-Heavy' if opponent_profile.is_blitz_heavy else ''}"
            f"{'📊 Balanced' if not any([opponent_profile.is_aggressive, opponent_profile.is_zone_heavy, opponent_profile.is_blitz_heavy]) else ''}",
            title="Defense Analysis"
        ))
        
        # Find similar defenses (DATA-DRIVEN)
        similar_defenses = self.fetcher.find_similar_defenses(opponent_team, top_n=5, seasons=seasons)
        similar_teams = [t[0] for t in similar_defenses]
        
        self.console.print(f"\n🔍 [bold]Similar Defenses (by data profile):[/bold]")
        for team, similarity, profile in similar_defenses:
            self.console.print(
                f"   {team}: {similarity:.0%} similar "
                f"(Sack: {profile.sack_rate:.1f}%, AirYds: {profile.avg_air_yards_allowed:.1f})"
            )
        
        # Get QB's play-by-play data
        qb_plays = self.fetcher.get_player_plays(qb_name, "QB", seasons)
        
        if qb_plays.empty:
            self.console.print(f"[red]No data found for {qb_name}[/red]")
            return projections
        
        # Calculate standard season averages
        qb_games = qb_plays.groupby('game_id').agg({
            'passing_yards': 'sum',
            'pass_touchdown': 'sum',
            'complete_pass': 'sum',
            'interception': 'sum',
            'air_yards': 'mean',
        }).reset_index()
        
        standard_passing_yards = qb_games['passing_yards'].mean()
        standard_passing_tds = qb_games['pass_touchdown'].mean()
        
        self.console.print(f"\n📊 [bold]Standard Season Averages:[/bold]")
        self.console.print(f"   Passing Yards/Game: {standard_passing_yards:.1f}")
        self.console.print(f"   Passing TDs/Game: {standard_passing_tds:.2f}")
        
        # Calculate performance vs similar defenses
        vs_similar = qb_plays[qb_plays['defteam'].isin(similar_teams)]
        adjustments = []
        
        if not vs_similar.empty and len(vs_similar) > 50:  # Need meaningful sample
            vs_similar_games = vs_similar.groupby('game_id').agg({
                'passing_yards': 'sum',
                'pass_touchdown': 'sum',
            }).reset_index()
            
            contextual_passing_yards = vs_similar_games['passing_yards'].mean()
            contextual_passing_tds = vs_similar_games['pass_touchdown'].mean()
            
            self.console.print(f"\n📊 [bold]vs Similar Defenses ({len(vs_similar_games)} games):[/bold]")
            self.console.print(f"   Passing Yards/Game: {contextual_passing_yards:.1f}")
            self.console.print(f"   Passing TDs/Game: {contextual_passing_tds:.2f}")
            
            adjustments.append(f"vs similar defenses: {contextual_passing_yards:.0f} yds")
        else:
            contextual_passing_yards = standard_passing_yards
            contextual_passing_tds = standard_passing_tds
            self.console.print(f"\n[yellow]⚠️ Limited games vs similar defenses, using season average[/yellow]")
        
        # WEATHER ADJUSTMENTS
        if game_weather:
            wind = game_weather.get('wind', 0)
            temp = game_weather.get('temp', 70)
            
            weather_splits = self.fetcher.get_player_weather_splits(qb_name, "QB", seasons)
            
            if wind >= 15 and 'high_wind_15mph+' in weather_splits:
                hw = weather_splits['high_wind_15mph+']
                wind_adjustment = hw['avg_passing_yards'] / standard_passing_yards
                contextual_passing_yards *= wind_adjustment
                adjustments.append(f"wind {wind}mph: {wind_adjustment:.0%}")
                self.console.print(f"\n🌬️ [bold]Wind Adjustment ({wind}mph):[/bold] {wind_adjustment:.0%}")
                self.console.print(f"   Avg in high wind: {hw['avg_passing_yards']:.1f} yds")
            
            if temp < 40 and 'cold_<40F' in weather_splits:
                cold = weather_splits['cold_<40F']
                cold_adjustment = cold['avg_passing_yards'] / standard_passing_yards
                contextual_passing_yards *= cold_adjustment
                adjustments.append(f"cold {temp}F: {cold_adjustment:.0%}")
                self.console.print(f"\n❄️ [bold]Cold Weather Adjustment ({temp}°F):[/bold] {cold_adjustment:.0%}")
        
        # ALTITUDE ADJUSTMENT
        if opponent_team in self.ALTITUDE_TEAMS:
            altitude_boost = 1.03  # 3% boost at altitude
            contextual_passing_yards *= altitude_boost
            adjustments.append(f"altitude: +3%")
            self.console.print(f"\n🏔️ [bold]Altitude Adjustment ({opponent_team}):[/bold] +3%")
        
        # Build projections
        projections.append(PropProjection(
            player=qb_name,
            prop_type="Passing Yards",
            standard_projection=standard_passing_yards,
            contextual_projection=contextual_passing_yards,
            current_line=current_lines.get("passing_yards"),
            confidence=self._calculate_confidence(standard_passing_yards, contextual_passing_yards),
            reasoning=f"vs {opponent_team}-profile defenses with adjustments: {', '.join(adjustments) if adjustments else 'none'}",
            adjustments=adjustments
        ))
        
        projections.append(PropProjection(
            player=qb_name,
            prop_type="Passing TDs",
            standard_projection=standard_passing_tds,
            contextual_projection=contextual_passing_tds,
            current_line=current_lines.get("passing_tds"),
            confidence=self._calculate_confidence(standard_passing_tds, contextual_passing_tds),
            reasoning=f"vs {opponent_team}-profile defenses",
            adjustments=adjustments
        ))
        
        return projections
    
    def analyze_with_game_script(
        self,
        player_name: str,
        position: str,
        expected_script: str,  # "winning", "losing", "close"
        current_lines: dict = None
    ) -> list[PropProjection]:
        """
        Analyze player with expected game script factored in.
        
        Key insight: RBs get more touches when winning, QBs throw more when trailing.
        """
        current_lines = current_lines or {}
        projections = []
        seasons = tuple(self.fetcher.years)
        
        self.console.print(f"\n[bold cyan]📈 Game Script Analysis: {player_name} ({position})[/bold cyan]")
        self.console.print(f"   Expected game script: [bold]{expected_script.upper()}[/bold]\n")
        
        # Get game script splits
        splits = self.fetcher.get_player_game_script_splits(player_name, position, seasons)
        
        if 'error' in splits:
            self.console.print(f"[red]{splits['error']}[/red]")
            return projections
        
        # Display splits
        script_map = {
            'winning': 'winning_7+',
            'losing': 'losing_7+',
            'close': 'close_game'
        }
        
        self.console.print("[bold]Game Script Splits:[/bold]")
        for script_name, script_data in splits.items():
            self.console.print(f"   {script_name}: {script_data}")
        
        # Get the expected scenario
        scenario_key = script_map.get(expected_script, 'close_game')
        
        if scenario_key in splits:
            scenario = splits[scenario_key]
            
            if position == "QB":
                contextual = scenario.get('avg_passing_yards', 0)
                # Get standard
                all_scenarios = [s.get('avg_passing_yards', 0) for s in splits.values() if 'avg_passing_yards' in s]
                standard = np.mean(all_scenarios) if all_scenarios else contextual
                
                projections.append(PropProjection(
                    player=player_name,
                    prop_type="Passing Yards",
                    standard_projection=standard,
                    contextual_projection=contextual,
                    current_line=current_lines.get("passing_yards"),
                    confidence=self._calculate_confidence(standard, contextual),
                    reasoning=f"Expected {expected_script} game script → {contextual:.0f} yds"
                ))
                
            elif position == "RB":
                contextual_yards = scenario.get('avg_rushing_yards', 0)
                contextual_carries = scenario.get('avg_carries', 0)
                
                # Get standard
                all_yards = [s.get('avg_rushing_yards', 0) for s in splits.values() if 'avg_rushing_yards' in s]
                all_carries = [s.get('avg_carries', 0) for s in splits.values() if 'avg_carries' in s]
                standard_yards = np.mean(all_yards) if all_yards else contextual_yards
                standard_carries = np.mean(all_carries) if all_carries else contextual_carries
                
                projections.append(PropProjection(
                    player=player_name,
                    prop_type="Rushing Yards",
                    standard_projection=standard_yards,
                    contextual_projection=contextual_yards,
                    current_line=current_lines.get("rushing_yards"),
                    confidence=self._calculate_confidence(standard_yards, contextual_yards),
                    reasoning=f"Expected {expected_script} game → {contextual_yards:.0f} yds"
                ))
                
                projections.append(PropProjection(
                    player=player_name,
                    prop_type="Rushing Attempts",
                    standard_projection=standard_carries,
                    contextual_projection=contextual_carries,
                    current_line=current_lines.get("rushing_attempts"),
                    confidence=self._calculate_confidence(standard_carries, contextual_carries),
                    reasoning=f"Expected {expected_script} game → {contextual_carries:.0f} carries"
                ))
        
        return projections
    
    def full_matchup_analysis(
        self,
        player_name: str,
        position: str,
        opponent: str,
        current_lines: dict = None,
        game_weather: dict = None,
        expected_script: str = "close"
    ) -> MatchupAnalysis:
        """
        Run comprehensive matchup analysis combining all data sources.
        
        This is the main entry point for thorough research.
        """
        current_lines = current_lines or {}
        seasons = tuple(self.fetcher.years)
        
        self.console.print(Panel(
            f"[bold]Full Matchup Analysis[/bold]\n"
            f"Player: {player_name} ({position})\n"
            f"Opponent: {opponent}\n"
            f"Weather: {game_weather or 'Not specified'}\n"
            f"Expected Script: {expected_script}",
            title="🔬 Prop Alpha v2.0"
        ))
        
        # 1. Get opponent profile
        opponent_profile = self.fetcher.calculate_defense_profile(opponent, seasons)
        
        # 2. Find similar defenses
        similar_defenses = self.fetcher.find_similar_defenses(opponent, top_n=5, seasons=seasons)
        
        # 3. Get weather splits
        weather_splits = self.fetcher.get_player_weather_splits(player_name, position, seasons)
        
        # 4. Get game script splits
        game_script_splits = self.fetcher.get_player_game_script_splits(player_name, position, seasons)
        
        # 5. Run projections
        projections = []
        
        if position == "QB":
            qb_projections = self.analyze_qb_vs_defense_profile(
                player_name, opponent, current_lines, game_weather
            )
            projections.extend(qb_projections)
        
        # Add game script adjusted projections
        script_projections = self.analyze_with_game_script(
            player_name, position, expected_script, current_lines
        )
        projections.extend(script_projections)
        
        return MatchupAnalysis(
            player=player_name,
            opponent=opponent,
            opponent_profile=opponent_profile,
            similar_defenses=similar_defenses,
            weather_splits=weather_splits,
            game_script_splits=game_script_splits,
            projections=projections
        )
    
    def _calculate_confidence(self, standard: float, contextual: float) -> str:
        """Calculate confidence level based on deviation from standard."""
        if standard == 0:
            return "Low"
        
        deviation = abs(contextual - standard) / standard
        
        if deviation > 0.15:
            return "High"
        elif deviation > 0.08:
            return "Medium"
        else:
            return "Low"
    
    def print_projections(self, projections: list[PropProjection]):
        """Print projections in a nice table format."""
        table = Table(title="🎯 Prop Projections with Contextual Analysis (v2.0)")
        
        table.add_column("Player", style="cyan")
        table.add_column("Prop", style="magenta")
        table.add_column("Season Avg", justify="right")
        table.add_column("Contextual", justify="right", style="green")
        table.add_column("Current Line", justify="right")
        table.add_column("Edge", justify="right", style="bold")
        table.add_column("Conf.", justify="center")
        table.add_column("Action", style="yellow")
        
        for p in projections:
            edge_str = f"{p.edge:+.1f}" if p.edge else "N/A"
            line_str = f"{p.current_line:.1f}" if p.current_line else "N/A"
            
            # Determine action
            if p.edge and abs(p.edge) > 5:
                action = "OVER ✅" if p.edge > 0 else "UNDER ✅"
            else:
                action = "PASS"
            
            table.add_row(
                p.player,
                p.prop_type,
                f"{p.standard_projection:.1f}",
                f"{p.contextual_projection:.1f}",
                line_str,
                edge_str,
                p.confidence,
                action
            )
        
        self.console.print(table)
        
        # Print reasoning
        self.console.print("\n[bold]📝 Analysis Notes:[/bold]")
        for p in projections:
            self.console.print(f"  • {p.prop_type}: {p.reasoning}")
            if p.adjustments:
                self.console.print(f"    Adjustments: {', '.join(p.adjustments)}")


def run_matchup_analysis(
    qb: str,
    opponent: str,
    lines: dict = None,
    weather: dict = None,
    expected_script: str = "close"
) -> list[PropProjection]:
    """
    Convenience function to run a full matchup analysis.
    
    Args:
        qb: QB name
        opponent: Opponent team abbrev
        lines: Current prop lines
        weather: Game weather {"wind": mph, "temp": F}
        expected_script: Expected game flow
        
    Returns:
        List of projections
    """
    analyzer = ContextualPropsAnalyzer()
    projections = analyzer.analyze_qb_vs_defense_profile(qb, opponent, lines, weather)
    analyzer.print_projections(projections)
    return projections


if __name__ == "__main__":
    # Example: Bills vs Broncos analysis with weather
    run_matchup_analysis(
        qb="J.Allen",
        opponent="DEN",
        lines={"passing_yards": 265.5, "passing_tds": 1.5},
        weather={"wind": 10, "temp": 25}  # Cold January game in Denver
    )
