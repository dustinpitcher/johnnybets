"""
Entity Extraction for Sports Teams and Players

Extracts mentions of teams and players from user messages
to create session tags with logos and metadata.
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Entity:
    """Represents an extracted entity (team or player)."""
    type: str  # 'team' or 'player'
    name: str
    normalized_name: str
    abbreviation: Optional[str] = None
    sport: Optional[str] = None
    logo_url: Optional[str] = None
    team_id: Optional[str] = None
    player_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "name": self.name,
            "normalized_name": self.normalized_name,
            "abbreviation": self.abbreviation,
            "sport": self.sport,
            "logo_url": self.logo_url,
            "team_id": self.team_id,
            "player_id": self.player_id,
        }


# =============================================================================
# TEAM DATA
# =============================================================================

NFL_TEAMS = {
    # AFC East
    "buffalo bills": {"abbr": "BUF", "city": "Buffalo", "name": "Bills", "id": "buf"},
    "miami dolphins": {"abbr": "MIA", "city": "Miami", "name": "Dolphins", "id": "mia"},
    "new england patriots": {"abbr": "NE", "city": "New England", "name": "Patriots", "id": "ne"},
    "new york jets": {"abbr": "NYJ", "city": "New York", "name": "Jets", "id": "nyj"},
    # AFC North
    "baltimore ravens": {"abbr": "BAL", "city": "Baltimore", "name": "Ravens", "id": "bal"},
    "cincinnati bengals": {"abbr": "CIN", "city": "Cincinnati", "name": "Bengals", "id": "cin"},
    "cleveland browns": {"abbr": "CLE", "city": "Cleveland", "name": "Browns", "id": "cle"},
    "pittsburgh steelers": {"abbr": "PIT", "city": "Pittsburgh", "name": "Steelers", "id": "pit"},
    # AFC South
    "houston texans": {"abbr": "HOU", "city": "Houston", "name": "Texans", "id": "hou"},
    "indianapolis colts": {"abbr": "IND", "city": "Indianapolis", "name": "Colts", "id": "ind"},
    "jacksonville jaguars": {"abbr": "JAX", "city": "Jacksonville", "name": "Jaguars", "id": "jax"},
    "tennessee titans": {"abbr": "TEN", "city": "Tennessee", "name": "Titans", "id": "ten"},
    # AFC West
    "denver broncos": {"abbr": "DEN", "city": "Denver", "name": "Broncos", "id": "den"},
    "kansas city chiefs": {"abbr": "KC", "city": "Kansas City", "name": "Chiefs", "id": "kc"},
    "las vegas raiders": {"abbr": "LV", "city": "Las Vegas", "name": "Raiders", "id": "lv"},
    "los angeles chargers": {"abbr": "LAC", "city": "Los Angeles", "name": "Chargers", "id": "lac"},
    # NFC East
    "dallas cowboys": {"abbr": "DAL", "city": "Dallas", "name": "Cowboys", "id": "dal"},
    "new york giants": {"abbr": "NYG", "city": "New York", "name": "Giants", "id": "nyg"},
    "philadelphia eagles": {"abbr": "PHI", "city": "Philadelphia", "name": "Eagles", "id": "phi"},
    "washington commanders": {"abbr": "WAS", "city": "Washington", "name": "Commanders", "id": "was"},
    # NFC North
    "chicago bears": {"abbr": "CHI", "city": "Chicago", "name": "Bears", "id": "chi"},
    "detroit lions": {"abbr": "DET", "city": "Detroit", "name": "Lions", "id": "det"},
    "green bay packers": {"abbr": "GB", "city": "Green Bay", "name": "Packers", "id": "gb"},
    "minnesota vikings": {"abbr": "MIN", "city": "Minnesota", "name": "Vikings", "id": "min"},
    # NFC South
    "atlanta falcons": {"abbr": "ATL", "city": "Atlanta", "name": "Falcons", "id": "atl"},
    "carolina panthers": {"abbr": "CAR", "city": "Carolina", "name": "Panthers", "id": "car"},
    "new orleans saints": {"abbr": "NO", "city": "New Orleans", "name": "Saints", "id": "no"},
    "tampa bay buccaneers": {"abbr": "TB", "city": "Tampa Bay", "name": "Buccaneers", "id": "tb"},
    # NFC West
    "arizona cardinals": {"abbr": "ARI", "city": "Arizona", "name": "Cardinals", "id": "ari"},
    "los angeles rams": {"abbr": "LAR", "city": "Los Angeles", "name": "Rams", "id": "lar"},
    "san francisco 49ers": {"abbr": "SF", "city": "San Francisco", "name": "49ers", "id": "sf"},
    "seattle seahawks": {"abbr": "SEA", "city": "Seattle", "name": "Seahawks", "id": "sea"},
}

NHL_TEAMS = {
    # Atlantic
    "boston bruins": {"abbr": "BOS", "city": "Boston", "name": "Bruins", "id": "bos"},
    "buffalo sabres": {"abbr": "BUF", "city": "Buffalo", "name": "Sabres", "id": "buf"},
    "detroit red wings": {"abbr": "DET", "city": "Detroit", "name": "Red Wings", "id": "det"},
    "florida panthers": {"abbr": "FLA", "city": "Florida", "name": "Panthers", "id": "fla"},
    "montreal canadiens": {"abbr": "MTL", "city": "Montreal", "name": "Canadiens", "id": "mtl"},
    "ottawa senators": {"abbr": "OTT", "city": "Ottawa", "name": "Senators", "id": "ott"},
    "tampa bay lightning": {"abbr": "TBL", "city": "Tampa Bay", "name": "Lightning", "id": "tbl"},
    "toronto maple leafs": {"abbr": "TOR", "city": "Toronto", "name": "Maple Leafs", "id": "tor"},
    # Metropolitan
    "carolina hurricanes": {"abbr": "CAR", "city": "Carolina", "name": "Hurricanes", "id": "car"},
    "columbus blue jackets": {"abbr": "CBJ", "city": "Columbus", "name": "Blue Jackets", "id": "cbj"},
    "new jersey devils": {"abbr": "NJD", "city": "New Jersey", "name": "Devils", "id": "njd"},
    "new york islanders": {"abbr": "NYI", "city": "New York", "name": "Islanders", "id": "nyi"},
    "new york rangers": {"abbr": "NYR", "city": "New York", "name": "Rangers", "id": "nyr"},
    "philadelphia flyers": {"abbr": "PHI", "city": "Philadelphia", "name": "Flyers", "id": "phi"},
    "pittsburgh penguins": {"abbr": "PIT", "city": "Pittsburgh", "name": "Penguins", "id": "pit"},
    "washington capitals": {"abbr": "WSH", "city": "Washington", "name": "Capitals", "id": "wsh"},
    # Central
    "arizona coyotes": {"abbr": "ARI", "city": "Arizona", "name": "Coyotes", "id": "ari"},
    "chicago blackhawks": {"abbr": "CHI", "city": "Chicago", "name": "Blackhawks", "id": "chi"},
    "colorado avalanche": {"abbr": "COL", "city": "Colorado", "name": "Avalanche", "id": "col"},
    "dallas stars": {"abbr": "DAL", "city": "Dallas", "name": "Stars", "id": "dal"},
    "minnesota wild": {"abbr": "MIN", "city": "Minnesota", "name": "Wild", "id": "min"},
    "nashville predators": {"abbr": "NSH", "city": "Nashville", "name": "Predators", "id": "nsh"},
    "st louis blues": {"abbr": "STL", "city": "St. Louis", "name": "Blues", "id": "stl"},
    "winnipeg jets": {"abbr": "WPG", "city": "Winnipeg", "name": "Jets", "id": "wpg"},
    # Pacific
    "anaheim ducks": {"abbr": "ANA", "city": "Anaheim", "name": "Ducks", "id": "ana"},
    "calgary flames": {"abbr": "CGY", "city": "Calgary", "name": "Flames", "id": "cgy"},
    "edmonton oilers": {"abbr": "EDM", "city": "Edmonton", "name": "Oilers", "id": "edm"},
    "los angeles kings": {"abbr": "LAK", "city": "Los Angeles", "name": "Kings", "id": "lak"},
    "san jose sharks": {"abbr": "SJS", "city": "San Jose", "name": "Sharks", "id": "sjs"},
    "seattle kraken": {"abbr": "SEA", "city": "Seattle", "name": "Kraken", "id": "sea"},
    "vancouver canucks": {"abbr": "VAN", "city": "Vancouver", "name": "Canucks", "id": "van"},
    "vegas golden knights": {"abbr": "VGK", "city": "Vegas", "name": "Golden Knights", "id": "vgk"},
}

# Common player names (expandable)
NOTABLE_PLAYERS = {
    # NFL QBs
    "patrick mahomes": {"sport": "nfl", "team": "KC", "position": "QB"},
    "josh allen": {"sport": "nfl", "team": "BUF", "position": "QB"},
    "lamar jackson": {"sport": "nfl", "team": "BAL", "position": "QB"},
    "jalen hurts": {"sport": "nfl", "team": "PHI", "position": "QB"},
    "joe burrow": {"sport": "nfl", "team": "CIN", "position": "QB"},
    "justin herbert": {"sport": "nfl", "team": "LAC", "position": "QB"},
    "trevor lawrence": {"sport": "nfl", "team": "JAX", "position": "QB"},
    "tua tagovailoa": {"sport": "nfl", "team": "MIA", "position": "QB"},
    "dak prescott": {"sport": "nfl", "team": "DAL", "position": "QB"},
    "kirk cousins": {"sport": "nfl", "team": "ATL", "position": "QB"},
    # NHL Goalies
    "igor shesterkin": {"sport": "nhl", "team": "NYR", "position": "G"},
    "andrei vasilevskiy": {"sport": "nhl", "team": "TBL", "position": "G"},
    "connor hellebuyck": {"sport": "nhl", "team": "WPG", "position": "G"},
    "ilya sorokin": {"sport": "nhl", "team": "NYI", "position": "G"},
    "juuse saros": {"sport": "nhl", "team": "NSH", "position": "G"},
    "jake oettinger": {"sport": "nhl", "team": "DAL", "position": "G"},
}


def get_team_logo_url(team_id: str, sport: str) -> str:
    """Get the logo URL for a team."""
    if sport == "nfl":
        return f"https://a.espncdn.com/i/teamlogos/nfl/500/{team_id}.png"
    elif sport == "nhl":
        return f"https://assets.nhle.com/logos/nhl/svg/{team_id.upper()}_light.svg"
    return ""


def build_team_patterns() -> Dict[str, Dict]:
    """Build regex patterns for team matching."""
    patterns = {}
    
    # NFL teams
    for full_name, data in NFL_TEAMS.items():
        patterns[full_name] = {**data, "sport": "nfl"}
        patterns[data["name"].lower()] = {**data, "sport": "nfl"}
        patterns[data["abbr"].lower()] = {**data, "sport": "nfl"}
        patterns[data["city"].lower()] = {**data, "sport": "nfl"}
    
    # NHL teams
    for full_name, data in NHL_TEAMS.items():
        # Avoid conflicts with NFL teams
        key = f"{full_name}"
        patterns[key] = {**data, "sport": "nhl"}
        patterns[f"{data['name'].lower()} (nhl)"] = {**data, "sport": "nhl"}
    
    return patterns


TEAM_PATTERNS = build_team_patterns()


class EntityExtractor:
    """Extract sports entities from text."""
    
    def __init__(self):
        self.team_patterns = TEAM_PATTERNS
        self.player_patterns = NOTABLE_PLAYERS
    
    def extract(self, text: str) -> List[Entity]:
        """Extract all entities from text."""
        entities = []
        text_lower = text.lower()
        seen = set()
        
        # Extract teams
        for pattern, data in self.team_patterns.items():
            if pattern in text_lower and pattern not in seen:
                seen.add(pattern)
                entity = Entity(
                    type="team",
                    name=f"{data.get('city', '')} {data['name']}".strip(),
                    normalized_name=data['name'].lower(),
                    abbreviation=data['abbr'],
                    sport=data['sport'],
                    team_id=data['id'],
                    logo_url=get_team_logo_url(data['id'], data['sport']),
                )
                entities.append(entity)
        
        # Extract players
        for player_name, data in self.player_patterns.items():
            if player_name in text_lower and player_name not in seen:
                seen.add(player_name)
                entity = Entity(
                    type="player",
                    name=player_name.title(),
                    normalized_name=player_name,
                    abbreviation=data.get('team'),
                    sport=data['sport'],
                )
                entities.append(entity)
        
        return entities
    
    def extract_to_dict(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities and return as list of dicts."""
        return [e.to_dict() for e in self.extract(text)]


# Global extractor instance
_extractor = EntityExtractor()


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """Extract entities from text (convenience function)."""
    return _extractor.extract_to_dict(text)

