"""
NFL Data Fetcher - Uses nflverse parquet data directly for play-by-play and roster data.

This module provides granular NFL data including:
- Play-by-play data (down, distance, formation, pass location, YAC, etc.)
- Roster and injury information
- Team schedules and game results
- Dynamic defense profiling
- Weather-adjusted queries

Data source: https://github.com/nflverse/nflverse-data/releases
"""

import pandas as pd
import numpy as np
from typing import Optional
from functools import lru_cache
from dataclasses import dataclass
import os

# nflverse parquet URLs
NFLVERSE_BASE_URL = "https://github.com/nflverse/nflverse-data/releases/download"
PBP_URL = f"{NFLVERSE_BASE_URL}/pbp/play_by_play_{{year}}.parquet"
PLAYER_STATS_URL = f"{NFLVERSE_BASE_URL}/player_stats/player_stats_{{year}}.parquet"
ROSTER_URL = f"{NFLVERSE_BASE_URL}/rosters/roster_{{year}}.parquet"

# Local cache directory
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "nfl_cache")

# Team name to abbreviation mapping
TEAM_ABBR = {
    # Full names
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
    # City only
    "Arizona": "ARI", "Atlanta": "ATL", "Baltimore": "BAL", "Buffalo": "BUF",
    "Carolina": "CAR", "Chicago": "CHI", "Cincinnati": "CIN", "Cleveland": "CLE",
    "Dallas": "DAL", "Denver": "DEN", "Detroit": "DET", "Green Bay": "GB",
    "Houston": "HOU", "Indianapolis": "IND", "Jacksonville": "JAX", "Kansas City": "KC",
    "Las Vegas": "LV", "Los Angeles Chargers": "LAC", "Los Angeles Rams": "LA",
    "Miami": "MIA", "Minnesota": "MIN", "New England": "NE", "New Orleans": "NO",
    "New York Giants": "NYG", "New York Jets": "NYJ", "Philadelphia": "PHI",
    "Pittsburgh": "PIT", "San Francisco": "SF", "Seattle": "SEA", "Tampa Bay": "TB",
    "Tennessee": "TEN", "Washington": "WAS",
    # Nicknames only
    "Cardinals": "ARI", "Falcons": "ATL", "Ravens": "BAL", "Bills": "BUF",
    "Panthers": "CAR", "Bears": "CHI", "Bengals": "CIN", "Browns": "CLE",
    "Cowboys": "DAL", "Broncos": "DEN", "Lions": "DET", "Packers": "GB",
    "Texans": "HOU", "Colts": "IND", "Jaguars": "JAX", "Chiefs": "KC",
    "Raiders": "LV", "Chargers": "LAC", "Rams": "LA", "Dolphins": "MIA",
    "Vikings": "MIN", "Patriots": "NE", "Saints": "NO", "Giants": "NYG",
    "Jets": "NYJ", "Eagles": "PHI", "Steelers": "PIT", "49ers": "SF",
    "Seahawks": "SEA", "Buccaneers": "TB", "Titans": "TEN", "Commanders": "WAS",
}

def normalize_team(team: str) -> str:
    """Convert team name to standard abbreviation."""
    if not team:
        return team
    # Already an abbreviation
    if team.upper() in ["ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", 
                        "DAL", "DEN", "DET", "GB", "HOU", "IND", "JAX", "KC",
                        "LA", "LAC", "LV", "MIA", "MIN", "NE", "NO", "NYG", 
                        "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"]:
        return team.upper()
    # Look up in mapping
    return TEAM_ABBR.get(team, team)


