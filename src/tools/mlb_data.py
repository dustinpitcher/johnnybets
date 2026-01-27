"""
MLB Data Fetcher and Analysis Tools

Provides comprehensive MLB betting analysis:
- Pitcher prop analysis with K projections, IP estimates, ERA context
- Defense-adjusted splits and pitch mix edges
- Park factors for all 30 stadiums
- Bullpen usage and fatigue tracking
- Weather impact on totals
- Lineup vs pitcher matchups
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import json
from datetime import datetime, timedelta


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PitcherProfile:
    """Comprehensive pitcher analytics profile."""
    name: str
    team: str
    throws: str = "R"  # R or L
    games_started: int = 0
    innings_pitched: float = 0.0
    era: float = 0.0
    whip: float = 0.0
    k_per_9: float = 0.0
    bb_per_9: float = 0.0
    hr_per_9: float = 0.0
    # Advanced metrics
    fip: float = 0.0  # Fielding Independent Pitching
    xera: float = 0.0  # Expected ERA
    xfip: float = 0.0  # Expected FIP
    stuff_plus: int = 100  # Stuff+ rating (100 = average)
    location_plus: int = 100  # Location+ rating
    # Batted ball data
    gb_pct: float = 0.0  # Ground ball percentage
    fb_pct: float = 0.0  # Fly ball percentage
    ld_pct: float = 0.0  # Line drive percentage
    hard_hit_pct: float = 0.0  # Hard hit %
    barrel_pct: float = 0.0  # Barrel %
    # Pitch mix
    pitch_mix: Dict[str, float] = field(default_factory=dict)
    # Platoon splits
    vs_rhb_era: float = 0.0
    vs_lhb_era: float = 0.0
    vs_rhb_k_pct: float = 0.0
    vs_lhb_k_pct: float = 0.0
    # Recent form (last 30 days)
    recent_era: float = 0.0
    recent_k_per_9: float = 0.0
    recent_ip_per_start: float = 0.0
    
    def is_ground_ball_pitcher(self) -> bool:
        return self.gb_pct > 45.0
    
    def is_strikeout_pitcher(self) -> bool:
        return self.k_per_9 > 9.0
    
    def has_platoon_split(self) -> bool:
        return abs(self.vs_rhb_era - self.vs_lhb_era) > 1.0
    
    def get_weak_side(self) -> str:
        if self.throws == "R":
            return "LHB" if self.vs_lhb_era > self.vs_rhb_era else "RHB"
        else:
            return "RHB" if self.vs_rhb_era > self.vs_lhb_era else "LHB"


@dataclass
class ParkFactor:
    """Park factor data for a stadium."""
    park_name: str
    team: str
    runs_factor: float = 1.0
    hr_factor: float = 1.0
    hits_factor: float = 1.0
    doubles_factor: float = 1.0
    triples_factor: float = 1.0
    strikeout_factor: float = 1.0
    # Dimensions
    lf_distance: int = 330
    cf_distance: int = 400
    rf_distance: int = 330
    # Features
    roof: str = "open"  # open, retractable, dome
    altitude: int = 0  # feet above sea level
    
    def is_hitter_friendly(self) -> bool:
        return self.runs_factor > 1.05
    
    def is_pitcher_friendly(self) -> bool:
        return self.runs_factor < 0.95
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "park_name": self.park_name,
            "team": self.team,
            "runs_factor": self.runs_factor,
            "hr_factor": self.hr_factor,
            "hits_factor": self.hits_factor,
            "strikeout_factor": self.strikeout_factor,
            "roof": self.roof,
            "altitude": self.altitude,
        }


@dataclass
class BullpenArm:
    """Individual reliever status."""
    name: str
    role: str  # closer, setup, middle, long
    days_rest: int = 0
    pitches_last_3_days: int = 0
    high_leverage: bool = False
    era: float = 0.0
    k_per_9: float = 0.0
    
    def is_available(self) -> bool:
        if self.days_rest == 0 and self.pitches_last_3_days > 30:
            return False
        if self.pitches_last_3_days > 50:
            return False
        return True
    
    def fatigue_level(self) -> str:
        if self.days_rest >= 2:
            return "fresh"
        elif self.days_rest == 1 and self.pitches_last_3_days < 30:
            return "rested"
        elif self.pitches_last_3_days > 40:
            return "fatigued"
        else:
            return "moderate"


# =============================================================================
# STATIC DATA
# =============================================================================

# All 30 MLB stadiums with park factors (2024 data)
PARK_FACTORS: Dict[str, ParkFactor] = {
    # Extreme hitter-friendly
    "COL": ParkFactor("Coors Field", "COL", runs_factor=1.35, hr_factor=1.25, 
                      strikeout_factor=0.85, altitude=5280, roof="open"),
    # Hitter-friendly
    "CIN": ParkFactor("Great American Ball Park", "CIN", runs_factor=1.15, hr_factor=1.20),
    "TEX": ParkFactor("Globe Life Field", "TEX", runs_factor=1.10, hr_factor=1.15, roof="retractable"),
    "BOS": ParkFactor("Fenway Park", "BOS", runs_factor=1.08, hr_factor=0.95, 
                      doubles_factor=1.40, lf_distance=310),
    "CHC": ParkFactor("Wrigley Field", "CHC", runs_factor=1.05, hr_factor=1.10),
    "PHI": ParkFactor("Citizens Bank Park", "PHI", runs_factor=1.05, hr_factor=1.08),
    "MIL": ParkFactor("American Family Field", "MIL", runs_factor=1.03, hr_factor=1.05, roof="retractable"),
    # Neutral
    "NYY": ParkFactor("Yankee Stadium", "NYY", runs_factor=1.02, hr_factor=1.10, rf_distance=314),
    "ATL": ParkFactor("Truist Park", "ATL", runs_factor=1.00, hr_factor=1.00),
    "HOU": ParkFactor("Minute Maid Park", "HOU", runs_factor=1.00, hr_factor=1.02, roof="retractable"),
    "LAA": ParkFactor("Angel Stadium", "LAA", runs_factor=0.98, hr_factor=0.98),
    "NYM": ParkFactor("Citi Field", "NYM", runs_factor=0.98, hr_factor=0.95),
    "DET": ParkFactor("Comerica Park", "DET", runs_factor=0.97, hr_factor=0.90, cf_distance=420),
    "MIN": ParkFactor("Target Field", "MIN", runs_factor=0.98, hr_factor=0.95),
    "CLE": ParkFactor("Progressive Field", "CLE", runs_factor=0.97, hr_factor=0.95),
    "CHW": ParkFactor("Guaranteed Rate Field", "CHW", runs_factor=1.00, hr_factor=1.05),
    "KC": ParkFactor("Kauffman Stadium", "KC", runs_factor=0.95, hr_factor=0.88),
    "BAL": ParkFactor("Camden Yards", "BAL", runs_factor=1.02, hr_factor=1.05),
    "TB": ParkFactor("Tropicana Field", "TB", runs_factor=0.95, hr_factor=0.92, roof="dome"),
    "TOR": ParkFactor("Rogers Centre", "TOR", runs_factor=1.00, hr_factor=1.02, roof="retractable"),
    "WSH": ParkFactor("Nationals Park", "WSH", runs_factor=0.98, hr_factor=1.00),
    "PIT": ParkFactor("PNC Park", "PIT", runs_factor=0.95, hr_factor=0.90),
    "STL": ParkFactor("Busch Stadium", "STL", runs_factor=0.97, hr_factor=0.95),
    "AZ": ParkFactor("Chase Field", "AZ", runs_factor=1.02, hr_factor=1.05, roof="retractable"),
    "SEA": ParkFactor("T-Mobile Park", "SEA", runs_factor=0.93, hr_factor=0.88, roof="retractable"),
    # Pitcher-friendly
    "LAD": ParkFactor("Dodger Stadium", "LAD", runs_factor=0.92, hr_factor=0.90, strikeout_factor=1.05),
    "SF": ParkFactor("Oracle Park", "SF", runs_factor=0.90, hr_factor=0.85, rf_distance=309),
    "OAK": ParkFactor("Oakland Coliseum", "OAK", runs_factor=0.88, hr_factor=0.85),
    "MIA": ParkFactor("loanDepot Park", "MIA", runs_factor=0.85, hr_factor=0.80, roof="retractable"),
    "SD": ParkFactor("Petco Park", "SD", runs_factor=0.90, hr_factor=0.88),
}

# Sample pitcher profiles (will be replaced with real data from MLB Stats API)
SAMPLE_PITCHERS: Dict[str, PitcherProfile] = {
    "spencer strider": PitcherProfile(
        name="Spencer Strider", team="ATL", throws="R",
        games_started=20, innings_pitched=110.0, era=3.15, whip=1.05,
        k_per_9=13.5, bb_per_9=2.8, hr_per_9=1.1,
        fip=3.00, xera=3.10, stuff_plus=135,
        gb_pct=32.0, fb_pct=45.0, hard_hit_pct=28.0,
        pitch_mix={"4-Seam": 55, "Slider": 40, "Changeup": 5},
        vs_rhb_era=2.90, vs_lhb_era=3.40,
        vs_rhb_k_pct=38.0, vs_lhb_k_pct=32.0,
        recent_era=2.80, recent_k_per_9=14.0, recent_ip_per_start=6.0
    ),
    "gerrit cole": PitcherProfile(
        name="Gerrit Cole", team="NYY", throws="R",
        games_started=25, innings_pitched=160.0, era=3.20, whip=1.00,
        k_per_9=11.5, bb_per_9=2.2, hr_per_9=1.0,
        fip=3.10, xera=3.05, stuff_plus=125,
        gb_pct=40.0, fb_pct=38.0, hard_hit_pct=30.0,
        pitch_mix={"4-Seam": 45, "Slider": 20, "Knuckle Curve": 20, "Changeup": 15},
        vs_rhb_era=3.10, vs_lhb_era=3.35,
        recent_era=2.50, recent_k_per_9=12.0, recent_ip_per_start=6.5
    ),
    "corbin burnes": PitcherProfile(
        name="Corbin Burnes", team="BAL", throws="R",
        games_started=28, innings_pitched=175.0, era=2.95, whip=0.98,
        k_per_9=10.0, bb_per_9=1.8, hr_per_9=0.8,
        fip=2.85, xera=2.90, stuff_plus=120,
        gb_pct=48.0, fb_pct=32.0, hard_hit_pct=26.0,
        pitch_mix={"Cutter": 40, "Sinker": 25, "Curveball": 20, "Changeup": 15},
        vs_rhb_era=2.70, vs_lhb_era=3.25,
        recent_era=2.60, recent_k_per_9=10.5, recent_ip_per_start=6.2
    ),
}


# =============================================================================
# MLB DATA FETCHER
# =============================================================================

class MLBDataFetcher:
    """
    Fetches and analyzes MLB data.
    
    Currently uses sample data - will integrate with MLB Stats API or pybaseball.
    """
    
    def __init__(self):
        pass
    
    def get_pitcher_profile(self, name: str) -> Optional[PitcherProfile]:
        """Get pitcher statistics and profile."""
        return SAMPLE_PITCHERS.get(name.lower())
    
    def get_park_factor(self, team: str) -> Optional[ParkFactor]:
        """Get park factor for a team's home stadium."""
        return PARK_FACTORS.get(team.upper())
    
    def get_all_park_factors(self) -> List[ParkFactor]:
        """Get all park factors sorted by runs factor."""
        return sorted(PARK_FACTORS.values(), key=lambda x: x.runs_factor, reverse=True)
    
    def get_bullpen_status(self, team: str) -> Dict[str, Any]:
        """Get bullpen availability and fatigue levels."""
        # Sample data - will be replaced with real tracking
        sample_arms = [
            BullpenArm("Closer", "closer", days_rest=1, pitches_last_3_days=25, high_leverage=True, era=2.50, k_per_9=12.0),
            BullpenArm("Setup Man", "setup", days_rest=0, pitches_last_3_days=35, high_leverage=True, era=3.00, k_per_9=10.5),
            BullpenArm("Middle Relief", "middle", days_rest=2, pitches_last_3_days=15, high_leverage=False, era=3.80, k_per_9=8.5),
            BullpenArm("Long Relief", "long", days_rest=3, pitches_last_3_days=0, high_leverage=False, era=4.20, k_per_9=7.0),
        ]
        
        available = [arm for arm in sample_arms if arm.is_available()]
        high_leverage_available = [arm for arm in available if arm.high_leverage]
        
        return {
            "team": team,
            "arms": [
                {
                    "name": arm.name,
                    "role": arm.role,
                    "days_rest": arm.days_rest,
                    "pitches_last_3_days": arm.pitches_last_3_days,
                    "available": arm.is_available(),
                    "fatigue": arm.fatigue_level(),
                }
                for arm in sample_arms
            ],
            "summary": {
                "total_arms": len(sample_arms),
                "available": len(available),
                "high_leverage_available": len(high_leverage_available),
                "bullpen_health": "good" if len(high_leverage_available) >= 2 else "taxed",
            },
        }
    
    def get_weather_impact(
        self,
        home_team: str,
        wind_mph: float = 0,
        wind_direction: str = "calm",
        temp_f: float = 70,
        humidity: float = 50,
    ) -> Dict[str, Any]:
        """Calculate weather impact on game total and home runs."""
        adjustment = 0.0
        hr_adjustment = 0.0
        notes = []
        
        # Wind adjustment
        if wind_mph > 10:
            if wind_direction.lower() in ["out", "blowing out", "lf", "rf", "cf"]:
                adjustment += 0.5 * (wind_mph / 10)
                hr_adjustment += 0.15 * (wind_mph / 10)
                notes.append(f"Wind blowing out {wind_mph} mph: +{adjustment:.1f} runs, favorable for HRs")
            elif wind_direction.lower() in ["in", "blowing in"]:
                adjustment -= 0.4 * (wind_mph / 10)
                hr_adjustment -= 0.20 * (wind_mph / 10)
                notes.append(f"Wind blowing in {wind_mph} mph: {adjustment:.1f} runs, suppresses HRs")
        
        # Temperature adjustment
        if temp_f < 50:
            temp_adj = -0.3 * ((50 - temp_f) / 10)
            adjustment += temp_adj
            hr_adjustment -= 0.10
            notes.append(f"Cold weather ({temp_f}°F): {temp_adj:.1f} runs, reduced ball carry")
        elif temp_f > 85:
            temp_adj = 0.25 * ((temp_f - 85) / 10)
            adjustment += temp_adj
            hr_adjustment += 0.08
            notes.append(f"Hot weather ({temp_f}°F): +{temp_adj:.1f} runs, increased ball carry")
        
        # Humidity adjustment (high humidity = slightly less HR power)
        if humidity > 70:
            hr_adjustment -= 0.05
            notes.append(f"High humidity ({humidity}%): slight HR suppression")
        
        # Park factor
        park = self.get_park_factor(home_team)
        if park:
            if park.runs_factor != 1.0:
                park_adj = (park.runs_factor - 1.0) * 10
                notes.append(f"{park.park_name}: {park_adj:+.1f} runs vs neutral park")
            if park.roof == "dome":
                notes.append("Dome stadium: weather not a factor")
                adjustment = 0
                hr_adjustment = 0
        
        return {
            "total_adjustment": round(adjustment, 2),
            "hr_adjustment": round(hr_adjustment, 2),
            "notes": notes,
            "park_factor": park.runs_factor if park else 1.0,
            "conditions": {
                "temp": temp_f,
                "wind_mph": wind_mph,
                "wind_direction": wind_direction,
                "humidity": humidity,
            },
        }


