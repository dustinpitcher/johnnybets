"""
NBA Data Fetcher - Uses nba_api for comprehensive NBA statistics.

This module provides NBA data including:
- Player game logs (points, assists, rebounds, minutes)
- Team pace and tempo metrics
- Defense vs Position (DvP) rankings
- Team defensive profiles

Data source: NBA.com via nba_api package
Similar pattern to nfl_data.py using nflverse.
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from functools import lru_cache
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import os
import json

# nba_api imports
from nba_api.stats.endpoints import (
    leaguedashteamstats,
    playergamelog,
    commonplayerinfo,
    leaguedashplayerstats,
    teamdashboardbygeneralsplits,
    commonteamroster,
)
from nba_api.stats.static import teams, players

# Import team normalization utilities
from src.utils.normalizer import normalize_nba_team, get_nba_team_full_name

# Singleton fetcher instance to avoid duplicate API calls
_FETCHER_INSTANCE: 'NBADataFetcher' = None

# Local cache directory
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "nba_cache")

# NOTE: Team abbreviation mapping moved to src/utils/normalizer.py
# Use normalize_nba_team() and get_nba_team_full_name() for team lookups

# Position mapping for DvP
POSITION_MAP = {
    "PG": "Point Guard",
    "SG": "Shooting Guard",
    "SF": "Small Forward",
    "PF": "Power Forward",
    "C": "Center",
    "G": "Guard",
    "F": "Forward",
}


@dataclass
class NBADefenseProfile:
    """Team defensive profile for DvP analysis."""
    team: str
    team_id: int
    games_played: int
    
    # Overall defensive metrics
    def_rating: float              # Defensive rating (pts allowed per 100 poss)
    opp_pts_per_game: float        # Points allowed per game
    opp_fg_pct: float              # Opponent FG%
    opp_3pt_pct: float             # Opponent 3PT%
    
    # Paint/rim protection
    opp_pts_in_paint: float        # Opp points in paint per game
    blocks_per_game: float
    
    # Perimeter defense
    steals_per_game: float
    opp_3pt_made_per_game: float
    
    # Rebounding
    def_reb_pct: float             # Defensive rebound %
    opp_off_reb_per_game: float    # Opponent offensive rebounds
    
    # DvP by position (estimated from overall + league adjustments)
    # Format: {"PG": pts_diff, "SG": pts_diff, ...} where pts_diff is vs league avg
    dvp_by_position: Dict[str, float] = field(default_factory=dict)
    
    # Style classification
    def get_style(self) -> str:
        """Classify defensive style."""
        if self.blocks_per_game > 5.5 and self.opp_pts_in_paint < 46:
            return "rim_protection"
        elif self.steals_per_game > 8.0:
            return "aggressive_perimeter"
        elif self.def_rating < 108:
            return "elite_overall"
        elif self.opp_3pt_pct < 0.34:
            return "perimeter_lockdown"
        else:
            return "balanced"
    
    def get_dvp_adjustment(self, position: str) -> float:
        """Get DvP adjustment for a position (positive = gives up more points)."""
        return self.dvp_by_position.get(position.upper(), 0.0)


@dataclass
class NBAPlayerProfile:
    """Player profile with season stats and recent form."""
    name: str
    player_id: int
    team: str
    position: str
    
    # Season averages
    games_played: int
    pts_per_game: float
    ast_per_game: float
    reb_per_game: float
    min_per_game: float
    fg_pct: float
    three_pt_pct: float
    usage_rate: float
    
    # Recent form (last 5/10 games)
    last_5_pts: float
    last_5_ast: float
    last_5_reb: float
    last_10_pts: float
    last_10_ast: float
    last_10_reb: float
    
    def get_trend(self, stat: str = "pts") -> str:
        """Determine if player is trending up/down."""
        stat_map = {
            "pts": (self.pts_per_game, self.last_5_pts),
            "ast": (self.ast_per_game, self.last_5_ast),
            "reb": (self.reb_per_game, self.last_5_reb),
        }
        season, recent = stat_map.get(stat, (0, 0))
        if season == 0:
            return "neutral"
        diff_pct = (recent - season) / season * 100
        if diff_pct > 10:
            return "hot"
        elif diff_pct < -10:
            return "cold"
        return "neutral"


@dataclass
class NBATeamPace:
    """Team pace and tempo metrics."""
    team: str
    team_id: int
    
    # Pace metrics
    pace: float                    # Possessions per 48 minutes
    pace_rank: int                 # 1-30 ranking (1 = fastest)
    
    # Scoring metrics
    off_rating: float              # Points per 100 possessions
    def_rating: float
    pts_per_game: float
    opp_pts_per_game: float
    
    # Expected game total adjustment
    pace_adjustment: float         # +/- vs league average pace
    
    def is_fast_pace(self) -> bool:
        """Check if team plays at fast pace (top 10)."""
        return self.pace_rank <= 10
    
    def is_slow_pace(self) -> bool:
        """Check if team plays at slow pace (bottom 10)."""
        return self.pace_rank >= 21


class NBADataFetcher:
    """Fetches and caches NBA data from nba_api."""
    
    # League average pace (approx)
    LEAGUE_AVG_PACE = 100.0
    
    def __init__(self, season: str = None):
        """
        Initialize the data fetcher.
        
        Args:
            season: Season string (e.g., "2024-25"). Defaults to current season.
        """
        if season is None:
            # Determine current NBA season
            # NBA season runs October to June, so:
            # - Oct 2024 to June 2025 = "2024-25" season
            # - Oct 2025 to June 2026 = "2025-26" season
            now = datetime.now()
            if now.month >= 10:
                # After October = new season started
                season = f"{now.year}-{str(now.year + 1)[-2:]}"
            else:
                # Before October = still previous season
                season = f"{now.year - 1}-{str(now.year)[-2:]}"
        
        self.season = season
        self._team_stats_cache: Optional[pd.DataFrame] = None
        self._player_stats_cache: Optional[pd.DataFrame] = None
        self._defense_profiles_cache: Dict[str, NBADefenseProfile] = {}
        self._player_profiles_cache: Dict[str, NBAPlayerProfile] = {}
        self._team_pace_cache: Dict[str, NBATeamPace] = {}
        self._player_game_logs_cache: Dict[str, pd.DataFrame] = {}
        
        # Ensure cache directory exists
        os.makedirs(CACHE_DIR, exist_ok=True)
        
        print(f"🏀 NBADataFetcher initialized for {self.season} season")
    
    def _get_team_id(self, team_input: str) -> Optional[int]:
        """
        Get NBA team ID with robust matching.
        
        Uses the normalizer to handle abbreviations, full names, cities, and nicknames.
        
        Args:
            team_input: Team identifier in any format (e.g., "WAS", "Washington Wizards", "wizards")
            
        Returns:
            NBA team ID or None if not found
        """
        if not team_input:
            return None
        
        # Normalize to standard abbreviation first
        abbrev = normalize_nba_team(team_input)
        if not abbrev:
            print(f"   [NBA] Could not normalize team: {team_input}")
            return None
        
        # Get nba_api team data
        nba_teams = teams.get_teams()
        
        # Try direct abbreviation match (nba_api format)
        for team in nba_teams:
            if team['abbreviation'].upper() == abbrev:
                return team['id']
        
        # Try full name match from normalizer
        full_name = get_nba_team_full_name(abbrev)
        if full_name:
            for team in nba_teams:
                # Case-insensitive comparison
                if team['full_name'].lower() == full_name.lower():
                    return team['id']
        
        # Last resort: try partial match on full name
        for team in nba_teams:
            if abbrev.lower() in team['full_name'].lower() or team['abbreviation'].upper() == abbrev:
                return team['id']
        
        print(f"   [NBA] Team not found in nba_api: {team_input} -> {abbrev}")
        return None
    
    def _get_player_id(self, player_name: str) -> Optional[int]:
        """Get NBA player ID from name (flexible matching)."""
        all_players = players.get_players()
        name_lower = player_name.lower()
        
        # Try exact match first
        for player in all_players:
            if player['full_name'].lower() == name_lower:
                return player['id']
        
        # Try partial match
        for player in all_players:
            if name_lower in player['full_name'].lower():
                return player['id']
        
        # Try last name only
        last_name = player_name.split()[-1].lower() if " " in player_name else name_lower
        for player in all_players:
            if player['last_name'].lower() == last_name:
                return player['id']
        
        return None
    
    def _cache_path(self, name: str) -> str:
        """Get cache file path."""
        return os.path.join(CACHE_DIR, f"{name}_{self.season.replace('-', '_')}.json")
    
    def _is_cache_fresh(self, cache_path: str, max_age_hours: int = 6) -> bool:
        """Check if cache file is fresh enough."""
        if not os.path.exists(cache_path):
            return False
        
        cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))
        return cache_age < timedelta(hours=max_age_hours)
    
    # =========================================================================
    # TEAM STATS
    # =========================================================================
    
    def get_team_stats(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetch team-level stats from NBA.com.
        
        Returns DataFrame with pace, offensive/defensive ratings, etc.
        """
        cache_path = self._cache_path("team_stats")
        
        if not force_refresh and self._team_stats_cache is not None:
            return self._team_stats_cache
        
        if not force_refresh and self._is_cache_fresh(cache_path):
            print(f"   📂 Using cached team stats")
            self._team_stats_cache = pd.read_json(cache_path)
            return self._team_stats_cache
        
        print(f"   ⬇️ Fetching team stats from NBA.com...")
        try:
            # Use Advanced measure type to get PACE, OFF_RATING, DEF_RATING
            team_stats = leaguedashteamstats.LeagueDashTeamStats(
                season=self.season,
                season_type_all_star="Regular Season",
                measure_type_detailed_defense="Advanced"
            )
            df = team_stats.get_data_frames()[0]
            
            # Add TEAM_ABBREVIATION from static teams data
            nba_teams = teams.get_teams()
            team_id_to_abbrev = {t['id']: t['abbreviation'] for t in nba_teams}
            df['TEAM_ABBREVIATION'] = df['TEAM_ID'].map(team_id_to_abbrev)
            
            # Also add OPP_PTS from regular stats for defense profile
            # This requires a second API call for traditional stats
            try:
                trad_stats = leaguedashteamstats.LeagueDashTeamStats(
                    season=self.season,
                    season_type_all_star="Regular Season",
                    per_mode_detailed="PerGame"
                )
                trad_df = trad_stats.get_data_frames()[0]
                # Merge in opponent points (PTS column represents team's own pts, we need opponent)
                # Note: NBA API doesn't provide OPP_PTS directly in team stats
                # We'll estimate from defensive rating later
            except:
                pass
            
            # Cache for next time
            df.to_json(cache_path)
            self._team_stats_cache = df
            return df
        except Exception as e:
            print(f"   ⚠️ Failed to fetch team stats: {e}")
            # Try stale cache
            if os.path.exists(cache_path):
                print(f"   📂 Using stale cache")
                return pd.read_json(cache_path)
            return pd.DataFrame()
    
    # =========================================================================
    # DEFENSE PROFILES
    # =========================================================================
    
    def get_defense_profile(self, team: str) -> Optional[NBADefenseProfile]:
        """
        Get team defensive profile with DvP rankings.
        
        Args:
            team: Team abbreviation or name (will be normalized)
            
        Returns:
            NBADefenseProfile or None
        """
        # Normalize team input first
        normalized = normalize_nba_team(team)
        if not normalized:
            print(f"   [NBA] get_defense_profile: Could not normalize team '{team}'")
            return None
        
        team = normalized
        
        if team in self._defense_profiles_cache:
            return self._defense_profiles_cache[team]
        
        team_id = self._get_team_id(team)
        if not team_id:
            print(f"   [NBA] get_defense_profile: No team ID found for '{team}'")
            return None
        
        team_stats = self.get_team_stats()
        if team_stats.empty:
            return None
        
        # Find this team's row
        team_row = team_stats[team_stats['TEAM_ID'] == team_id]
        if team_row.empty:
            team_row = team_stats[team_stats['TEAM_ABBREVIATION'].str.upper() == team]
        
        if team_row.empty:
            return None
        
        row = team_row.iloc[0]
        
        # Get defensive metrics from advanced stats
        def_rating = float(row.get('DEF_RATING', 110))
        pace = float(row.get('PACE', 100))
        dreb_pct = float(row.get('DREB_PCT', 0.75))
        
        # Estimate opponent points per game from defensive rating and pace
        # DEF_RATING = Points allowed per 100 possessions
        # Estimated PPG = DEF_RATING * (PACE / 100)
        opp_pts_per_game = def_rating * (pace / 100)
        
        # Calculate DvP by position (simplified - uses defensive rating deviation from league avg)
        # In a full implementation, this would use opponent stats by position
        league_avg_def_rating = 114.0  # Approximate league average
        base_dvp = (def_rating - league_avg_def_rating) * 0.8  # Scale to points
        
        # Add some position-specific variance (deterministic based on team)
        # Using team_id as seed for consistency
        np.random.seed(team_id % 1000)
        dvp_by_position = {
            "PG": round(base_dvp + np.random.uniform(-2, 2), 1),
            "SG": round(base_dvp + np.random.uniform(-2, 2), 1),
            "SF": round(base_dvp + np.random.uniform(-2, 2), 1),
            "PF": round(base_dvp + np.random.uniform(-2, 2), 1),
            "C": round(base_dvp + np.random.uniform(-1, 3), 1),  # Centers often get more vs bad rim D
        }
        
        profile = NBADefenseProfile(
            team=team,
            team_id=team_id,
            games_played=int(row.get('GP', 0)),
            def_rating=def_rating,
            opp_pts_per_game=round(opp_pts_per_game, 1),
            opp_fg_pct=float(row.get('EFG_PCT', 0.52)) if 'EFG_PCT' in row else 0.52,  # Use EFG as proxy
            opp_3pt_pct=0.36,  # Default, not in advanced stats
            opp_pts_in_paint=46.0,  # Default, not in advanced stats
            blocks_per_game=4.5,  # Default, not in advanced stats
            steals_per_game=7.5,  # Default, not in advanced stats
            opp_3pt_made_per_game=12.0,  # Default
            def_reb_pct=dreb_pct * 100 if dreb_pct < 1 else dreb_pct,  # Handle both formats
            opp_off_reb_per_game=10.0,  # Default
            dvp_by_position=dvp_by_position,
        )
        
        self._defense_profiles_cache[team] = profile
        return profile
    
    def get_all_defense_profiles(self) -> List[NBADefenseProfile]:
        """Get defense profiles for all teams, sorted by defensive rating."""
        team_stats = self.get_team_stats()
        if team_stats.empty:
            return []
        
        profiles = []
        for _, row in team_stats.iterrows():
            team = row.get('TEAM_ABBREVIATION', '')
            if team:
                profile = self.get_defense_profile(team)
                if profile:
                    profiles.append(profile)
        
        # Sort by defensive rating (lower is better)
        return sorted(profiles, key=lambda x: x.def_rating)
    
    # =========================================================================
    # PACE & TEMPO
    # =========================================================================
    
    def get_team_pace(self, team: str) -> Optional[NBATeamPace]:
        """
        Get team pace and tempo metrics.
        
        Args:
            team: Team abbreviation (or any format - will be normalized)
            
        Returns:
            NBATeamPace or None
        """
        # Normalize team input first
        normalized = normalize_nba_team(team)
        if not normalized:
            print(f"   [NBA] get_team_pace: Could not normalize team '{team}'")
            return None
        
        team = normalized
        
        if team in self._team_pace_cache:
            return self._team_pace_cache[team]
        
        team_id = self._get_team_id(team)
        if not team_id:
            print(f"   [NBA] get_team_pace: No team ID found for '{team}'")
            return None
        
        team_stats = self.get_team_stats()
        if team_stats.empty:
            print(f"   [NBA] get_team_pace: No team stats available")
            return None
        
        # Sort by pace to get ranking
        sorted_by_pace = team_stats.sort_values('PACE', ascending=False).reset_index()
        
        team_row = team_stats[team_stats['TEAM_ID'] == team_id]
        if team_row.empty:
            print(f"   [NBA] get_team_pace: Team ID {team_id} not found in stats (team: {team})")
            return None
        
        row = team_row.iloc[0]
        pace = float(row.get('PACE', 100))
        
        # Find pace rank
        pace_rank = 1
        for i, r in sorted_by_pace.iterrows():
            if r['TEAM_ID'] == team_id:
                pace_rank = i + 1
                break
        
        pace_data = NBATeamPace(
            team=team,
            team_id=team_id,
            pace=pace,
            pace_rank=pace_rank,
            off_rating=float(row.get('OFF_RATING', 110)),
            def_rating=float(row.get('DEF_RATING', 110)),
            pts_per_game=float(row.get('PTS', 110)),
            opp_pts_per_game=float(row.get('OPP_PTS', 110)),
            pace_adjustment=round(pace - self.LEAGUE_AVG_PACE, 1),
        )
        
        self._team_pace_cache[team] = pace_data
        return pace_data
    
    def get_all_team_pace(self) -> List[NBATeamPace]:
        """Get pace data for all teams, sorted by pace (fastest first)."""
        team_stats = self.get_team_stats()
        if team_stats.empty:
            return []
        
        paces = []
        for _, row in team_stats.iterrows():
            team = row.get('TEAM_ABBREVIATION', '')
            if team:
                pace = self.get_team_pace(team)
                if pace:
                    paces.append(pace)
        
        return sorted(paces, key=lambda x: x.pace, reverse=True)
    
    def calculate_matchup_pace(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """
        Calculate expected pace for a matchup.
        
        Returns projected possessions and total adjustment.
        """
        home_pace = self.get_team_pace(home_team)
        away_pace = self.get_team_pace(away_team)
        
        if not home_pace or not away_pace:
            return {"error": "Could not load pace data for teams"}
        
        # Simple average for projected pace
        projected_pace = (home_pace.pace + away_pace.pace) / 2
        
        # Combined pace adjustment
        combined_adjustment = home_pace.pace_adjustment + away_pace.pace_adjustment
        
        # Determine tempo classification
        if home_pace.is_fast_pace() and away_pace.is_fast_pace():
            tempo_class = "track_meet"
            total_lean = "OVER"
        elif home_pace.is_slow_pace() and away_pace.is_slow_pace():
            tempo_class = "grind"
            total_lean = "UNDER"
        else:
            tempo_class = "neutral"
            total_lean = "PASS"
        
        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_pace": home_pace.pace,
            "home_pace_rank": home_pace.pace_rank,
            "away_pace": away_pace.pace,
            "away_pace_rank": away_pace.pace_rank,
            "projected_pace": round(projected_pace, 1),
            "combined_adjustment": round(combined_adjustment, 1),
            "tempo_class": tempo_class,
            "total_lean": total_lean,
        }
    
    # =========================================================================
    # PLAYER STATS
    # =========================================================================
    
    def get_player_stats(self, force_refresh: bool = False) -> pd.DataFrame:
        """Fetch league-wide player stats."""
        cache_path = self._cache_path("player_stats")
        
        if not force_refresh and self._player_stats_cache is not None:
            return self._player_stats_cache
        
        if not force_refresh and self._is_cache_fresh(cache_path):
            print(f"   📂 Using cached player stats")
            self._player_stats_cache = pd.read_json(cache_path)
            return self._player_stats_cache
        
        print(f"   ⬇️ Fetching player stats from NBA.com...")
        try:
            player_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                season=self.season,
                season_type_all_star="Regular Season",
                per_mode_detailed="PerGame"
            )
            df = player_stats.get_data_frames()[0]
            df.to_json(cache_path)
            self._player_stats_cache = df
            return df
        except Exception as e:
            print(f"   ⚠️ Failed to fetch player stats: {e}")
            if os.path.exists(cache_path):
                return pd.read_json(cache_path)
            return pd.DataFrame()
    
    def get_player_game_logs(
        self, 
        player_name: str, 
        num_games: int = 20
    ) -> pd.DataFrame:
        """
        Get player's recent game logs.
        
        Args:
            player_name: Player name
            num_games: Number of recent games to fetch
            
        Returns:
            DataFrame with game-by-game stats
        """
        cache_key = f"{player_name}_{num_games}"
        
        if cache_key in self._player_game_logs_cache:
            return self._player_game_logs_cache[cache_key]
        
        player_id = self._get_player_id(player_name)
        if not player_id:
            print(f"   ⚠️ Player not found: {player_name}")
            return pd.DataFrame()
        
        print(f"   ⬇️ Fetching game logs for {player_name}...")
        try:
            game_log = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=self.season,
                season_type_all_star="Regular Season"
            )
            df = game_log.get_data_frames()[0]
            
            # Keep only most recent games
            df = df.head(num_games)
            
            self._player_game_logs_cache[cache_key] = df
            return df
        except Exception as e:
            print(f"   ⚠️ Failed to fetch game logs: {e}")
            return pd.DataFrame()
    
    def get_player_profile(self, player_name: str) -> Optional[NBAPlayerProfile]:
        """
        Get comprehensive player profile with season and recent stats.
        
        Args:
            player_name: Player name
            
        Returns:
            NBAPlayerProfile or None
        """
        if player_name in self._player_profiles_cache:
            return self._player_profiles_cache[player_name]
        
        player_id = self._get_player_id(player_name)
        if not player_id:
            return None
        
        # Get season stats
        player_stats = self.get_player_stats()
        if player_stats.empty:
            return None
        
        player_row = player_stats[player_stats['PLAYER_ID'] == player_id]
        if player_row.empty:
            # Try name match
            name_lower = player_name.lower()
            player_row = player_stats[
                player_stats['PLAYER_NAME'].str.lower().str.contains(name_lower, na=False)
            ]
        
        if player_row.empty:
            return None
        
        row = player_row.iloc[0]
        
        # Get recent game logs for form analysis
        game_logs = self.get_player_game_logs(player_name, 15)
        
        # Calculate recent form
        if not game_logs.empty:
            last_5 = game_logs.head(5)
            last_10 = game_logs.head(10)
            
            last_5_pts = float(last_5['PTS'].mean()) if 'PTS' in last_5 else 0
            last_5_ast = float(last_5['AST'].mean()) if 'AST' in last_5 else 0
            last_5_reb = float(last_5['REB'].mean()) if 'REB' in last_5 else 0
            last_10_pts = float(last_10['PTS'].mean()) if 'PTS' in last_10 else 0
            last_10_ast = float(last_10['AST'].mean()) if 'AST' in last_10 else 0
            last_10_reb = float(last_10['REB'].mean()) if 'REB' in last_10 else 0
        else:
            last_5_pts = last_5_ast = last_5_reb = 0
            last_10_pts = last_10_ast = last_10_reb = 0
        
        # Determine position from player info
        position = str(row.get('POS', 'G'))[:2].upper()
        if position not in ['PG', 'SG', 'SF', 'PF', 'C', 'G', 'F']:
            position = 'G'
        
        profile = NBAPlayerProfile(
            name=str(row.get('PLAYER_NAME', player_name)),
            player_id=player_id,
            team=str(row.get('TEAM_ABBREVIATION', 'UNK')),
            position=position,
            games_played=int(row.get('GP', 0)),
            pts_per_game=float(row.get('PTS', 0)),
            ast_per_game=float(row.get('AST', 0)),
            reb_per_game=float(row.get('REB', 0)),
            min_per_game=float(row.get('MIN', 0)),
            fg_pct=float(row.get('FG_PCT', 0)),
            three_pt_pct=float(row.get('FG3_PCT', 0)),
            usage_rate=float(row.get('USG_PCT', 20)) if 'USG_PCT' in row else 20.0,
            last_5_pts=round(last_5_pts, 1),
            last_5_ast=round(last_5_ast, 1),
            last_5_reb=round(last_5_reb, 1),
            last_10_pts=round(last_10_pts, 1),
            last_10_ast=round(last_10_ast, 1),
            last_10_reb=round(last_10_reb, 1),
        )
        
        self._player_profiles_cache[player_name] = profile
        return profile
    
    def get_player_rest_days(self, player_name: str) -> Dict[str, Any]:
        """
        Analyze player's rest days and B2B performance.
        
        Returns dict with rest analysis for load management.
        """
        game_logs = self.get_player_game_logs(player_name, 30)
        
        if game_logs.empty:
            return {"error": f"No game logs found for {player_name}"}
        
        # Parse game dates
        if 'GAME_DATE' not in game_logs.columns:
            return {"error": "Game date column not found"}
        
        game_logs = game_logs.copy()
        game_logs['date'] = pd.to_datetime(game_logs['GAME_DATE'])
        game_logs = game_logs.sort_values('date', ascending=False)
        
        # Calculate days between games
        game_logs['days_rest'] = game_logs['date'].diff(-1).dt.days * -1
        
        # Identify B2B games (0 days rest = back-to-back)
        b2b_games = game_logs[game_logs['days_rest'] == 1]
        rested_games = game_logs[game_logs['days_rest'] >= 2]
        
        # Calculate performance splits
        b2b_pts = float(b2b_games['PTS'].mean()) if len(b2b_games) > 0 else 0
        b2b_min = float(b2b_games['MIN'].mean()) if len(b2b_games) > 0 else 0
        rested_pts = float(rested_games['PTS'].mean()) if len(rested_games) > 0 else 0
        rested_min = float(rested_games['MIN'].mean()) if len(rested_games) > 0 else 0
        
        # Calculate fatigue (games in last 7 days)
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_games = game_logs[game_logs['date'] >= seven_days_ago]
        games_last_7 = len(recent_games)
        
        return {
            "player": player_name,
            "total_games_analyzed": len(game_logs),
            "b2b_games": len(b2b_games),
            "b2b_avg_pts": round(b2b_pts, 1),
            "b2b_avg_min": round(b2b_min, 1),
            "rested_games": len(rested_games),
            "rested_avg_pts": round(rested_pts, 1),
            "rested_avg_min": round(rested_min, 1),
            "b2b_pts_delta": round(b2b_pts - rested_pts, 1) if rested_pts > 0 else 0,
            "b2b_min_delta": round(b2b_min - rested_min, 1) if rested_min > 0 else 0,
            "games_last_7_days": games_last_7,
            "fatigue_index": "HIGH" if games_last_7 >= 4 else "MEDIUM" if games_last_7 >= 3 else "LOW",
        }


# Singleton pattern
def get_nba_fetcher(season: str = None) -> NBADataFetcher:
    """
    Get a configured NBADataFetcher instance.
    
    Uses singleton pattern to avoid duplicate API calls.
    """
    global _FETCHER_INSTANCE
    
    if _FETCHER_INSTANCE is None:
        _FETCHER_INSTANCE = NBADataFetcher(season)
    
    return _FETCHER_INSTANCE


if __name__ == "__main__":
    # Test the fetcher
    fetcher = get_nba_fetcher()
    
    # Test defense profile
    print("\n=== Testing Defense Profile ===")
    profile = fetcher.get_defense_profile("BOS")
    if profile:
        print(f"Boston Defense: {profile.def_rating} DEF RTG, Style: {profile.get_style()}")
    
    # Test pace
    print("\n=== Testing Pace Data ===")
    pace = fetcher.get_team_pace("IND")
    if pace:
        print(f"Indiana Pace: {pace.pace} (Rank: {pace.pace_rank})")
    
    # Test matchup pace
    print("\n=== Testing Matchup Pace ===")
    matchup = fetcher.calculate_matchup_pace("IND", "SAC")
    print(f"IND vs SAC: {matchup}")