@dataclass
class DefenseProfile:
    """Data-driven defensive profile for a team."""
    team: str
    total_plays: int
    # Pressure metrics
    sack_rate: float  # % of dropbacks resulting in sack
    pressure_proxy: float  # Incomplete + sack + int rate
    # Coverage metrics  
    avg_air_yards_allowed: float  # Average depth of target allowed
    completion_pct_allowed: float
    yards_per_attempt_allowed: float
    # Style classification (calculated)
    is_aggressive: bool  # High pressure, low air yards = aggressive man
    is_zone_heavy: bool  # Low pressure, high air yards = zone
    is_blitz_heavy: bool  # High sack rate
    
    def similarity_score(self, other: 'DefenseProfile') -> float:
        """Calculate similarity to another defense profile (0-1, higher = more similar)."""
        # Normalize and compare key metrics
        metrics = [
            ('sack_rate', 0.05),  # typical range ~3-8%
            ('avg_air_yards_allowed', 3.0),  # typical range ~6-10
            ('completion_pct_allowed', 10.0),  # typical range ~55-70%
            ('yards_per_attempt_allowed', 2.0),  # typical range ~5-9
        ]
        
        total_diff = 0
        for attr, scale in metrics:
            diff = abs(getattr(self, attr) - getattr(other, attr)) / scale
            total_diff += min(diff, 1.0)  # Cap at 1.0 per metric
        
        # Convert to similarity (0-1)
        return max(0, 1 - (total_diff / len(metrics)))