# =============================================================================
# TOOL FUNCTIONS (for agent binding)
# =============================================================================

def analyze_pitcher_props(
    pitcher_name: str,
    opponent: str,
    line_ks: float = None,
    line_ip: float = None,
    park: str = None,
) -> str:
    """
    Analyze MLB pitcher props with projections and edges.
    
    Args:
        pitcher_name: Pitcher's name
        opponent: Opposing team abbreviation
        line_ks: Strikeouts line to analyze (optional)
        line_ip: Innings pitched line to analyze (optional)
        park: Home stadium if not opponent's (optional)
    
    Returns:
        JSON analysis with projections and betting angles
    """
    fetcher = MLBDataFetcher()
    
    # Get pitcher profile
    profile = fetcher.get_pitcher_profile(pitcher_name)
    
    # Get park factor
    stadium = park or opponent
    park_factor = fetcher.get_park_factor(stadium)
    
    if not profile:
        # Return scaffold response for unknown pitchers
        return json.dumps({
            "status": "limited_data",
            "pitcher": pitcher_name,
            "opponent": opponent,
            "message": f"Full profile for {pitcher_name} not in database yet. Using general analysis.",
            "park_factor": park_factor.to_dict() if park_factor else None,
            "general_notes": [
                "Check pitcher's recent K rate (last 3 starts)",
                "Look for platoon advantages in lineup",
                "Consider park K-factor and elevation",
                "Weather (wind/temp) impacts totals more than Ks",
            ],
            "available_analysis": [
                "Park factors",
                "Weather impact",
                "Bullpen status",
            ],
        }, indent=2)
    
    # Project strikeouts
    base_k_per_start = (profile.k_per_9 / 9) * profile.recent_ip_per_start
    
    # Park adjustment for Ks
    k_park_adj = 1.0
    if park_factor:
        k_park_adj = park_factor.strikeout_factor
    
    projected_ks = base_k_per_start * k_park_adj
    
    # Analyze K line if provided
    k_analysis = None
    if line_ks is not None:
        edge = projected_ks - line_ks
        k_analysis = {
            "line": line_ks,
            "projection": round(projected_ks, 1),
            "edge": round(edge, 1),
            "recommendation": "OVER" if edge > 0.5 else "UNDER" if edge < -0.5 else "PASS",
            "confidence": "high" if abs(edge) > 1.0 else "medium" if abs(edge) > 0.5 else "low",
        }
    
    # Project innings
    projected_ip = profile.recent_ip_per_start
    ip_analysis = None
    if line_ip is not None:
        ip_edge = projected_ip - line_ip
        ip_analysis = {
            "line": line_ip,
            "projection": round(projected_ip, 1),
            "edge": round(ip_edge, 1),
            "recommendation": "OVER" if ip_edge > 0.3 else "UNDER" if ip_edge < -0.3 else "PASS",
        }
    
    return json.dumps({
        "status": "success",
        "pitcher": {
            "name": profile.name,
            "team": profile.team,
            "throws": profile.throws,
            "era": profile.era,
            "recent_era": profile.recent_era,
            "k_per_9": profile.k_per_9,
            "recent_k_per_9": profile.recent_k_per_9,
            "stuff_plus": profile.stuff_plus,
            "recent_ip_per_start": profile.recent_ip_per_start,
        },
        "opponent": opponent,
        "park": {
            "name": park_factor.park_name if park_factor else "Unknown",
            "runs_factor": park_factor.runs_factor if park_factor else 1.0,
            "k_factor": park_factor.strikeout_factor if park_factor else 1.0,
            "classification": (
                "Hitter-friendly" if park_factor and park_factor.is_hitter_friendly()
                else "Pitcher-friendly" if park_factor and park_factor.is_pitcher_friendly()
                else "Neutral"
            ),
        },
        "projections": {
            "strikeouts": round(projected_ks, 1),
            "innings": round(projected_ip, 1),
        },
        "k_analysis": k_analysis,
        "ip_analysis": ip_analysis,
        "platoon_note": f"Weaker vs {profile.get_weak_side()}" if profile.has_platoon_split() else "No significant platoon split",
        "pitch_mix": profile.pitch_mix,
        "key_factors": [
            f"Stuff+ of {profile.stuff_plus} ({'elite' if profile.stuff_plus > 120 else 'above avg' if profile.stuff_plus > 105 else 'avg'})",
            f"Recent form: {profile.recent_era} ERA, {profile.recent_k_per_9} K/9 in last 30 days",
            f"Avg {profile.recent_ip_per_start} IP per start recently",
            f"{'Ground ball pitcher' if profile.is_ground_ball_pitcher() else 'Fly ball pitcher'} ({profile.gb_pct:.0f}% GB)",
        ],
    }, indent=2)


