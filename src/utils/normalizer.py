"""
Team and Event Normalization Utilities

Provides robust team name normalization for NBA, NHL, and NFL.
Handles abbreviations, full names, city names, and nicknames.
"""
import difflib
from typing import List, Dict, Any, Optional, Tuple


# =============================================================================
# NBA TEAM DATA
# =============================================================================

NBA_TEAMS = {
    "ATL": {"full": "Atlanta Hawks", "city": "Atlanta", "name": "Hawks"},
    "BOS": {"full": "Boston Celtics", "city": "Boston", "name": "Celtics"},
    "BKN": {"full": "Brooklyn Nets", "city": "Brooklyn", "name": "Nets"},
    "CHA": {"full": "Charlotte Hornets", "city": "Charlotte", "name": "Hornets"},
    "CHI": {"full": "Chicago Bulls", "city": "Chicago", "name": "Bulls"},
    "CLE": {"full": "Cleveland Cavaliers", "city": "Cleveland", "name": "Cavaliers"},
    "DAL": {"full": "Dallas Mavericks", "city": "Dallas", "name": "Mavericks"},
    "DEN": {"full": "Denver Nuggets", "city": "Denver", "name": "Nuggets"},
    "DET": {"full": "Detroit Pistons", "city": "Detroit", "name": "Pistons"},
    "GSW": {"full": "Golden State Warriors", "city": "Golden State", "name": "Warriors"},
    "HOU": {"full": "Houston Rockets", "city": "Houston", "name": "Rockets"},
    "IND": {"full": "Indiana Pacers", "city": "Indiana", "name": "Pacers"},
    "LAC": {"full": "LA Clippers", "city": "Los Angeles", "name": "Clippers"},
    "LAL": {"full": "Los Angeles Lakers", "city": "Los Angeles", "name": "Lakers"},
    "MEM": {"full": "Memphis Grizzlies", "city": "Memphis", "name": "Grizzlies"},
    "MIA": {"full": "Miami Heat", "city": "Miami", "name": "Heat"},
    "MIL": {"full": "Milwaukee Bucks", "city": "Milwaukee", "name": "Bucks"},
    "MIN": {"full": "Minnesota Timberwolves", "city": "Minnesota", "name": "Timberwolves"},
    "NOP": {"full": "New Orleans Pelicans", "city": "New Orleans", "name": "Pelicans"},
    "NYK": {"full": "New York Knicks", "city": "New York", "name": "Knicks"},
    "OKC": {"full": "Oklahoma City Thunder", "city": "Oklahoma City", "name": "Thunder"},
    "ORL": {"full": "Orlando Magic", "city": "Orlando", "name": "Magic"},
    "PHI": {"full": "Philadelphia 76ers", "city": "Philadelphia", "name": "76ers"},
    "PHX": {"full": "Phoenix Suns", "city": "Phoenix", "name": "Suns"},
    "POR": {"full": "Portland Trail Blazers", "city": "Portland", "name": "Trail Blazers"},
    "SAC": {"full": "Sacramento Kings", "city": "Sacramento", "name": "Kings"},
    "SAS": {"full": "San Antonio Spurs", "city": "San Antonio", "name": "Spurs"},
    "TOR": {"full": "Toronto Raptors", "city": "Toronto", "name": "Raptors"},
    "UTA": {"full": "Utah Jazz", "city": "Utah", "name": "Jazz"},
    "WAS": {"full": "Washington Wizards", "city": "Washington", "name": "Wizards"},
}

# Build reverse lookup: any variation -> abbreviation
def _build_nba_aliases() -> Dict[str, str]:
    aliases = {}
    for abbrev, info in NBA_TEAMS.items():
        # Abbreviation itself
        aliases[abbrev.lower()] = abbrev
        # Full name
        aliases[info["full"].lower()] = abbrev
        # City
        aliases[info["city"].lower()] = abbrev
        # Nickname
        aliases[info["name"].lower()] = abbrev
    
    # Handle special cases and common variations
    aliases["cavs"] = "CLE"
    aliases["sixers"] = "PHI"
    aliases["blazers"] = "POR"
    aliases["wolves"] = "MIN"
    aliases["t-wolves"] = "MIN"
    aliases["twolves"] = "MIN"
    aliases["pels"] = "NOP"
    aliases["mavs"] = "DAL"
    aliases["clips"] = "LAC"
    aliases["la clippers"] = "LAC"
    aliases["los angeles clippers"] = "LAC"
    aliases["los angeles lakers"] = "LAL"
    aliases["la lakers"] = "LAL"
    aliases["golden state"] = "GSW"
    aliases["gs warriors"] = "GSW"
    aliases["okc thunder"] = "OKC"
    aliases["philly"] = "PHI"
    aliases["nola"] = "NOP"
    
    return aliases

NBA_TEAM_ALIASES = _build_nba_aliases()


# =============================================================================
# NHL TEAM DATA
# =============================================================================

