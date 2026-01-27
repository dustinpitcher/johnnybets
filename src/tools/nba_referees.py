"""
NBA Referee Database - Referee Tendencies for Betting Analysis (Scaffold).

This module provides NBA referee data including:
- Fouls per game averages
- Free throw rate in games officiated
- Over/under tendencies (impact on game totals)
- Home court bias metrics

Data source: To be implemented (NBA L2M reports, refstats.com, or manual entry)

Status: SCAFFOLD - Data structures defined, data integration pending.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class NBARefereeProfile:
    """Profile of an NBA referee with betting-relevant metrics."""
    name: str
    referee_id: Optional[int] = None
    games_officiated: int = 0
    
    # Foul metrics
    fouls_per_game: float = 0.0        # Total fouls called per game
    home_fouls_per_game: float = 0.0   # Fouls on home team
    away_fouls_per_game: float = 0.0   # Fouls on away team
    foul_differential: float = 0.0     # Away - Home (positive = favors home)
    
    # Free throw metrics
    ft_attempts_per_game: float = 0.0  # Total FT attempts per game
    home_ft_rate: float = 0.0          # Home team FTA rate
    away_ft_rate: float = 0.0          # Away team FTA rate
    
    # Total tendencies
    avg_total_points: float = 0.0      # Average total points in games
    over_rate: float = 0.0             # % of games going over (vs closing line)
    games_over_220: int = 0            # Count of games over 220
    games_under_220: int = 0           # Count of games under 220
    total_impact: float = 0.0          # Estimated +/- on totals
    
    # Style classification
    is_whistle_happy: bool = False     # Calls many fouls
    is_lets_them_play: bool = False    # Lets them play
    favors_home: bool = False          # Shows home court bias
    favors_overs: bool = False         # Games tend to go over
    favors_unders: bool = False        # Games tend to go under
    
    def get_foul_style(self) -> str:
        """Get foul calling style."""
        if self.fouls_per_game > 44:
            return "whistle_happy"
        elif self.fouls_per_game < 38:
            return "lets_them_play"
        else:
            return "average"
    
    def get_total_tendency(self) -> str:
        """Get over/under tendency."""
        if self.over_rate > 0.55:
            return "over"
        elif self.over_rate < 0.45:
            return "under"
        else:
            return "neutral"


@dataclass
class NBACrewAssignment:
    """Referee crew assignment for a specific game."""
    game_date: datetime
    home_team: str
    away_team: str
    crew_chief: str
    referee_1: str
    referee_2: str
    alternate: str = ""


# Known referee tendencies (placeholder data - to be updated with real data)
# Source: Would come from NBA L2M reports, refstats.com, or similar
KNOWN_REFEREES: Dict[str, NBARefereeProfile] = {
    # Example entries - these are placeholders based on public perception, NOT real data
    "scott_foster": NBARefereeProfile(
        name="Scott Foster",
        referee_id=1,
        games_officiated=1500,
        fouls_per_game=42.5,
        ft_attempts_per_game=46.2,
        avg_total_points=218.5,
        over_rate=0.47,
        total_impact=-2.5,
        is_lets_them_play=True,
        favors_unders=True,
    ),
    "tony_brothers": NBARefereeProfile(
        name="Tony Brothers",
        referee_id=2,
        games_officiated=1400,
        fouls_per_game=44.8,
        ft_attempts_per_game=49.1,
        avg_total_points=223.2,
        over_rate=0.53,
        total_impact=+1.8,
        is_whistle_happy=True,
        favors_overs=True,
    ),
    "ed_malloy": NBARefereeProfile(
        name="Ed Malloy",
        referee_id=3,
        games_officiated=1200,
        fouls_per_game=41.2,
        ft_attempts_per_game=44.8,
        avg_total_points=219.5,
        over_rate=0.49,
        total_impact=0,
    ),
    "marc_davis": NBARefereeProfile(
        name="Marc Davis",
        referee_id=4,
        games_officiated=1100,
        fouls_per_game=43.5,
        ft_attempts_per_game=47.3,
        avg_total_points=221.8,
        over_rate=0.52,
        total_impact=+1.2,
    ),
    "zach_zarba": NBARefereeProfile(
        name="Zach Zarba",
        referee_id=5,
        games_officiated=1000,
        fouls_per_game=40.8,
        ft_attempts_per_game=43.5,
        avg_total_points=217.2,
        over_rate=0.46,
        total_impact=-2.0,
        is_lets_them_play=True,
        favors_unders=True,
    ),
    "james_capers": NBARefereeProfile(
        name="James Capers",
        referee_id=6,
        games_officiated=1300,
        fouls_per_game=45.2,
        ft_attempts_per_game=50.5,
        avg_total_points=225.1,
        over_rate=0.56,
        total_impact=+3.0,
        is_whistle_happy=True,
        favors_overs=True,
    ),
}


class NBARefereeDatabase:
    """
    Database for NBA referee tendencies.
    
    SCAFFOLD: Structure implemented, data integration pending.
    
    Future enhancements:
    - Scrape data from NBA L2M reports
    - Integrate with refstats.com or similar
    - Track crew combinations (not just individuals)
    - Add player-specific matchup data (e.g., star treatment)
    """
    
    def __init__(self):
        """Initialize referee database."""
        self.referees = KNOWN_REFEREES.copy()
        self._last_updated: Optional[datetime] = None
    
    def get_referee(self, name: str) -> Optional[NBARefereeProfile]:
        """
        Get referee profile by name.
        
        Args:
            name: Referee name (flexible matching)
            
        Returns:
            NBARefereeProfile or None
        """
        # Try exact match first
        name_key = name.lower().replace(" ", "_").replace(".", "")
        if name_key in self.referees:
            return self.referees[name_key]
        
        # Try partial match
        for key, profile in self.referees.items():
            if name.lower() in profile.name.lower():
                return profile
        
        return None
    
    def get_over_refs(self, threshold: float = 0.55) -> List[NBARefereeProfile]:
        """Get referees who favor overs."""
        return [r for r in self.referees.values() if r.over_rate >= threshold]
    
    def get_under_refs(self, threshold: float = 0.45) -> List[NBARefereeProfile]:
        """Get referees who favor unders."""
        return [r for r in self.referees.values() if r.over_rate <= threshold]
    
    def get_whistle_happy_refs(self, threshold: float = 44.0) -> List[NBARefereeProfile]:
        """Get referees known for calling many fouls."""
        return [r for r in self.referees.values() if r.fouls_per_game >= threshold]
    
    def get_player_friendly_refs(self, threshold: float = 38.0) -> List[NBARefereeProfile]:
        """Get referees known for letting them play."""
        return [r for r in self.referees.values() if r.fouls_per_game <= threshold]
    
    def analyze_crew(
        self,
        crew_chief: str = None,
        referee_1: str = None,
        referee_2: str = None
    ) -> Dict[str, Any]:
        """
        Analyze referee crew for betting.
        
        Args:
            crew_chief: Crew chief name
            referee_1: First referee name
            referee_2: Second referee name
            
        Returns:
            Dict with analysis and recommendations
        """
        result = {
            "status": "scaffold",
            "note": "Full referee analysis pending data integration",
            "crew": [],
            "total_lean": None,
            "total_impact": None,
            "foul_expectation": None,
            "home_bias": None,
            "confidence": "Low",
        }
        
        refs = []
        for ref_name in [crew_chief, referee_1, referee_2]:
            if ref_name:
                profile = self.get_referee(ref_name)
                if profile:
                    refs.append(profile)
        
        if not refs:
            result["note"] = "Referees not found in database"
            return result
        
        # Average their tendencies
        avg_fouls = sum(r.fouls_per_game for r in refs) / len(refs)
        avg_ft = sum(r.ft_attempts_per_game for r in refs) / len(refs)
        avg_total = sum(r.avg_total_points for r in refs) / len(refs)
        avg_over_rate = sum(r.over_rate for r in refs) / len(refs)
        avg_impact = sum(r.total_impact for r in refs) / len(refs)
        
        result["crew"] = [
            {
                "name": r.name,
                "fouls_per_game": r.fouls_per_game,
                "ft_attempts_per_game": r.ft_attempts_per_game,
                "avg_total_points": r.avg_total_points,
                "over_rate": r.over_rate,
                "total_impact": r.total_impact,
                "style": r.get_foul_style(),
                "total_tendency": r.get_total_tendency(),
            }
            for r in refs
        ]
        
        # Determine leans
        if avg_over_rate > 0.55:
            result["total_lean"] = "OVER"
            result["confidence"] = "Medium" if avg_over_rate > 0.58 else "Low"
        elif avg_over_rate < 0.45:
            result["total_lean"] = "UNDER"
            result["confidence"] = "Medium" if avg_over_rate < 0.42 else "Low"
        else:
            result["total_lean"] = "NEUTRAL"
        
        result["total_impact"] = round(avg_impact, 1)
        
        # Foul expectation
        if avg_fouls > 44:
            result["foul_expectation"] = "HIGH - expect many free throws"
        elif avg_fouls < 38:
            result["foul_expectation"] = "LOW - refs let them play"
        else:
            result["foul_expectation"] = "AVERAGE"
        
        # FT impact
        result["ft_rate_expectation"] = f"{avg_ft:.1f} FTA/game expected"
        
        result["status"] = "success"
        
        return result
    
    def to_json(self, analysis: Dict[str, Any]) -> str:
        """Convert analysis to JSON."""
        return json.dumps(analysis, indent=2, default=str)
    
    def update_from_source(self):
        """
        Update referee data from external source.
        
        SCAFFOLD: To be implemented with web scraping from NBA sources.
        """
        # TODO: Implement scraping from NBA L2M reports
        # TODO: Parse game-by-game data for referee impact
        # TODO: Update KNOWN_REFEREES dict
        self._last_updated = datetime.now()
        raise NotImplementedError("Referee data scraping not yet implemented")


def get_referee_database() -> NBARefereeDatabase:
    """Get configured referee database instance."""
    return NBARefereeDatabase()


def analyze_refs(
    crew_chief: str = None,
    ref1: str = None,
    ref2: str = None
) -> Dict[str, Any]:
    """Convenience function for referee analysis."""
    db = NBARefereeDatabase()
    return db.analyze_crew(crew_chief, ref1, ref2)


if __name__ == "__main__":
    # Example usage
    analysis = analyze_refs("Scott Foster", "Tony Brothers")
    print(json.dumps(analysis, indent=2))