def get_pitcher_profile(pitcher_name: str) -> str:
    """Get detailed pitcher profile and metrics."""
    fetcher = MLBDataFetcher()
    profile = fetcher.get_pitcher_profile(pitcher_name)
    
    if not profile:
        return json.dumps({
            "status": "not_found",
            "message": f"Pitcher '{pitcher_name}' not found in database",
            "suggestion": "Try full name (e.g., 'Spencer Strider', 'Gerrit Cole')",
        }, indent=2)
    
    return json.dumps({
        "status": "success",
        "name": profile.name,
        "team": profile.team,
        "throws": profile.throws,
        "traditional_stats": {
            "games_started": profile.games_started,
            "innings_pitched": profile.innings_pitched,
            "era": profile.era,
            "whip": profile.whip,
            "k_per_9": profile.k_per_9,
            "bb_per_9": profile.bb_per_9,
            "hr_per_9": profile.hr_per_9,
        },
        "advanced_stats": {
            "fip": profile.fip,
            "xera": profile.xera,
            "stuff_plus": profile.stuff_plus,
            "gb_pct": profile.gb_pct,
            "fb_pct": profile.fb_pct,
            "hard_hit_pct": profile.hard_hit_pct,
        },
        "platoon_splits": {
            "vs_rhb_era": profile.vs_rhb_era,
            "vs_lhb_era": profile.vs_lhb_era,
            "vs_rhb_k_pct": profile.vs_rhb_k_pct,
            "vs_lhb_k_pct": profile.vs_lhb_k_pct,
            "weak_side": profile.get_weak_side() if profile.has_platoon_split() else "none",
        },
        "recent_form": {
            "era": profile.recent_era,
            "k_per_9": profile.recent_k_per_9,
            "ip_per_start": profile.recent_ip_per_start,
        },
        "pitch_mix": profile.pitch_mix,
        "style": {
            "ground_ball_pitcher": profile.is_ground_ball_pitcher(),
            "strikeout_pitcher": profile.is_strikeout_pitcher(),
        },
    }, indent=2)