NHL_TEAMS = {
    "ANA": {"full": "Anaheim Ducks", "city": "Anaheim", "name": "Ducks"},
    # Note: Arizona Coyotes moved to Utah in 2024-25 season, now Utah Hockey Club
    "BOS": {"full": "Boston Bruins", "city": "Boston", "name": "Bruins"},
    "BUF": {"full": "Buffalo Sabres", "city": "Buffalo", "name": "Sabres"},
    "CGY": {"full": "Calgary Flames", "city": "Calgary", "name": "Flames"},
    "CAR": {"full": "Carolina Hurricanes", "city": "Carolina", "name": "Hurricanes"},
    "CHI": {"full": "Chicago Blackhawks", "city": "Chicago", "name": "Blackhawks"},
    "COL": {"full": "Colorado Avalanche", "city": "Colorado", "name": "Avalanche"},
    "CBJ": {"full": "Columbus Blue Jackets", "city": "Columbus", "name": "Blue Jackets"},
    "DAL": {"full": "Dallas Stars", "city": "Dallas", "name": "Stars"},
    "DET": {"full": "Detroit Red Wings", "city": "Detroit", "name": "Red Wings"},
    "EDM": {"full": "Edmonton Oilers", "city": "Edmonton", "name": "Oilers"},
    "FLA": {"full": "Florida Panthers", "city": "Florida", "name": "Panthers"},
    "LAK": {"full": "Los Angeles Kings", "city": "Los Angeles", "name": "Kings"},
    "MIN": {"full": "Minnesota Wild", "city": "Minnesota", "name": "Wild"},
    "MTL": {"full": "Montreal Canadiens", "city": "Montreal", "name": "Canadiens"},
    "NSH": {"full": "Nashville Predators", "city": "Nashville", "name": "Predators"},
    "NJD": {"full": "New Jersey Devils", "city": "New Jersey", "name": "Devils"},
    "NYI": {"full": "New York Islanders", "city": "New York", "name": "Islanders"},
    "NYR": {"full": "New York Rangers", "city": "New York", "name": "Rangers"},
    "OTT": {"full": "Ottawa Senators", "city": "Ottawa", "name": "Senators"},
    "PHI": {"full": "Philadelphia Flyers", "city": "Philadelphia", "name": "Flyers"},
    "PIT": {"full": "Pittsburgh Penguins", "city": "Pittsburgh", "name": "Penguins"},
    "SJS": {"full": "San Jose Sharks", "city": "San Jose", "name": "Sharks"},
    "SEA": {"full": "Seattle Kraken", "city": "Seattle", "name": "Kraken"},
    "STL": {"full": "St. Louis Blues", "city": "St. Louis", "name": "Blues"},
    "TBL": {"full": "Tampa Bay Lightning", "city": "Tampa Bay", "name": "Lightning"},
    "TOR": {"full": "Toronto Maple Leafs", "city": "Toronto", "name": "Maple Leafs"},
    "UTA": {"full": "Utah Hockey Club", "city": "Utah", "name": "Mammoth"},  # New team 2024-25
    "VAN": {"full": "Vancouver Canucks", "city": "Vancouver", "name": "Canucks"},
    "VGK": {"full": "Vegas Golden Knights", "city": "Vegas", "name": "Golden Knights"},
    "WSH": {"full": "Washington Capitals", "city": "Washington", "name": "Capitals"},
    "WPG": {"full": "Winnipeg Jets", "city": "Winnipeg", "name": "Jets"},
}

def _build_nhl_aliases() -> Dict[str, str]:
    aliases = {}
    for abbrev, info in NHL_TEAMS.items():
        # Abbreviation itself
        aliases[abbrev.lower()] = abbrev
        # Full name
        aliases[info["full"].lower()] = abbrev
        # City
        aliases[info["city"].lower()] = abbrev
        # Nickname
        aliases[info["name"].lower()] = abbrev
    
    # Handle special cases and common variations
    aliases["canes"] = "CAR"
    aliases["habs"] = "MTL"
    aliases["preds"] = "NSH"
    aliases["pens"] = "PIT"
    aliases["bolts"] = "TBL"
    aliases["leafs"] = "TOR"
    aliases["caps"] = "WSH"
    aliases["knights"] = "VGK"
    aliases["vegas"] = "VGK"
    aliases["las vegas"] = "VGK"
    aliases["la kings"] = "LAK"
    aliases["los angeles kings"] = "LAK"
    aliases["st louis"] = "STL"
    aliases["st. louis"] = "STL"
    aliases["saint louis"] = "STL"
    aliases["jackets"] = "CBJ"
    aliases["blue jackets"] = "CBJ"
    aliases["avs"] = "COL"
    aliases["isles"] = "NYI"
    aliases["nyi"] = "NYI"
    aliases["nyr"] = "NYR"
    aliases["njd"] = "NJD"
    aliases["tb lightning"] = "TBL"
    aliases["tampa"] = "TBL"
    aliases["san jose"] = "SJS"
    aliases["sj sharks"] = "SJS"
    # Utah variations (new team)
    aliases["utah mammoth"] = "UTA"
    aliases["utah hc"] = "UTA"
    aliases["utah hockey club"] = "UTA"
    # Montreal variations
    aliases["montréal"] = "MTL"
    aliases["montréal canadiens"] = "MTL"
    
    # Arizona Coyotes (moved to Utah in 2024-25, map to Utah for current data)
    aliases["ari"] = "UTA"
    aliases["arizona"] = "UTA"
    aliases["arizona coyotes"] = "UTA"
    aliases["coyotes"] = "UTA"
    aliases["phx"] = "UTA"  # Old Phoenix abbreviation
    
    return aliases

