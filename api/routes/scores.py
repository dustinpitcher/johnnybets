"""
Live Scores API Routes

Fetches live scores from ESPN's public API for the ticker.
"""
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
import httpx
from datetime import datetime, timezone

router = APIRouter(prefix="/scores", tags=["scores"])


class Game(BaseModel):
    """Game data for the ticker."""
    id: str
    sport: str
    homeTeam: str
    awayTeam: str
    homeScore: Optional[int] = None
    awayScore: Optional[int] = None
    status: str  # scheduled, live, final
    startTime: Optional[str] = None
    period: Optional[str] = None
    broadcast: Optional[str] = None


class ScoresResponse(BaseModel):
    """Response with live scores."""
    games: List[Game]
    updated_at: str


# ESPN API endpoints
ESPN_ENDPOINTS = {
    "nfl": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    "nhl": "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard",
    "mlb": "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard",
    "nba": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
}


def parse_espn_status(status_type: dict) -> tuple[str, Optional[str]]:
    """Parse ESPN status into our format."""
    state = status_type.get("state", "").lower()
    detail = status_type.get("detail", "")
    short_detail = status_type.get("shortDetail", "")
    
    if state == "pre":
        return "scheduled", short_detail or detail
    elif state == "in":
        return "live", short_detail or detail
    elif state == "post":
        return "final", None
    else:
        return "scheduled", detail


def parse_espn_game(event: dict, sport: str) -> Game:
    """Parse an ESPN event into our Game format."""
    competition = event.get("competitions", [{}])[0]
    competitors = competition.get("competitors", [])
    
    home_team = None
    away_team = None
    home_score = None
    away_score = None
    
    for comp in competitors:
        team_data = comp.get("team", {})
        abbr = team_data.get("abbreviation", "???")
        score = comp.get("score")
        
        if comp.get("homeAway") == "home":
            home_team = abbr
            home_score = int(score) if score and score.isdigit() else None
        else:
            away_team = abbr
            away_score = int(score) if score and score.isdigit() else None
    
    status_type = event.get("status", {}).get("type", {})
    status, period = parse_espn_status(status_type)
    
    # Get broadcast info
    broadcasts = competition.get("broadcasts", [])
    broadcast = None
    if broadcasts:
        names = broadcasts[0].get("names", [])
        if names:
            broadcast = names[0]
    
    return Game(
        id=event.get("id", ""),
        sport=sport,
        homeTeam=home_team or "???",
        awayTeam=away_team or "???",
        homeScore=home_score,
        awayScore=away_score,
        status=status,
        startTime=period if status == "scheduled" else None,
        period=period if status == "live" else None,
        broadcast=broadcast,
    )


async def fetch_espn_scores(sport: str) -> List[Game]:
    """Fetch scores from ESPN API for a sport."""
    url = ESPN_ENDPOINTS.get(sport)
    if not url:
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            events = data.get("events", [])
            games = [parse_espn_game(event, sport) for event in events]
            return games
    except Exception as e:
        print(f"Error fetching {sport} scores: {e}")
        return []


@router.get("", response_model=ScoresResponse)
async def get_all_scores():
    """
    Get live scores for all supported sports (NFL, NHL, MLB, NBA).
    
    Data is fetched from ESPN's public API.
    """
    all_games = []
    
    # Fetch all sports in parallel
    import asyncio
    results = await asyncio.gather(
        fetch_espn_scores("nfl"),
        fetch_espn_scores("nhl"),
        fetch_espn_scores("mlb"),
        fetch_espn_scores("nba"),
        return_exceptions=True,
    )
    
    for result in results:
        if isinstance(result, list):
            all_games.extend(result)
    
    # Sort: live games first, then scheduled, then final
    status_order = {"live": 0, "scheduled": 1, "final": 2}
    all_games.sort(key=lambda g: status_order.get(g.status, 3))
    
    return ScoresResponse(
        games=all_games,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/{sport}", response_model=ScoresResponse)
async def get_sport_scores(sport: str):
    """
    Get live scores for a specific sport.
    
    Args:
        sport: One of nfl, nhl, mlb, nba
    """
    sport_lower = sport.lower()
    if sport_lower not in ESPN_ENDPOINTS:
        return ScoresResponse(
            games=[],
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
    
    games = await fetch_espn_scores(sport_lower)
    
    return ScoresResponse(
        games=games,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