def get_lineup_vs_pitcher(pitcher_name: str, opponent: str) -> str:
    """Analyze how a lineup matches up vs a pitcher."""
    fetcher = MLBDataFetcher()
    profile = fetcher.get_pitcher_profile(pitcher_name)
    
    # Sample lineup matchup data
    matchup_data = {
        "status": "success",
        "pitcher": pitcher_name,
        "opponent": opponent,
        "summary": {
            "lineup_xwoba": 0.320,
            "lineup_k_rate": 24.5,
            "barrel_rate": 7.2,
            "platoon_advantage_batters": 3,
        },
        "key_matchups": [
            {"batter": "Leadoff", "xwoba": 0.380, "k_rate": 18.0, "note": "Strong vs RHP"},
            {"batter": "Cleanup", "xwoba": 0.350, "k_rate": 22.0, "note": "Power threat"},
            {"batter": "5-hole", "xwoba": 0.290, "k_rate": 30.0, "note": "K candidate"},
        ],
        "platoon_breakdown": {
            "rhb_in_lineup": 5,
            "lhb_in_lineup": 4,
        },
        "betting_angles": [],
    }
    
    if profile:
        # Add pitcher-specific analysis
        if profile.is_strikeout_pitcher():
            matchup_data["betting_angles"].append(
                f"{profile.name} has elite Ks ({profile.k_per_9} K/9) - look for K props"
            )
        if profile.has_platoon_split():
            matchup_data["betting_angles"].append(
                f"Weaker vs {profile.get_weak_side()} - check lineup construction"
            )
    
    return json.dumps(matchup_data, indent=2)