NHL_TEAM_ALIASES = _build_nhl_aliases()


# =============================================================================
# NORMALIZATION FUNCTIONS
# =============================================================================

def normalize_nba_team(team: str) -> Optional[str]:
    """
    Convert any NBA team reference to standard 3-letter abbreviation.
    
    Args:
        team: Team name in any format (abbreviation, full name, city, nickname)
        
    Returns:
        Standard abbreviation (e.g., "WAS") or None if not found
        
    Examples:
        normalize_nba_team("WAS") -> "WAS"
        normalize_nba_team("Washington Wizards") -> "WAS"
        normalize_nba_team("wizards") -> "WAS"
        normalize_nba_team("Sixers") -> "PHI"
    """
    if not team:
        return None
    
    team_lower = team.strip().lower()
    
    # Check if already a valid abbreviation
    if team.upper() in NBA_TEAMS:
        return team.upper()
    
    # Look up in aliases
    if team_lower in NBA_TEAM_ALIASES:
        return NBA_TEAM_ALIASES[team_lower]
    
    # Try fuzzy matching as last resort
    for alias, abbrev in NBA_TEAM_ALIASES.items():
        if alias in team_lower or team_lower in alias:
            return abbrev
    
    return None


def normalize_nhl_team(team: str) -> Optional[str]:
    """
    Convert any NHL team reference to standard 3-letter abbreviation.
    
    Args:
        team: Team name in any format (abbreviation, full name, city, nickname)
        
    Returns:
        Standard abbreviation (e.g., "NYR") or None if not found
        
    Examples:
        normalize_nhl_team("NYR") -> "NYR"
        normalize_nhl_team("New York Rangers") -> "NYR"
        normalize_nhl_team("rangers") -> "NYR"
        normalize_nhl_team("Habs") -> "MTL"
    """
    if not team:
        return None
    
    team_lower = team.strip().lower()
    
    # Check if already a valid abbreviation
    if team.upper() in NHL_TEAMS:
        return team.upper()
    
    # Look up in aliases
    if team_lower in NHL_TEAM_ALIASES:
        return NHL_TEAM_ALIASES[team_lower]
    
    # Try fuzzy matching as last resort
    for alias, abbrev in NHL_TEAM_ALIASES.items():
        if alias in team_lower or team_lower in alias:
            return abbrev
    
    return None


def get_nba_team_full_name(abbrev: str) -> Optional[str]:
    """Get full team name from abbreviation."""
    abbrev = abbrev.upper() if abbrev else None
    if abbrev in NBA_TEAMS:
        return NBA_TEAMS[abbrev]["full"]
    return None


def get_nhl_team_full_name(abbrev: str) -> Optional[str]:
    """Get full team name from abbreviation."""
    abbrev = abbrev.upper() if abbrev else None
    if abbrev in NHL_TEAMS:
        return NHL_TEAMS[abbrev]["full"]
    return None


# =============================================================================
# EVENT NORMALIZER CLASS (Legacy)
# =============================================================================

class EventNormalizer:
    def __init__(self):
        pass

    def normalize_team_name(self, name: str) -> str:
        """
        Normalize team names to a standard format.
        Example: "Kansas City Chiefs" -> "Kansas City" or "KC"
        For now, just lowercase and strip.
        """
        return name.lower().strip()

    def match_events(self, kalshi_events: List[Dict], mybookie_events: List[Dict]) -> List[Tuple[Dict, Dict]]:
        """
        Match events from Kalshi and MyBookie based on team names/titles.
        Returns a list of tuples (kalshi_event, mybookie_event).
        """
        matched = []
        
        # Simple O(N*M) matching for now
        for k_event in kalshi_events:
            best_match = None
            highest_ratio = 0.0
            
            k_title = k_event.get('title', '') or k_event.get('ticker', '')
            
            for m_event in mybookie_events:
                # Construct a comparable string from mybookie event
                m_title = f"{m_event.get('away_team')} vs {m_event.get('home_team')}"
                
                ratio = difflib.SequenceMatcher(None, k_title.lower(), m_title.lower()).ratio()
                
                if ratio > 0.6 and ratio > highest_ratio: # Threshold 0.6
                    highest_ratio = ratio
                    best_match = m_event
            
            if best_match:
                matched.append((k_event, best_match))
                
        return matched

if __name__ == "__main__":
    norm = EventNormalizer()
    # Test data
    k = [{'title': 'Chiefs vs 49ers'}]
    m = [{'home_team': 'San Francisco 49ers', 'away_team': 'Kansas City Chiefs'}]
    
    matches = norm.match_events(k, m)
    print(f"Matches: {matches}")

