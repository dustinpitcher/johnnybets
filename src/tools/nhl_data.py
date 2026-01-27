"""
NHL Data Fetcher - Uses MoneyPuck CSV data for advanced hockey analytics.

This module provides NHL data including:
- Goalie stats (save %, xG save %, high-danger saves)
- Skater stats (goals, assists, Corsi, xG)
- Team-level analytics (Corsi%, xGF%, HD chances)
- Game-by-game logs for splits analysis

Data source: https://moneypuck.com/data.htm
Similar pattern to nfl_data.py using nflverse.
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Tuple
from functools import lru_cache
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import os

# MoneyPuck CSV URLs
# Season summary data (aggregated)
MONEYPUCK_BASE_URL = "https://moneypuck.com/moneypuck/playerData"
GOALIE_SEASON_URL = f"{MONEYPUCK_BASE_URL}/seasonSummary/{{season}}/regular/goalies.csv"
SKATER_SEASON_URL = f"{MONEYPUCK_BASE_URL}/seasonSummary/{{season}}/regular/skaters.csv"
TEAM_SEASON_URL = f"{MONEYPUCK_BASE_URL}/seasonSummary/{{season}}/regular/teams.csv"

# Game-level data for splits - Note: MoneyPuck may not provide these publicly
# We'll try to fetch but gracefully handle 404s
GOALIE_GAMES_URL = f"{MONEYPUCK_BASE_URL}/careers/gameByGame/regular/goalies/{{player_id}}.csv"
SKATER_GAMES_URL = f"{MONEYPUCK_BASE_URL}/careers/gameByGame/regular/skaters/{{player_id}}.csv"

# Singleton fetcher instance to avoid duplicate downloads
_FETCHER_INSTANCE: 'NHLDataFetcher' = None

# Local cache directory
CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "nhl_cache")


@dataclass
class GoalieProfile:
    """Comprehensive goalie profile with betting-relevant metrics."""
    name: str
    player_id: int
    team: str
    games_played: int
    # Core save metrics
    save_pct: float              # Actual SV%
    saves: int
    shots_against: int
    goals_against: float
    # Expected goals metrics
    xg_against: float            # Expected goals against
    xg_save_pct: float           # Expected SV% based on shot quality
    luck_factor: float           # Actual SV% - xG SV% (positive = overperforming)
    # High-danger metrics
    high_danger_shots_against: int
    high_danger_goals_against: int
    high_danger_sv_pct: float    # HD save %
    # Workload
    shots_against_per_game: float
    minutes_played: float
    # Back-to-back tracking (calculated separately)
    b2b_games: int = 0
    b2b_save_pct: float = 0.0
    rested_games: int = 0        # 2+ days rest
    rested_save_pct: float = 0.0
    
    def is_overperforming(self, threshold: float = 0.01) -> bool:
        """Check if goalie is overperforming xG (luck regression candidate)."""
        return self.luck_factor > threshold
    
    def is_high_volume_goalie(self, threshold: float = 30.0) -> bool:
        """Check if goalie faces high shot volume (30+ shots/game)."""
        return self.shots_against_per_game >= threshold
    
    def get_b2b_penalty(self) -> float:
        """Calculate SV% drop on back-to-backs."""
        if self.b2b_games > 0 and self.rested_games > 0:
            return self.rested_save_pct - self.b2b_save_pct
        return 0.0


@dataclass
class SkaterProfile:
    """Skater profile with Corsi and xG metrics."""
    name: str
    player_id: int
    team: str
    position: str
    games_played: int
    # Scoring
    goals: int
    assists: int
    points: int
    # Expected metrics
    xg: float                    # Expected goals
    xg_diff: float               # Goals - xG (positive = finishing above expected)
    # Corsi/Fenwick
    corsi_for: int
    corsi_against: int
    corsi_pct: float             # CF / (CF + CA)
    # Ice time
    toi_per_game: float          # Time on ice per game (minutes)
    # High-danger
    high_danger_goals: int
    high_danger_chances: int


@dataclass  
class TeamProfile:
    """Team-level advanced metrics for matchup analysis."""
    team: str
    games_played: int
    # Corsi (shot attempts)
    corsi_for_per_game: float
    corsi_against_per_game: float
    corsi_pct: float              # Possession proxy
    # Expected goals
    xg_for_per_game: float
    xg_against_per_game: float
    xg_diff_per_game: float       # xGF - xGA
    # High-danger chances
    hd_chances_for: float
    hd_chances_against: float
    hd_pct: float                 # HD CF / (HD CF + HD CA)
    # Goals
    goals_for_per_game: float
    goals_against_per_game: float
    # Special teams
    pp_pct: float                 # Power play %
    pk_pct: float                 # Penalty kill %
    
    def get_style(self) -> str:
        """Classify team playing style."""
        if self.corsi_pct > 52 and self.xg_for_per_game > 3.0:
            return "offensive_possession"
        elif self.corsi_pct < 48 and self.xg_against_per_game < 2.5:
            return "defensive_counter"
        elif self.hd_pct > 52:
            return "high_danger_focused"
        else:
            return "balanced"


class NHLDataFetcher:
    """Fetches and caches NHL data from MoneyPuck CSV files."""
    
    def __init__(self, seasons: List[int] = None):
        """
        Initialize the data fetcher.
        
        Args:
            seasons: List of seasons to load. Format: 2024 means 2024-25 season.
                     Defaults to current and previous season.
        """
        current_year = datetime.now().year
        # NHL season spans two years - if we're past October, current season is this year
        if datetime.now().month >= 10:
            default_seasons = [current_year, current_year - 1]
        else:
            default_seasons = [current_year - 1, current_year - 2]
        
        self.seasons = seasons or default_seasons
        self._goalie_cache: dict[int, pd.DataFrame] = {}
        self._skater_cache: dict[int, pd.DataFrame] = {}
        self._team_cache: dict[int, pd.DataFrame] = {}
        self._goalie_games_cache: dict[int, pd.DataFrame] = {}
        self._goalie_profiles_cache: dict[str, GoalieProfile] = {}
        self._team_profiles_cache: dict[str, TeamProfile] = {}
        
        # Ensure cache directory exists
        os.makedirs(CACHE_DIR, exist_ok=True)
    
    def _get_cached_or_download(self, url: str, cache_name: str, max_age_hours: int = 24) -> pd.DataFrame:
        """Download data or use cached version if fresh enough."""
        cache_path = os.path.join(CACHE_DIR, f"{cache_name}.csv")
        
        # Check if cache exists and is fresh
        if os.path.exists(cache_path):
            cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_path))
            if cache_age < timedelta(hours=max_age_hours):
                print(f"   📂 Using cached: {cache_name} (age: {cache_age.total_seconds()/3600:.1f}h)")
                return pd.read_csv(cache_path)
            else:
                print(f"   🔄 Cache expired: {cache_name}")
        
        print(f"   ⬇️ Downloading: {url}")
        try:
            df = pd.read_csv(url)
            # Cache for next time
            df.to_csv(cache_path, index=False)
            return df
        except Exception as e:
            print(f"   ⚠️ Failed to download {url}: {e}")
            # Try to use stale cache if download fails
            if os.path.exists(cache_path):
                print(f"   📂 Using stale cache: {cache_name}")
                return pd.read_csv(cache_path)
            return pd.DataFrame()
    
    # =========================================================================
    # GOALIE DATA
    # =========================================================================
    
    def get_goalie_season_stats(self, season: int = None) -> pd.DataFrame:
        """
        Fetch goalie season summary stats from MoneyPuck.
        
        Args:
            season: Season year (e.g., 2024 for 2024-25). Defaults to most recent.
            
        Returns:
            DataFrame with goalie stats including xG, save %, high-danger saves.
        """
        season = season or self.seasons[0]
        
        if season not in self._goalie_cache:
            print(f"🥅 Loading goalie data for {season}-{str(season+1)[-2:]}...")
            url = GOALIE_SEASON_URL.format(season=season)
            self._goalie_cache[season] = self._get_cached_or_download(
                url, f"goalies_{season}"
            )
        
        return self._goalie_cache[season]
    
    def get_goalie_game_logs(self, season: int = None, player_id: int = None) -> pd.DataFrame:
        """
        Fetch goalie game-by-game logs for splits analysis.
        
        NOTE: MoneyPuck requires player_id for game-level data and it's per-player.
        For bulk analysis, we return an empty DataFrame and skip B2B calculations.
        B2B status should be determined from schedule data instead.
        
        Args:
            season: Season year.
            player_id: Player ID (required for MoneyPuck game-level data)
            
        Returns:
            DataFrame with per-game goalie stats, or empty if not available.
        """
        # MoneyPuck doesn't provide bulk game logs - only per-player with player_id
        # For now, return empty DataFrame and handle B2B via schedule/external data
        if player_id is None:
            # No player_id means we can't fetch game logs from MoneyPuck
            return pd.DataFrame()
        
        season = season or self.seasons[0]
        cache_key = f"{player_id}_{season}"
        
        if cache_key not in self._goalie_games_cache:
            print(f"📊 Loading goalie game logs for player {player_id}...")
            url = GOALIE_GAMES_URL.format(player_id=player_id)
            self._goalie_games_cache[cache_key] = self._get_cached_or_download(
                url, f"goalie_games_{player_id}_{season}"
            )
        
        return self._goalie_games_cache.get(cache_key, pd.DataFrame())
    
    def get_goalie_profile(self, goalie_name: str, season: int = None) -> Optional[GoalieProfile]:
        """
        Get comprehensive goalie profile with betting-relevant metrics.
        
        Args:
            goalie_name: Goalie name (flexible matching)
            season: Season year
            
        Returns:
            GoalieProfile dataclass or None if not found
        """
        season = season or self.seasons[0]
        cache_key = f"{goalie_name}_{season}"
        
        if cache_key in self._goalie_profiles_cache:
            return self._goalie_profiles_cache[cache_key]
        
        # Get season stats
        goalies_df = self.get_goalie_season_stats(season)
        if goalies_df.empty:
            return None
        
        # Flexible name matching
        name_lower = goalie_name.lower()
        mask = goalies_df['name'].str.lower().str.contains(name_lower, na=False)
        
        if not mask.any():
            # Try last name only
            last_name = goalie_name.split()[-1].lower() if " " in goalie_name else name_lower
            mask = goalies_df['name'].str.lower().str.contains(last_name, na=False)
        
        if not mask.any():
            print(f"   ⚠️ Goalie not found: {goalie_name}")
            return None
        
        # MoneyPuck has multiple rows per goalie (situation: all, 5on5, 4on5, 5on4, other)
        # We want the 'all' situation for total stats
        goalie_rows = goalies_df[mask]
        if 'situation' in goalie_rows.columns:
            all_situation = goalie_rows[goalie_rows['situation'] == 'all']
            if not all_situation.empty:
                goalie = all_situation.iloc[0]
            else:
                goalie = goalie_rows.iloc[0]
        else:
            goalie = goalie_rows.iloc[0]
        
        # MoneyPuck column names:
        # - ongoal: shots on goal (against)
        # - goals: goals allowed
        # - xGoals: expected goals against
        # - highDangerShots: HD shots faced
        # - highDangerGoals: HD goals allowed
        shots_against = int(goalie.get('ongoal', 0) or 0)
        goals_against = int(goalie.get('goals', 0) or 0)
        saves = shots_against - goals_against
        games = int(goalie.get('games_played', 0) or 1)
        
        # xG metrics
        xg_against = float(goalie.get('xGoals', 0) or 0)
        
        # Calculate save percentages
        save_pct = saves / shots_against if shots_against > 0 else 0.0
        xg_save_pct = 1 - (xg_against / shots_against) if shots_against > 0 else 0.0
        luck_factor = save_pct - xg_save_pct
        
        # High-danger metrics
        hd_shots = int(goalie.get('highDangerShots', 0) or 0)
        hd_goals = int(goalie.get('highDangerGoals', 0) or 0)
        hd_save_pct = 1 - (hd_goals / hd_shots) if hd_shots > 0 else 0.0
        
        profile = GoalieProfile(
            name=goalie.get('name', goalie_name),
            player_id=goalie.get('playerId', 0),
            team=goalie.get('team', 'UNK'),
            games_played=games,
            save_pct=round(save_pct, 4),
            saves=saves,
            shots_against=shots_against,
            goals_against=goals_against,
            xg_against=round(xg_against, 2),
            xg_save_pct=round(xg_save_pct, 4),
            luck_factor=round(luck_factor, 4),
            high_danger_shots_against=hd_shots,
            high_danger_goals_against=hd_goals,
            high_danger_sv_pct=round(hd_save_pct, 4),
            shots_against_per_game=round(shots_against / games, 1) if games > 0 else 0,
            minutes_played=goalie.get('icetime', 0) or goalie.get('TOI', 0) or 0,
        )
        
        # Calculate B2B splits from game logs (if available)
        # Note: MoneyPuck requires player_id for game-level data
        player_id = goalie.get('playerId', 0)
        profile = self._add_b2b_splits(profile, goalie_name, season, player_id)
        
        self._goalie_profiles_cache[cache_key] = profile
        return profile
    
    def _add_b2b_splits(self, profile: GoalieProfile, goalie_name: str, season: int, player_id: int = None) -> GoalieProfile:
        """
        Calculate back-to-back performance splits for a goalie.
        
        Note: MoneyPuck requires player_id for game-level data. If not available,
        B2B splits will be empty and the analyzer should use the is_back_to_back
        flag from the user input instead.
        """
        game_logs = self.get_goalie_game_logs(season, player_id)
        
        if game_logs.empty:
            # No game logs available - B2B analysis will use default estimates
            return profile
        
        # Filter to this goalie
        name_lower = goalie_name.lower()
        mask = game_logs['name'].str.lower().str.contains(name_lower, na=False)
        if not mask.any():
            last_name = goalie_name.split()[-1].lower() if " " in goalie_name else name_lower
            mask = game_logs['name'].str.lower().str.contains(last_name, na=False)
        
        if not mask.any():
            return profile
        
        goalie_games = game_logs[mask].copy()
        
        # Need game dates to identify B2B
        if 'gameDate' not in goalie_games.columns and 'game_date' not in goalie_games.columns:
            return profile
        
        date_col = 'gameDate' if 'gameDate' in goalie_games.columns else 'game_date'
        goalie_games['date'] = pd.to_datetime(goalie_games[date_col])
        goalie_games = goalie_games.sort_values('date')
        
        # Identify B2B games (played day after previous game)
        goalie_games['days_rest'] = goalie_games['date'].diff().dt.days
        goalie_games['is_b2b'] = goalie_games['days_rest'] == 1
        
        # Calculate splits
        shots_col = 'shotsOnGoalAgainst' if 'shotsOnGoalAgainst' in goalie_games.columns else 'shots'
        saves_col = 'saves' if 'saves' in goalie_games.columns else None
        
        if saves_col and shots_col in goalie_games.columns:
            b2b_games = goalie_games[goalie_games['is_b2b']]
            rested_games = goalie_games[goalie_games['days_rest'] >= 2]
            
            if len(b2b_games) > 0:
                b2b_saves = b2b_games[saves_col].sum()
                b2b_shots = b2b_games[shots_col].sum()
                profile.b2b_games = len(b2b_games)
                profile.b2b_save_pct = round(b2b_saves / b2b_shots, 4) if b2b_shots > 0 else 0
            
            if len(rested_games) > 0:
                rested_saves = rested_games[saves_col].sum()
                rested_shots = rested_games[shots_col].sum()
                profile.rested_games = len(rested_games)
                profile.rested_save_pct = round(rested_saves / rested_shots, 4) if rested_shots > 0 else 0
        
        return profile
    
    def find_goalies_by_team(self, team: str, season: int = None) -> List[GoalieProfile]:
        """Get all goalies for a specific team."""
        season = season or self.seasons[0]
        goalies_df = self.get_goalie_season_stats(season)
        
        if goalies_df.empty:
            return []
        
        team_upper = team.upper()
        mask = goalies_df['team'].str.upper() == team_upper
        
        profiles = []
        for _, goalie in goalies_df[mask].iterrows():
            profile = self.get_goalie_profile(goalie['name'], season)
            if profile:
                profiles.append(profile)
        
        return profiles
    
    # =========================================================================
    # SKATER DATA
    # =========================================================================
    
    def get_skater_season_stats(self, season: int = None) -> pd.DataFrame:
        """Fetch skater season summary stats from MoneyPuck."""
        season = season or self.seasons[0]
        
        if season not in self._skater_cache:
            print(f"🏒 Loading skater data for {season}-{str(season+1)[-2:]}...")
            url = SKATER_SEASON_URL.format(season=season)
            self._skater_cache[season] = self._get_cached_or_download(
                url, f"skaters_{season}"
            )
        
        return self._skater_cache[season]
    
    def get_skater_profile(self, player_name: str, season: int = None) -> Optional[SkaterProfile]:
        """Get skater profile with Corsi and xG metrics."""
        season = season or self.seasons[0]
        skaters_df = self.get_skater_season_stats(season)
        
        if skaters_df.empty:
            return None
        
        # Flexible name matching
        name_lower = player_name.lower()
        mask = skaters_df['name'].str.lower().str.contains(name_lower, na=False)
        
        if not mask.any():
            last_name = player_name.split()[-1].lower() if " " in player_name else name_lower
            mask = skaters_df['name'].str.lower().str.contains(last_name, na=False)
        
        if not mask.any():
            return None
        
        player = skaters_df[mask].iloc[0]
        games = player.get('games_played', 0) or player.get('GP', 0) or 1
        
        # Corsi metrics
        cf = player.get('CorsiFor', 0) or player.get('CF', 0) or 0
        ca = player.get('CorsiAgainst', 0) or player.get('CA', 0) or 0
        corsi_pct = cf / (cf + ca) * 100 if (cf + ca) > 0 else 50.0
        
        return SkaterProfile(
            name=player.get('name', player_name),
            player_id=player.get('playerId', 0),
            team=player.get('team', 'UNK'),
            position=player.get('position', 'F'),
            games_played=games,
            goals=player.get('goals', 0) or player.get('G', 0) or 0,
            assists=player.get('assists', 0) or player.get('A', 0) or 0,
            points=player.get('points', 0) or player.get('P', 0) or 0,
            xg=player.get('xGoals', 0) or player.get('ixG', 0) or 0,
            xg_diff=player.get('goals', 0) - player.get('xGoals', 0) if player.get('xGoals') else 0,
            corsi_for=cf,
            corsi_against=ca,
            corsi_pct=round(corsi_pct, 1),
            toi_per_game=round(player.get('icetime', 0) / games / 60, 1) if games > 0 else 0,
            high_danger_goals=player.get('highDangerGoals', 0) or 0,
            high_danger_chances=player.get('highDangerShots', 0) or 0,
        )
    
    # =========================================================================
    # TEAM DATA
    # =========================================================================
    
    def get_team_season_stats(self, season: int = None) -> pd.DataFrame:
        """Fetch team-level season stats from MoneyPuck."""
        season = season or self.seasons[0]
        
        if season not in self._team_cache:
            print(f"🏟️ Loading team data for {season}-{str(season+1)[-2:]}...")
            url = TEAM_SEASON_URL.format(season=season)
            self._team_cache[season] = self._get_cached_or_download(
                url, f"teams_{season}"
            )
        
        return self._team_cache[season]
    
    def get_team_profile(self, team: str, season: int = None) -> Optional[TeamProfile]:
        """Get team profile with Corsi and xG metrics."""
        season = season or self.seasons[0]
        cache_key = f"{team}_{season}"
        
        if cache_key in self._team_profiles_cache:
            return self._team_profiles_cache[cache_key]
        
        teams_df = self.get_team_season_stats(season)
        
        if teams_df.empty:
            # Try aggregating from skater data
            return self._build_team_profile_from_skaters(team, season)
        
        team_upper = team.upper()
        mask = teams_df['team'].str.upper() == team_upper
        
        if not mask.any():
            return None
        
        team_data = teams_df[mask].iloc[0]
        games = team_data.get('games_played', 0) or team_data.get('GP', 0) or 1
        
        # Corsi
        cf = team_data.get('CorsiFor', 0) or 0
        ca = team_data.get('CorsiAgainst', 0) or 0
        corsi_pct = cf / (cf + ca) * 100 if (cf + ca) > 0 else 50.0
        
        # xG
        xgf = team_data.get('xGoalsFor', 0) or 0
        xga = team_data.get('xGoalsAgainst', 0) or 0
        
        # HD
        hd_for = team_data.get('highDangerShotsFor', 0) or 0
        hd_against = team_data.get('highDangerShotsAgainst', 0) or 0
        hd_pct = hd_for / (hd_for + hd_against) * 100 if (hd_for + hd_against) > 0 else 50.0
        
        profile = TeamProfile(
            team=team_upper,
            games_played=games,
            corsi_for_per_game=round(cf / games, 1) if games > 0 else 0,
            corsi_against_per_game=round(ca / games, 1) if games > 0 else 0,
            corsi_pct=round(corsi_pct, 1),
            xg_for_per_game=round(xgf / games, 2) if games > 0 else 0,
            xg_against_per_game=round(xga / games, 2) if games > 0 else 0,
            xg_diff_per_game=round((xgf - xga) / games, 2) if games > 0 else 0,
            hd_chances_for=round(hd_for / games, 1) if games > 0 else 0,
            hd_chances_against=round(hd_against / games, 1) if games > 0 else 0,
            hd_pct=round(hd_pct, 1),
            goals_for_per_game=round(team_data.get('goalsFor', 0) / games, 2) if games > 0 else 0,
            goals_against_per_game=round(team_data.get('goalsAgainst', 0) / games, 2) if games > 0 else 0,
            pp_pct=team_data.get('powerPlayPct', 0) or 0,
            pk_pct=team_data.get('penaltyKillPct', 0) or 0,
        )
        
        self._team_profiles_cache[cache_key] = profile
        return profile
    
    def _build_team_profile_from_skaters(self, team: str, season: int) -> Optional[TeamProfile]:
        """Build team profile by aggregating skater stats (fallback method)."""
        skaters_df = self.get_skater_season_stats(season)
        
        if skaters_df.empty:
            return None
        
        team_upper = team.upper()
        team_skaters = skaters_df[skaters_df['team'].str.upper() == team_upper]
        
        if team_skaters.empty:
            return None
        
        # Aggregate (rough approximation)
        games = team_skaters['games_played'].max() if 'games_played' in team_skaters.columns else 1
        
        return TeamProfile(
            team=team_upper,
            games_played=games,
            corsi_for_per_game=0,
            corsi_against_per_game=0,
            corsi_pct=50.0,
            xg_for_per_game=team_skaters['xGoals'].sum() / games if 'xGoals' in team_skaters.columns else 0,
            xg_against_per_game=0,
            xg_diff_per_game=0,
            hd_chances_for=0,
            hd_chances_against=0,
            hd_pct=50.0,
            goals_for_per_game=team_skaters['goals'].sum() / games if 'goals' in team_skaters.columns else 0,
            goals_against_per_game=0,
            pp_pct=0,
            pk_pct=0,
        )
    
    # =========================================================================
    # MATCHUP ANALYSIS
    # =========================================================================
    
    def compare_teams(self, team_a: str, team_b: str, season: int = None) -> dict:
        """
        Compare two teams for matchup analysis.
        
        Returns dict with each team's profile and edge indicators.
        """
        season = season or self.seasons[0]
        
        profile_a = self.get_team_profile(team_a, season)
        profile_b = self.get_team_profile(team_b, season)
        
        if not profile_a or not profile_b:
            return {"error": "Could not load team profiles"}
        
        return {
            "teams": {
                team_a: {
                    "corsi_pct": profile_a.corsi_pct,
                    "xg_diff": profile_a.xg_diff_per_game,
                    "hd_pct": profile_a.hd_pct,
                    "style": profile_a.get_style(),
                },
                team_b: {
                    "corsi_pct": profile_b.corsi_pct,
                    "xg_diff": profile_b.xg_diff_per_game,
                    "hd_pct": profile_b.hd_pct,
                    "style": profile_b.get_style(),
                }
            },
            "edges": {
                "possession_edge": team_a if profile_a.corsi_pct > profile_b.corsi_pct else team_b,
                "xg_edge": team_a if profile_a.xg_diff_per_game > profile_b.xg_diff_per_game else team_b,
                "hd_edge": team_a if profile_a.hd_pct > profile_b.hd_pct else team_b,
            }
        }


# Convenience function with singleton pattern
def get_nhl_fetcher(seasons: List[int] = None) -> NHLDataFetcher:
    """
    Get a configured NHLDataFetcher instance.
    
    Uses singleton pattern to avoid creating multiple instances
    and downloading data multiple times.
    """
    global _FETCHER_INSTANCE
    
    if _FETCHER_INSTANCE is None:
        _FETCHER_INSTANCE = NHLDataFetcher(seasons)
    
    return _FETCHER_INSTANCE