class NFLDataFetcher:
    """Fetches and caches NFL data from nflverse parquet files."""
    
    def __init__(self, years: list[int] = None):
        """
        Initialize the data fetcher.
        
        Args:
            years: List of seasons to load. Defaults to last 3 years.
        """
        self.years = years or [2023, 2024, 2025]
        self._pbp_cache: dict[int, pd.DataFrame] = {}
        self._pbp_combined_cache: dict[tuple, pd.DataFrame] = {}  # Cache combined PBP
        self._roster_cache: dict[int, pd.DataFrame] = {}
        self._defense_profiles_cache: dict[str, DefenseProfile] = {}
        self._verbose = True  # Control logging
        
        # Ensure cache directory exists
        os.makedirs(CACHE_DIR, exist_ok=True)
    
    def _get_cached_or_download(self, url: str, cache_name: str) -> pd.DataFrame:
        """Download data or use cached version."""
        cache_path = os.path.join(CACHE_DIR, f"{cache_name}.parquet")
        
        if os.path.exists(cache_path):
            print(f"   📂 Using cached: {cache_name}")
            return pd.read_parquet(cache_path)
        
        print(f"   ⬇️ Downloading: {url}")
        try:
            df = pd.read_parquet(url)
            # Cache for next time
            df.to_parquet(cache_path)
            return df
        except Exception as e:
            print(f"   ⚠️ Failed to download {url}: {e}")
            return pd.DataFrame()
    
    def get_play_by_play(self, seasons: tuple[int] = None) -> pd.DataFrame:
        """
        Fetch play-by-play data for specified seasons.
        
        Args:
            seasons: Tuple of years. Defaults to self.years.
            
        Returns:
            DataFrame with granular play-by-play data.
        """
        years = tuple(seasons) if seasons else tuple(self.years)
        
        # Check combined cache first
        if years in self._pbp_combined_cache:
            return self._pbp_combined_cache[years]
        
        if self._verbose:
            print(f"📊 Loading play-by-play data for {list(years)}...")
        
        dfs = []
        for year in years:
            if year not in self._pbp_cache:
                url = PBP_URL.format(year=year)
                self._pbp_cache[year] = self._get_cached_or_download(url, f"pbp_{year}")
            dfs.append(self._pbp_cache[year])
        
        if not dfs or all(df.empty for df in dfs):
            if self._verbose:
                print("   ⚠️ No play-by-play data available")
            return pd.DataFrame()
        
        pbp = pd.concat([df for df in dfs if not df.empty], ignore_index=True)
        
        # Cache the combined result
        self._pbp_combined_cache[years] = pbp
        
        if self._verbose:
            print(f"   ✓ Loaded {len(pbp):,} plays")
            self._verbose = False  # Only log first time
        
        return pbp
    
    def get_roster(self, year: int) -> pd.DataFrame:
        """Fetch roster data for a specific year."""
        if year not in self._roster_cache:
            print(f"📋 Loading roster data for {year}...")
            url = ROSTER_URL.format(year=year)
            self._roster_cache[year] = self._get_cached_or_download(url, f"roster_{year}")
        return self._roster_cache[year]
    
    def get_player_stats(self, years: list[int] = None) -> pd.DataFrame:
        """Fetch weekly player stats."""
        years = years or self.years
        print(f"📈 Loading player stats for {years}...")
        
        dfs = []
        for year in years:
            url = PLAYER_STATS_URL.format(year=year)
            df = self._get_cached_or_download(url, f"player_stats_{year}")
            dfs.append(df)
        
        if not dfs or all(df.empty for df in dfs):
            return pd.DataFrame()
        
        return pd.concat([df for df in dfs if not df.empty], ignore_index=True)
    
    # =========================================================================
    # DYNAMIC DEFENSE PROFILING
    # =========================================================================
    
    def calculate_defense_profile(self, team: str, seasons: tuple[int] = None) -> DefenseProfile:
        """
        Calculate a data-driven defensive profile for a team.
        
        This replaces hardcoded defense classifications with actual metrics.
        """
        # Normalize team name to abbreviation
        team_abbr = normalize_team(team)
        
        cache_key = f"{team_abbr}_{seasons or tuple(self.years)}"
        if cache_key in self._defense_profiles_cache:
            return self._defense_profiles_cache[cache_key]
        
        pbp = self.get_play_by_play(seasons)
        if pbp.empty:
            return DefenseProfile(
                team=team_abbr, total_plays=0, sack_rate=0, pressure_proxy=0,
                avg_air_yards_allowed=0, completion_pct_allowed=0,
                yards_per_attempt_allowed=0, is_aggressive=False,
                is_zone_heavy=False, is_blitz_heavy=False
            )
        
        # Get plays where this team was on defense (using abbreviation)
        defense_plays = pbp[pbp['defteam'] == team_abbr]
        pass_plays = defense_plays[defense_plays['play_type'] == 'pass']
        
        if len(pass_plays) == 0:
            return DefenseProfile(
                team=team_abbr, total_plays=0, sack_rate=0, pressure_proxy=0,
                avg_air_yards_allowed=0, completion_pct_allowed=0,
                yards_per_attempt_allowed=0, is_aggressive=False,
                is_zone_heavy=False, is_blitz_heavy=False
            )
        
        # Calculate metrics
        sack_rate = pass_plays['sack'].mean() * 100 if 'sack' in pass_plays.columns else 0
        
        completion_pct = (
            pass_plays['complete_pass'].sum() / len(pass_plays) * 100
            if 'complete_pass' in pass_plays.columns else 0
        )
        
        avg_air_yards = (
            pass_plays['air_yards'].mean()
            if 'air_yards' in pass_plays.columns else 0
        )
        
        yards_per_attempt = (
            pass_plays['passing_yards'].mean()
            if 'passing_yards' in pass_plays.columns else 0
        )
        
        # Pressure proxy: sacks + interceptions + incompletions
        int_rate = pass_plays['interception'].mean() * 100 if 'interception' in pass_plays.columns else 0
        incomplete_rate = 100 - completion_pct
        pressure_proxy = sack_rate + int_rate + (incomplete_rate * 0.5)
        
        # Classify style based on metrics
        # Aggressive/man coverage: High pressure, lower air yards (tight coverage)
        is_aggressive = pressure_proxy > 25 and avg_air_yards < 8.0
        # Zone heavy: Lower pressure, higher air yards allowed (soft coverage)
        is_zone_heavy = pressure_proxy < 20 and avg_air_yards > 8.5
        # Blitz heavy: High sack rate
        is_blitz_heavy = sack_rate > 5.0
        
        profile = DefenseProfile(
            team=team_abbr,
            total_plays=len(pass_plays),
            sack_rate=round(sack_rate, 2),
            pressure_proxy=round(pressure_proxy, 2),
            avg_air_yards_allowed=round(avg_air_yards, 2),
            completion_pct_allowed=round(completion_pct, 2),
            yards_per_attempt_allowed=round(yards_per_attempt, 2),
            is_aggressive=is_aggressive,
            is_zone_heavy=is_zone_heavy,
            is_blitz_heavy=is_blitz_heavy
        )
        
        self._defense_profiles_cache[cache_key] = profile
        return profile
    
    def find_similar_defenses(
        self, 
        team: str, 
        top_n: int = 5,
        seasons: tuple[int] = None
    ) -> list[tuple[str, float, DefenseProfile]]:
        """
        Find teams with similar defensive profiles using actual data.
        
        Returns list of (team, similarity_score, profile) tuples.
        """
        target_profile = self.calculate_defense_profile(team, seasons)
        
        # Get all teams
        pbp = self.get_play_by_play(seasons)
        if pbp.empty:
            return [(team, 1.0, target_profile)]
        
        all_teams = pbp['defteam'].dropna().unique()
        
        similarities = []
        for other_team in all_teams:
            if pd.isna(other_team) or other_team == '':
                continue
            other_profile = self.calculate_defense_profile(other_team, seasons)
            if other_profile.total_plays < 100:  # Skip teams with insufficient data
                continue
            score = target_profile.similarity_score(other_profile)
            similarities.append((other_team, score, other_profile))
        
        # Sort by similarity (descending) and return top N
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]
    
    # =========================================================================
    # WEATHER-ADJUSTED QUERIES
    # =========================================================================
    
    def get_player_plays_with_conditions(
        self,
        player_name: str,
        position: str = "QB",
        seasons: tuple[int] = None,
        min_wind: float = None,
        max_wind: float = None,
        min_temp: float = None,
        max_temp: float = None,
        dome_only: bool = False,
        outdoor_only: bool = False
    ) -> pd.DataFrame:
        """
        Get player plays filtered by weather conditions.
        
        Args:
            player_name: Player name
            position: Position (QB, RB, WR, TE)
            seasons: Years to search
            min_wind: Minimum wind speed (mph)
            max_wind: Maximum wind speed (mph)
            min_temp: Minimum temperature (F)
            max_temp: Maximum temperature (F)
            dome_only: Only indoor games
            outdoor_only: Only outdoor games
        """
        # Get base player plays
        player_plays = self.get_player_plays(player_name, position, seasons)
        
        if player_plays.empty:
            return player_plays
        
        # Apply weather filters
        if min_wind is not None and 'wind' in player_plays.columns:
            player_plays = player_plays[player_plays['wind'] >= min_wind]
        
        if max_wind is not None and 'wind' in player_plays.columns:
            player_plays = player_plays[player_plays['wind'] <= max_wind]
        
        if min_temp is not None and 'temp' in player_plays.columns:
            player_plays = player_plays[player_plays['temp'] >= min_temp]
        
        if max_temp is not None and 'temp' in player_plays.columns:
            player_plays = player_plays[player_plays['temp'] <= max_temp]
        
        if dome_only and 'roof' in player_plays.columns:
            player_plays = player_plays[player_plays['roof'].isin(['dome', 'closed'])]
        
        if outdoor_only and 'roof' in player_plays.columns:
            player_plays = player_plays[~player_plays['roof'].isin(['dome', 'closed'])]
        
        return player_plays
    
    def get_player_weather_splits(
        self,
        player_name: str,
        position: str = "QB",
        seasons: tuple[int] = None
    ) -> dict:
        """
        Calculate player performance splits by weather conditions.
        
        Returns dict with stats in different weather scenarios.
        """
        all_plays = self.get_player_plays(player_name, position, seasons)
        
        if all_plays.empty:
            return {"error": f"No plays found for {player_name}"}
        
        # Ensure we have weather data
        if 'wind' not in all_plays.columns:
            return {"error": "Weather data not available"}
        
        # Calculate splits
        splits = {}
        
        # High wind (15+ mph)
        high_wind = all_plays[all_plays['wind'] >= 15]
        if len(high_wind) > 0:
            high_wind_games = high_wind.groupby('game_id').agg({
                'passing_yards': 'sum',
                'air_yards': 'mean',
                'complete_pass': 'sum',
            }).reset_index()
            splits['high_wind_15mph+'] = {
                'games': len(high_wind_games),
                'avg_passing_yards': round(high_wind_games['passing_yards'].mean(), 1),
                'avg_depth_of_target': round(high_wind_games['air_yards'].mean(), 1),
            }
        
        # Low/no wind (< 10 mph)
        low_wind = all_plays[all_plays['wind'] < 10]
        if len(low_wind) > 0:
            low_wind_games = low_wind.groupby('game_id').agg({
                'passing_yards': 'sum',
                'air_yards': 'mean',
            }).reset_index()
            splits['low_wind_<10mph'] = {
                'games': len(low_wind_games),
                'avg_passing_yards': round(low_wind_games['passing_yards'].mean(), 1),
                'avg_depth_of_target': round(low_wind_games['air_yards'].mean(), 1),
            }
        
        # Cold weather (< 40 F)
        if 'temp' in all_plays.columns:
            cold = all_plays[all_plays['temp'] < 40]
            if len(cold) > 0:
                cold_games = cold.groupby('game_id').agg({
                    'passing_yards': 'sum',
                }).reset_index()
                splits['cold_<40F'] = {
                    'games': len(cold_games),
                    'avg_passing_yards': round(cold_games['passing_yards'].mean(), 1),
                }
        
        return splits
    
    # =========================================================================
    # GAME SCRIPT ANALYSIS
    # =========================================================================
    
    def get_player_game_script_splits(
        self,
        player_name: str,
        position: str = "QB",
        seasons: tuple[int] = None
    ) -> dict:
        """
        Calculate player performance by game script (leading, trailing, close).
        
        Key insight: RBs get more carries when winning, QBs throw more when trailing.
        """
        all_plays = self.get_player_plays(player_name, position, seasons)
        
        if all_plays.empty:
            return {"error": f"No plays found for {player_name}"}
        
        if 'score_differential' not in all_plays.columns:
            return {"error": "Score differential not available"}
        
        splits = {}
        
        # When team is winning by 7+
        winning = all_plays[all_plays['score_differential'] > 7]
        if len(winning) > 0:
            winning_games = winning.groupby('game_id')
            if position == "QB":
                stats = winning.groupby('game_id').agg({
                    'passing_yards': 'sum',
                    'pass_attempt': 'sum',
                }).reset_index()
                splits['winning_7+'] = {
                    'games': len(stats),
                    'avg_passing_yards': round(stats['passing_yards'].mean(), 1),
                    'avg_attempts': round(stats['pass_attempt'].mean(), 1),
                }
            elif position == "RB":
                stats = winning.groupby('game_id').agg({
                    'rushing_yards': 'sum',
                    'rush_attempt': 'sum',
                }).reset_index()
                splits['winning_7+'] = {
                    'games': len(stats),
                    'avg_rushing_yards': round(stats['rushing_yards'].mean(), 1),
                    'avg_carries': round(stats['rush_attempt'].mean(), 1),
                }
        
        # When team is losing by 7+
        losing = all_plays[all_plays['score_differential'] < -7]
        if len(losing) > 0:
            if position == "QB":
                stats = losing.groupby('game_id').agg({
                    'passing_yards': 'sum',
                    'pass_attempt': 'sum',
                }).reset_index()
                splits['losing_7+'] = {
                    'games': len(stats),
                    'avg_passing_yards': round(stats['passing_yards'].mean(), 1),
                    'avg_attempts': round(stats['pass_attempt'].mean(), 1),
                }
            elif position == "RB":
                stats = losing.groupby('game_id').agg({
                    'rushing_yards': 'sum',
                    'rush_attempt': 'sum',
                }).reset_index()
                splits['losing_7+'] = {
                    'games': len(stats),
                    'avg_rushing_yards': round(stats['rushing_yards'].mean(), 1),
                    'avg_carries': round(stats['rush_attempt'].mean(), 1),
                }
        
        # Close game (-7 to +7)
        close = all_plays[
            (all_plays['score_differential'] >= -7) & 
            (all_plays['score_differential'] <= 7)
        ]
        if len(close) > 0:
            if position == "QB":
                stats = close.groupby('game_id').agg({
                    'passing_yards': 'sum',
                    'pass_attempt': 'sum',
                }).reset_index()
                splits['close_game'] = {
                    'games': len(stats),
                    'avg_passing_yards': round(stats['passing_yards'].mean(), 1),
                    'avg_attempts': round(stats['pass_attempt'].mean(), 1),
                }
            elif position == "RB":
                stats = close.groupby('game_id').agg({
                    'rushing_yards': 'sum',
                    'rush_attempt': 'sum',
                }).reset_index()
                splits['close_game'] = {
                    'games': len(stats),
                    'avg_rushing_yards': round(stats['rushing_yards'].mean(), 1),
                    'avg_carries': round(stats['rush_attempt'].mean(), 1),
                }
        
        return splits
    
    # =========================================================================
    # ORIGINAL METHODS
    # =========================================================================
    
    def get_player_plays(
        self, 
        player_name: str, 
        position: str = "QB",
        seasons: tuple[int] = None
    ) -> pd.DataFrame:
        """
        Get all plays involving a specific player.
        
        Args:
            player_name: Player's name (e.g., "J.Allen", "Josh Allen", "C.J. Stroud")
            position: Position filter (QB, RB, WR, TE)
            seasons: Years to search
            
        Returns:
            Filtered DataFrame of plays
        """
        pbp = self.get_play_by_play(seasons)
        
        if pbp.empty:
            return pbp
        
        # Handle common name formats
        # nflverse format is "FirstInitial.LastName" (e.g., "C.Stroud", "J.Allen", "J.Mixon")
        name_variants = [player_name]
        
        # Extract last name for flexible matching
        last_name = player_name.split()[-1] if " " in player_name else None
        if last_name and "." not in last_name:
            name_variants.append(last_name)
        
        # Handle "Joe Mixon" -> "J.Mixon" (full first name to initial)
        if " " in player_name and "." not in player_name:
            parts = player_name.split()
            if len(parts) >= 2:
                first_initial = parts[0][0] if parts[0] else ""
                last = parts[-1]
                simplified = f"{first_initial}.{last}"
                name_variants.append(simplified)
        
        # Handle "C.J. Stroud" -> "C.Stroud" (drop middle initial)
        if ". " in player_name:
            # "C.J. Stroud" -> try "C.Stroud"
            parts = player_name.split()
            if len(parts) >= 2:
                first_initial = parts[0][0] if parts[0] else ""
                last = parts[-1]
                simplified = f"{first_initial}.{last}"
                name_variants.append(simplified)
        
        # Handle "J.Allen" format
        if "." in player_name and " " not in player_name:
            parts = player_name.split(".")
            if len(parts) == 2:
                name_variants.append(parts[1].strip())  # Just last name
        
        # Remove duplicates while preserving order
        name_variants = list(dict.fromkeys(name_variants))
        
        def name_match(col):
            """Check if any name variant matches."""
            if col not in pbp.columns:
                return pd.Series([False] * len(pbp))
            matches = pd.Series([False] * len(pbp))
            for name in name_variants:
                matches |= pbp[col].str.contains(name, case=False, na=False)
            return matches
        
        if position == "QB":
            # For QBs, look at passer fields
            passer_cols = ['passer', 'passer_player_name', 'passer_player_id']
            mask = pd.Series([False] * len(pbp))
            for col in passer_cols:
                mask |= name_match(col)
            player_plays = pbp[mask]
        elif position == "RB":
            # For RBs, look at rusher fields
            rusher_cols = ['rusher', 'rusher_player_name', 'rusher_player_id']
            mask = pd.Series([False] * len(pbp))
            for col in rusher_cols:
                mask |= name_match(col)
            player_plays = pbp[mask]
        elif position in ("WR", "TE"):
            # For receivers, look at receiver fields
            receiver_cols = ['receiver', 'receiver_player_name', 'receiver_player_id']
            mask = pd.Series([False] * len(pbp))
            for col in receiver_cols:
                mask |= name_match(col)
            player_plays = pbp[mask]
        else:
            # Search all player columns
            mask = (
                name_match('passer') | name_match('passer_player_name') |
                name_match('rusher') | name_match('rusher_player_name') |
                name_match('receiver') | name_match('receiver_player_name')
            )
            player_plays = pbp[mask]
        
        print(f"   Found {len(player_plays):,} plays for {player_name} ({position})")
        return player_plays
    
    def get_defense_stats(self, team: str, seasons: tuple[int] = None) -> dict:
        """
        Calculate defensive stats for a team.
        
        Returns dict with defensive metrics.
        """
        profile = self.calculate_defense_profile(team, seasons)
        
        return {
            'team': profile.team,
            'total_plays_faced': profile.total_plays,
            'sack_rate': profile.sack_rate,
            'pressure_proxy': profile.pressure_proxy,
            'avg_air_yards_allowed': profile.avg_air_yards_allowed,
            'completion_pct_allowed': profile.completion_pct_allowed,
            'yards_per_attempt_allowed': profile.yards_per_attempt_allowed,
            'style': {
                'is_aggressive': profile.is_aggressive,
                'is_zone_heavy': profile.is_zone_heavy,
                'is_blitz_heavy': profile.is_blitz_heavy,
            }
        }


# Convenience function for quick data access
def get_fetcher(years: list[int] = None) -> NFLDataFetcher:
    """Get a configured NFLDataFetcher instance."""
    return NFLDataFetcher(years)
