"""
NHL Referee Database - Referee Tendencies for Betting Analysis (Scaffold).

This module provides referee and linesmen data including:
- Penalties per game averages
- Power play % in games officiated
- Over/under tendencies (do they call tight or loose games?)
- Historical game totals

Data source: To be implemented (scoutingtherefs.com or manual entry)

Status: SCAFFOLD - Data structures defined, data integration pending.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

import os


@dataclass
class RefereeProfile:
    """Profile of an NHL referee with betting-relevant metrics."""
    name: str
    referee_id: Optional[int] = None
    games_officiated: int = 0
    
    # Penalty metrics
    penalties_per_game: float = 0.0        # Total penalties called per game
    home_penalties_per_game: float = 0.0   # Penalties on home team
    away_penalties_per_game: float = 0.0   # Penalties on away team
    
    # Power play metrics
    powerplays_per_game: float = 0.0       # Total PP opportunities per game
    avg_pp_goals_per_game: float = 0.0     # PP goals in games they ref
    
    # Total tendencies
    avg_total_goals: float = 0.0           # Average total goals in games
    over_rate: float = 0.0                 # % of games going over (vs closing line)
    games_over_5_5: int = 0                # Count of games over 5.5
    games_under_5_5: int = 0               # Count of games under 5.5
    
    # Style classification
    is_tight_caller: bool = False          # Calls many penalties
    is_loose_caller: bool = False          # Lets them play
    favors_overs: bool = False             # Games tend to go over
    favors_unders: bool = False            # Games tend to go under
    
    def get_penalty_style(self) -> str:
        """Get penalty calling style."""
        if self.penalties_per_game > 8.5:
            return "tight"
        elif self.penalties_per_game < 6.5:
            return "loose"
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
class RefereeAssignment:
    """Referee assignment for a specific game."""
    game_date: datetime
    home_team: str
    away_team: str
    referee_1: str
    referee_2: str
    linesman_1: str = ""
    linesman_2: str = ""


# Known referee tendencies (placeholder data - to be updated with real data)
# Source: This would come from scoutingtherefs.com or similar
KNOWN_REFEREES: Dict[str, RefereeProfile] = {
    # Example entries - these are placeholders, not real data
    "wes_mccauley": RefereeProfile(
        name="Wes McCauley",
        referee_id=1,
        games_officiated=100,
        penalties_per_game=7.8,
        avg_total_goals=5.8,
        over_rate=0.52,
        is_tight_caller=False,
        favors_overs=True,
    ),
    "chris_rooney": RefereeProfile(
        name="Chris Rooney",
        referee_id=2,
        games_officiated=100,
        penalties_per_game=8.2,
        avg_total_goals=6.1,
        over_rate=0.56,
        is_tight_caller=True,
        favors_overs=True,
    ),
    "frederick_lheureux": RefereeProfile(
        name="Frederick L'Heureux",
        referee_id=3,
        games_officiated=80,
        penalties_per_game=9.1,
        avg_total_goals=6.3,
        over_rate=0.58,
        is_tight_caller=True,
        favors_overs=True,
    ),
}


class NHLRefereeDatabase:
    """
    Database for NHL referee tendencies.
    
    SCAFFOLD: Structure implemented, data integration pending.
    
    Future enhancements:
    - Scrape data from scoutingtherefs.com
    - Update data automatically before game day
    - Add linesmen analysis
    - Add crew combination analysis
    """
    
    def __init__(self):
        """Initialize referee database."""
        self.referees = KNOWN_REFEREES.copy()
        self._last_updated: Optional[datetime] = None
    
    def get_referee(self, name: str) -> Optional[RefereeProfile]:
        """
        Get referee profile by name.
        
        Args:
            name: Referee name (flexible matching)
            
        Returns:
            RefereeProfile or None
        """
        # Try exact match first
        name_key = name.lower().replace(" ", "_").replace("'", "")
        if name_key in self.referees:
            return self.referees[name_key]
        
        # Try partial match
        for key, profile in self.referees.items():
            if name.lower() in profile.name.lower():
                return profile
        
        return None
    
    def get_over_refs(self, threshold: float = 0.55) -> List[RefereeProfile]:
        """Get referees who favor overs."""
        return [r for r in self.referees.values() if r.over_rate >= threshold]
    
    def get_tight_callers(self, threshold: float = 8.5) -> List[RefereeProfile]:
        """Get referees known for calling many penalties."""
        return [r for r in self.referees.values() if r.penalties_per_game >= threshold]
    
    def get_loose_callers(self, threshold: float = 6.5) -> List[RefereeProfile]:
        """Get referees known for letting them play."""
        return [r for r in self.referees.values() if r.penalties_per_game <= threshold]
    
    def analyze_game_refs(
        self,
        referee_1: str = None,
        referee_2: str = None
    ) -> Dict[str, Any]:
        """
        Analyze referee assignment for betting.
        
        Args:
            referee_1: First referee name
            referee_2: Second referee name
            
        Returns:
            Dict with analysis and recommendations
        """
        result = {
            "status": "scaffold",
            "note": "Full referee analysis pending data integration",
            "referees": [],
            "total_lean": None,
            "penalty_expectation": None,
            "confidence": "Low",
        }
        
        refs = []
        for ref_name in [referee_1, referee_2]:
            if ref_name:
                profile = self.get_referee(ref_name)
                if profile:
                    refs.append(profile)
        
        if not refs:
            result["note"] = "Referees not found in database"
            return result
        
        # Average their tendencies
        avg_penalties = sum(r.penalties_per_game for r in refs) / len(refs)
        avg_total = sum(r.avg_total_goals for r in refs) / len(refs)
        avg_over_rate = sum(r.over_rate for r in refs) / len(refs)
        
        result["referees"] = [
            {
                "name": r.name,
                "penalties_per_game": r.penalties_per_game,
                "avg_total_goals": r.avg_total_goals,
                "over_rate": r.over_rate,
                "style": r.get_penalty_style(),
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
        
        if avg_penalties > 8.5:
            result["penalty_expectation"] = "HIGH - expect many power plays"
        elif avg_penalties < 6.5:
            result["penalty_expectation"] = "LOW - refs let them play"
        
        result["status"] = "success"
        
        return result
    
    def to_json(self, analysis: Dict[str, Any]) -> str:
        """Convert analysis to JSON."""
        return json.dumps(analysis, indent=2, default=str)
    
    def update_from_source(self):
        """
        Update referee data from external source.
        
        SCAFFOLD: To be implemented with web scraping from scoutingtherefs.com
        """
        # TODO: Implement scraping from scoutingtherefs.com
        # TODO: Parse HTML tables for referee stats
        # TODO: Update KNOWN_REFEREES dict
        self._last_updated = datetime.now()
        raise NotImplementedError("Referee data scraping not yet implemented")


def get_referee_database() -> NHLRefereeDatabase:
    """Get configured referee database instance."""
    return NHLRefereeDatabase()


def analyze_refs(ref1: str = None, ref2: str = None) -> Dict[str, Any]:
    """Convenience function for referee analysis."""
    db = NHLRefereeDatabase()
    return db.analyze_game_refs(ref1, ref2)


if __name__ == "__main__":
    # Example usage
    analysis = analyze_refs("Wes McCauley", "Chris Rooney")
    print(json.dumps(analysis, indent=2))




