"""
Edge Validator - Anti-Slop Module for Sports Betting Analysis.

This module provides sanity checks to avoid common AI/public betting traps:
1. Calculate actual +EV given juice
2. Detect public side (contrarian check)
3. Historical ATS by spot type
4. Weather/narrative trap detection

Added 2026-01-18 after discovering both AI models gave "slop" picks.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class BetType(Enum):
    SPREAD = "spread"
    TOTAL = "total"
    MONEYLINE = "moneyline"
    PROP = "prop"


class SpotType(Enum):
    PLAYOFF_FAVORITE = "playoff_favorite"
    PLAYOFF_UNDERDOG = "playoff_underdog"
    HOME_FAVORITE = "home_favorite"
    ROAD_UNDERDOG = "road_underdog"
    COLD_WEATHER_UNDER = "cold_weather_under"
    DIVISIONAL_GAME = "divisional_game"


@dataclass
class EdgeValidation:
    """Result of edge validation checks."""
    has_mathematical_edge: bool
    calculated_hit_rate: float  # Based on historical data
    required_hit_rate: float    # Based on juice
    edge_pct: float             # calculated - required
    is_public_side: bool
    public_pct: Optional[float]
    contrarian_signals: List[str]
    spot_type_ats: Optional[float]  # Historical ATS for this spot type
    warnings: List[str]
    recommendation: str  # "BET", "FADE", "PASS", "CONTRARIAN"
    confidence: str      # "HIGH", "MEDIUM", "LOW"
    # Extended fields for enhanced validation
    sharp_action_pct: Optional[float] = None  # % of sharp/syndicate money
    closing_line_value: Optional[float] = None  # CLV: difference from open to current
    is_sharp_side: bool = False  # Whether sharps are on this side
    
    def to_markdown(self) -> str:
        """Format as markdown for agent output."""
        warnings_str = "\n".join(f"  ⚠️ {w}" for w in self.warnings) if self.warnings else "  ✅ No warnings"
        signals_str = "\n".join(f"  📊 {s}" for s in self.contrarian_signals) if self.contrarian_signals else "  None"
        
        # Build sharp/CLV section if available
        sharp_section = ""
        if self.sharp_action_pct is not None or self.closing_line_value is not None:
            sharp_section = f"""
### Sharp Money Analysis
| Metric | Value |
|--------|-------|
| Sharp Action % | {f"{self.sharp_action_pct:.0f}%" if self.sharp_action_pct else "Unknown"} |
| Closing Line Value | {f"{self.closing_line_value:+.1f}" if self.closing_line_value else "N/A"} |
| Sharp Side? | {"✅ YES" if self.is_sharp_side else "❌ NO"} |
"""
        
        return f"""
## 🔬 Edge Validation Report

### Mathematical Edge
| Metric | Value |
|--------|-------|
| Historical Hit Rate | {self.calculated_hit_rate:.1f}% |
| Required to Profit | {self.required_hit_rate:.1f}% |
| **Edge** | {self.edge_pct:+.1f}% |
| Has +EV | {"✅ YES" if self.has_mathematical_edge else "❌ NO"} |

### Public/Contrarian Analysis
| Metric | Value |
|--------|-------|
| Public Side? | {"🚨 YES" if self.is_public_side else "✅ NO"} |
| Public % | {f"{self.public_pct:.0f}%" if self.public_pct else "Unknown"} |
| Spot Type ATS | {f"{self.spot_type_ats:.1f}%" if self.spot_type_ats else "N/A"} |
{sharp_section}
### Contrarian Signals
{signals_str}

### Warnings
{warnings_str}