def get_park_factors(team: str) -> str:
    """Get park factors for an MLB stadium."""
    fetcher = MLBDataFetcher()
    park = fetcher.get_park_factor(team)
    
    if not park:
        # Return all parks if team not found
        all_parks = fetcher.get_all_park_factors()
        return json.dumps({
            "status": "team_not_found",
            "message": f"Team '{team}' not found. Here are all parks:",
            "parks": [
                {
                    "team": p.team,
                    "name": p.park_name,
                    "runs": p.runs_factor,
                    "hr": p.hr_factor,
                    "type": "Hitter" if p.is_hitter_friendly() else "Pitcher" if p.is_pitcher_friendly() else "Neutral",
                }
                for p in all_parks[:10]
            ],
        }, indent=2)
    
    return json.dumps({
        "status": "success",
        "team": team,
        "park_name": park.park_name,
        "factors": {
            "runs": park.runs_factor,
            "home_runs": park.hr_factor,
            "hits": park.hits_factor,
            "doubles": park.doubles_factor,
            "triples": park.triples_factor,
            "strikeouts": park.strikeout_factor,
        },
        "dimensions": {
            "left_field": park.lf_distance,
            "center_field": park.cf_distance,
            "right_field": park.rf_distance,
        },
        "features": {
            "roof": park.roof,
            "altitude": park.altitude,
        },
        "classification": (
            "Hitter-friendly" if park.is_hitter_friendly()
            else "Pitcher-friendly" if park.is_pitcher_friendly()
            else "Neutral"
        ),
        "betting_impact": {
            "total_adjustment": round((park.runs_factor - 1.0) * 9, 1),
            "note": f"Adjust totals by ~{(park.runs_factor - 1.0) * 9:+.1f} runs vs neutral park",
        },
    }, indent=2)