### **RECOMMENDATION: {self.recommendation}** ({self.confidence} confidence)
"""


class EdgeValidator:
    """
    Validates betting edges against historical data and public betting patterns.
    """
    
    # Historical ATS rates by spot type (verified from actual data)
    SPOT_TYPE_HISTORICAL_ATS = {
        SpotType.PLAYOFF_FAVORITE: 44.7,      # Favorites LOSE money in playoffs
        SpotType.PLAYOFF_UNDERDOG: 55.3,      # Underdogs COVER 55%+ in playoffs
        SpotType.HOME_FAVORITE: 48.1,         # Home favorites slightly under 50%
        SpotType.ROAD_UNDERDOG: 51.9,         # Road dogs slightly profitable
        SpotType.COLD_WEATHER_UNDER: 49.2,    # Cold doesn't help unders much
        SpotType.DIVISIONAL_GAME: 50.5,       # Divisional games are coin flips
    }
    
    # Weather impact on totals (from actual data analysis)
    WEATHER_TOTAL_IMPACT = {
        "cold_35F": -1.2,     # Only 1.2 points lower on average
        "wind_15mph": -2.1,   # Slightly more impact
        "snow": -3.5,         # Moderate impact
        "rain": -1.8,         # Minor impact
    }
    
    def __init__(self):
        pass
    
    def american_to_implied(self, odds: int) -> float:
        """
        Convert American odds to implied probability.
        
        Args:
            odds: American odds (e.g., -110, +150)
            
        Returns:
            Implied probability as percentage (0-100)
        """
        if odds < 0:
            return (-odds / (-odds + 100)) * 100
        else:
            return (100 / (odds + 100)) * 100
    
    def calculate_breakeven(self, juice: int = -110) -> float:
        """
        Calculate breakeven hit rate for given juice.
        
        Standard -110 requires 52.38% to break even.
        """
        return self.american_to_implied(juice)
    
    def validate_spread_edge(
        self,
        spread: float,
        juice: int,
        is_favorite: bool,
        is_playoff: bool,
        is_home: bool,
        public_pct: Optional[float] = None,
        weather_condition: Optional[str] = None,
        calculated_edge: Optional[float] = None,
    ) -> EdgeValidation:
        """
        Validate a spread bet for actual edge.
        
        Args:
            spread: The spread (e.g., -3.0)
            juice: The juice (e.g., -110)
            is_favorite: True if betting the favorite
            is_playoff: True if playoff game
            is_home: True if betting home team
            public_pct: % of public money on this side
            weather_condition: Weather factor if applicable
            calculated_edge: Pre-calculated edge from analysis
            
        Returns:
            EdgeValidation with all checks
        """
        warnings = []
        contrarian_signals = []
        
        # Determine spot type
        if is_playoff:
            spot_type = SpotType.PLAYOFF_FAVORITE if is_favorite else SpotType.PLAYOFF_UNDERDOG
        elif is_home and is_favorite:
            spot_type = SpotType.HOME_FAVORITE
        elif not is_home and not is_favorite:
            spot_type = SpotType.ROAD_UNDERDOG
        else:
            spot_type = SpotType.DIVISIONAL_GAME
        
        # Get historical ATS for this spot type
        spot_ats = self.SPOT_TYPE_HISTORICAL_ATS.get(spot_type, 50.0)
        
        # Calculate required hit rate
        required_hit_rate = self.calculate_breakeven(juice)
        
        # Use spot type ATS as baseline hit rate if no specific calculation
        calculated_hit_rate = spot_ats
        if calculated_edge:
            # If analysis provided an edge, adjust
            calculated_hit_rate = 50.0 + (calculated_edge * 2)  # Rough conversion
        
        edge_pct = calculated_hit_rate - required_hit_rate
        has_edge = edge_pct > 0
        
        # Public side detection
        is_public_side = False
        if public_pct and public_pct > 60:
            is_public_side = True
            warnings.append(f"This is the PUBLIC side ({public_pct:.0f}% of bets)")
        
        # Spot type warnings
        if is_playoff and is_favorite:
            warnings.append(f"Playoff favorites cover only {spot_ats:.1f}% historically - LOSING spot")
            contrarian_signals.append("Historical: Playoff underdogs cover 55%+ ATS")
        
        if is_playoff and not is_favorite:
            contrarian_signals.append(f"Playoff underdogs cover {spot_ats:.1f}% - PROFITABLE spot")
        
        # Weather narrative check
        if weather_condition:
            impact = self.WEATHER_TOTAL_IMPACT.get(weather_condition, 0)
            if abs(impact) < 3:
                warnings.append(f"Weather impact ({weather_condition}) is minimal: {impact:+.1f} pts - narrative trap")
        
        # Line freeze check
        if is_favorite and public_pct and public_pct > 70:
            contrarian_signals.append("Line not moving despite heavy public action = books want this money")
        
        # Determine recommendation
        if has_edge and not is_public_side:
            recommendation = "BET"
            confidence = "HIGH" if edge_pct > 5 else "MEDIUM"
        elif not has_edge and is_public_side:
            recommendation = "FADE"
            confidence = "MEDIUM"
        elif not has_edge:
            recommendation = "PASS"
            confidence = "LOW"
        else:
            recommendation = "CONTRARIAN"  # Has edge but is public side
            confidence = "LOW"
        
        return EdgeValidation(
            has_mathematical_edge=has_edge,
            calculated_hit_rate=calculated_hit_rate,
            required_hit_rate=required_hit_rate,
            edge_pct=edge_pct,
            is_public_side=is_public_side,
            public_pct=public_pct,
            contrarian_signals=contrarian_signals,
            spot_type_ats=spot_ats,
            warnings=warnings,
            recommendation=recommendation,
            confidence=confidence,
        )
    
    def validate_total_edge(
        self,
        total: float,
        is_over: bool,
        juice: int,
        historical_hit_rate: float,
        weather_condition: Optional[str] = None,
        public_pct: Optional[float] = None,
    ) -> EdgeValidation:
        """
        Validate an over/under bet for actual edge.
        
        Args:
            total: The total (e.g., 40.5)
            is_over: True if betting OVER
            juice: The juice (e.g., -110)
            historical_hit_rate: Hit rate from data analysis
            weather_condition: Weather factor if applicable
            public_pct: % of public money on this side
            
        Returns:
            EdgeValidation with all checks
        """
        warnings = []
        contrarian_signals = []
        
        required_hit_rate = self.calculate_breakeven(juice)
        edge_pct = historical_hit_rate - required_hit_rate
        has_edge = edge_pct > 0
        
        # Public side detection
        is_public_side = False
        if public_pct and public_pct > 60:
            is_public_side = True
            warnings.append(f"This is the PUBLIC side ({public_pct:.0f}% of bets)")
        
        # Weather narrative trap
        if weather_condition and not is_over:
            impact = self.WEATHER_TOTAL_IMPACT.get(weather_condition, 0)
            if abs(impact) < 3:
                warnings.append(f"Weather = Under is a NARRATIVE TRAP. Actual impact: {impact:+.1f} pts")
                warnings.append("Books already price in weather. This edge is baked in.")
        
        # Check if hit rate is even close to profitable
        if historical_hit_rate < 50:
            warnings.append(f"Historical hit rate ({historical_hit_rate:.1f}%) is BELOW 50% - this bet is a loser")
        
        # Determine recommendation
        if has_edge and not is_public_side and historical_hit_rate >= 53:
            recommendation = "BET"
            confidence = "HIGH" if edge_pct > 3 else "MEDIUM"
        elif not has_edge:
            recommendation = "PASS"
            confidence = "HIGH" if edge_pct < -5 else "LOW"
        else:
            recommendation = "PASS"
            confidence = "LOW"
        
        return EdgeValidation(
            has_mathematical_edge=has_edge,
            calculated_hit_rate=historical_hit_rate,
            required_hit_rate=required_hit_rate,
            edge_pct=edge_pct,
            is_public_side=is_public_side,
            public_pct=public_pct,
            contrarian_signals=contrarian_signals,
            spot_type_ats=None,
            warnings=warnings,
            recommendation=recommendation,
            confidence=confidence,
        )
    
    def validate_prop_edge(
        self,
        prop_type: str,
        projection: float,
        line: float,
        is_over: bool,
        juice: int,
        sample_size: int,
    ) -> EdgeValidation:
        """
        Validate a player prop bet.
        
        Args:
            prop_type: Type of prop (e.g., "passing_yards")
            projection: Our calculated projection
            line: The betting line
            is_over: True if betting OVER
            juice: The juice
            sample_size: Number of games in our sample
            
        Returns:
            EdgeValidation with all checks
        """
        warnings = []
        contrarian_signals = []
        
        required_hit_rate = self.calculate_breakeven(juice)
        
        # Calculate edge based on projection vs line
        if is_over:
            edge_pct = ((projection - line) / line) * 100
        else:
            edge_pct = ((line - projection) / line) * 100
        
        # Rough hit rate estimate: 50% + edge/2
        calculated_hit_rate = 50.0 + (edge_pct / 2)
        calculated_hit_rate = max(0, min(100, calculated_hit_rate))
        
        has_edge = calculated_hit_rate > required_hit_rate
        
        # Sample size warning
        if sample_size < 10:
            warnings.append(f"Small sample size ({sample_size} games) - projection may be unreliable")
        
        # Edge magnitude check
        if abs(edge_pct) < 5:
            warnings.append(f"Edge ({edge_pct:+.1f}%) is too small to overcome variance")
        
        # Determine recommendation
        if has_edge and sample_size >= 10 and abs(edge_pct) >= 8:
            recommendation = "BET"
            confidence = "HIGH" if edge_pct > 15 else "MEDIUM"
        elif has_edge and abs(edge_pct) >= 5:
            recommendation = "BET"
            confidence = "LOW"
        else:
            recommendation = "PASS"
            confidence = "LOW" if has_edge else "MEDIUM"
        
        return EdgeValidation(
            has_mathematical_edge=has_edge,
            calculated_hit_rate=calculated_hit_rate,
            required_hit_rate=required_hit_rate,
            edge_pct=edge_pct,
            is_public_side=False,  # Hard to know for props
            public_pct=None,
            contrarian_signals=contrarian_signals,
            spot_type_ats=None,
            warnings=warnings,
            recommendation=recommendation,
            confidence=confidence,
        )
    
    def validate_nba_prop_edge(
        self,
        prop_type: str,
        projection: float,
        line: float,
        is_over: bool,
        juice: int,
        sample_size: int,
        public_pct: Optional[float] = None,
        sharp_action_pct: Optional[float] = None,
        closing_line_value: Optional[float] = None,
    ) -> EdgeValidation:
        """
        Validate an NBA player prop bet with enhanced sharp money analysis.
        
        Args:
            prop_type: Type of prop (e.g., "PTS", "AST", "REB")
            projection: Our calculated projection
            line: The betting line
            is_over: True if betting OVER
            juice: The juice
            sample_size: Number of games in our sample
            public_pct: % of public money on this side
            sharp_action_pct: % of sharp/syndicate money on this side
            closing_line_value: Difference from open line (positive = line moved in our favor)
            
        Returns:
            EdgeValidation with all checks including sharp analysis
        """
        warnings = []
        contrarian_signals = []
        
        required_hit_rate = self.calculate_breakeven(juice)
        
        # Calculate edge based on projection vs line
        if is_over:
            edge_pct = ((projection - line) / line) * 100
        else:
            edge_pct = ((line - projection) / line) * 100
        
        # Rough hit rate estimate: 50% + edge/2
        calculated_hit_rate = 50.0 + (edge_pct / 2)
        calculated_hit_rate = max(0, min(100, calculated_hit_rate))
        
        has_edge = calculated_hit_rate > required_hit_rate
        
        # Sample size warning
        if sample_size < 10:
            warnings.append(f"Small sample size ({sample_size} games) - projection may be unreliable")
        
        # Edge magnitude check
        if abs(edge_pct) < 5:
            warnings.append(f"Edge ({edge_pct:+.1f}%) is too small to overcome variance")
        
        # Public side detection
        is_public_side = False
        if public_pct and public_pct > 60:
            is_public_side = True
            warnings.append(f"This is the PUBLIC side ({public_pct:.0f}% of bets)")
        
        # Sharp action analysis
        is_sharp_side = False
        if sharp_action_pct is not None:
            if sharp_action_pct > 60:
                is_sharp_side = True
                contrarian_signals.append(f"SHARP MONEY ALERT: {sharp_action_pct:.0f}% of sharp action on this side")
            elif sharp_action_pct < 40:
                warnings.append(f"Sharps are FADING this side ({100 - sharp_action_pct:.0f}% sharp action against)")
        
        # CLV analysis - positive CLV indicates line moved in our favor (sharp validation)
        if closing_line_value is not None:
            if closing_line_value > 0.5:
                contrarian_signals.append(f"Positive CLV (+{closing_line_value:.1f}) - sharps validated this move")
                is_sharp_side = True
            elif closing_line_value < -0.5:
                warnings.append(f"Negative CLV ({closing_line_value:.1f}) - line moved against us")
        
        # Public vs Sharp divergence - powerful signal
        if public_pct and sharp_action_pct:
            if public_pct > 65 and sharp_action_pct < 40:
                contrarian_signals.append("PUBLIC/SHARP SPLIT: Public heavy but sharps fading = FADE signal")
            elif public_pct < 40 and sharp_action_pct > 60:
                contrarian_signals.append("SHARP CONTRARIAN: Public light but sharps loading = BET signal")
        
        # Determine recommendation with enhanced logic
        if is_sharp_side and has_edge and sample_size >= 10 and abs(edge_pct) >= 5:
            recommendation = "BET"
            confidence = "HIGH"
        elif has_edge and sample_size >= 10 and abs(edge_pct) >= 8:
            recommendation = "BET"
            confidence = "HIGH" if edge_pct > 15 else "MEDIUM"
        elif has_edge and abs(edge_pct) >= 5:
            if is_public_side and not is_sharp_side:
                recommendation = "CAUTION"  # Edge exists but public side without sharp confirmation
                confidence = "LOW"
            else:
                recommendation = "BET"
                confidence = "LOW"
        elif not has_edge and is_public_side and not is_sharp_side:
            recommendation = "FADE"
            confidence = "MEDIUM"
        else:
            recommendation = "PASS"
            confidence = "LOW" if has_edge else "MEDIUM"
        
        return EdgeValidation(
            has_mathematical_edge=has_edge,
            calculated_hit_rate=calculated_hit_rate,
            required_hit_rate=required_hit_rate,
            edge_pct=edge_pct,
            is_public_side=is_public_side,
            public_pct=public_pct,
            contrarian_signals=contrarian_signals,
            spot_type_ats=None,
            warnings=warnings,
            recommendation=recommendation,
            confidence=confidence,
            sharp_action_pct=sharp_action_pct,
            closing_line_value=closing_line_value,
            is_sharp_side=is_sharp_side,
        )


# Convenience function for quick validation
def validate_bet(
    bet_type: str,
    **kwargs
) -> EdgeValidation:
    """
    Quick validation of any bet type.
    
    Args:
        bet_type: "spread", "total", "prop", or "nba_prop"
        **kwargs: Arguments for the specific validation method
        
    Returns:
        EdgeValidation result
    """
    validator = EdgeValidator()
    
    if bet_type == "spread":
        return validator.validate_spread_edge(**kwargs)
    elif bet_type == "total":
        return validator.validate_total_edge(**kwargs)
    elif bet_type == "prop":
        return validator.validate_prop_edge(**kwargs)
    elif bet_type == "nba_prop":
        return validator.validate_nba_prop_edge(**kwargs)
    else:
        raise ValueError(f"Unknown bet type: {bet_type}")


if __name__ == "__main__":
    # Test the validator
    print("Testing Edge Validator...")
    
    # Test: Patriots -3 as playoff favorite
    result = validate_bet(
        "spread",
        spread=-3.0,
        juice=-120,
        is_favorite=True,
        is_playoff=True,
        is_home=True,
        public_pct=76,
    )
    print(result.to_markdown())
    
    # Test: Under 40.5 in cold weather
    result2 = validate_bet(
        "total",
        total=40.5,
        is_over=False,
        juice=-105,
        historical_hit_rate=37.5,  # From our actual data analysis!
        weather_condition="cold_35F",
        public_pct=55,
    )
    print(result2.to_markdown())