def analyze_bullpen_usage(team: str) -> str:
    """Analyze bullpen availability and fatigue."""
    fetcher = MLBDataFetcher()
    status = fetcher.get_bullpen_status(team)
    
    return json.dumps({
        "status": "success",
        **status,
        "betting_implications": [
            "Taxed bullpen = lean OVER on late innings" if status["summary"]["bullpen_health"] == "taxed" else "Fresh bullpen = late-game holds more likely",
            "Check closer availability for save props",
            "Middle relief fatigue impacts live betting",
        ],
    }, indent=2)


def get_weather_impact(
    home_team: str,
    wind_mph: float = 0,
    wind_direction: str = "calm", 
    temp_f: float = 70,
) -> str:
    """Get weather impact on MLB game."""
    fetcher = MLBDataFetcher()
    impact = fetcher.get_weather_impact(home_team, wind_mph, wind_direction, temp_f)
    
    return json.dumps({
        "status": "success",
        "home_team": home_team,
        **impact,
        "betting_recommendations": [
            f"Adjust total by {impact['total_adjustment']:+.1f} runs for weather" if impact['total_adjustment'] != 0 else "Weather neutral",
            "Look for HR props" if impact['hr_adjustment'] > 0.1 else "Fade HR props" if impact['hr_adjustment'] < -0.1 else "HR props neutral",
        ],
    }, indent=2)
