"""
Daily Intro API Routes

Endpoints for generating and serving the daily intro message.
"""
import os
from datetime import datetime
from typing import Optional, List
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from api.core.daily_intro_storage import get_storage
from api.core.agent import create_session


router = APIRouter(prefix="/daily-intro", tags=["daily-intro"])


# API key for generation endpoint (only GitHub Actions should call this)
GENERATE_API_KEY = os.getenv("DAILY_INTRO_API_KEY")


class DailyIntroResponse(BaseModel):
    """Response with daily intro content."""
    content: str
    generated_at: str
    games_featured: List[str]
    sports: List[str]
    date: str


class GenerateResponse(BaseModel):
    """Response from generation endpoint."""
    success: bool
    date: str
    games_featured: List[str]
    sports: List[str]


# Static fallback message when no daily intro is available
FALLBACK_CONTENT = """Oh good, another person who wants to beat the books. At least you came to someone who knows what they're doing. I'm **JohnnyBets**.

Look, here's the deal:
- 📊 **Live Odds** from every book that matters
- 🎯 **Prop Alpha** player analysis using actual data, not vibes
- 🏒 **NHL Goalie Alpha** because save props are free money if you're not lazy
- 📈 **Arbitrage Scanner** for people who like math over luck

Ask me something. And please, make it interesting."""


def _get_generation_prompt() -> str:
    """Build the prompt for Johnny to generate the daily intro."""
    eastern = ZoneInfo("America/New_York")
    now_et = datetime.now(eastern)
    date_str = now_et.strftime("%A, %B %d, %Y")
    
    return f"""Generate a brief, engaging intro for JohnnyBets users. Today is {date_str}.

First, use your tools to fetch today's games:
1. Call fetch_sportsbook_odds for each active sport (NFL, NBA, NHL, MLB) to see what games are happening today
2. Analyze the slate to find the 3 most interesting betting opportunities

Then write an intro that:
1. Opens with a hook about today's betting slate
2. Highlights the top 3 games with ONE keen betting insight each (line movement, sharp vs public split, total trends, ref tendencies, or prop angle)
3. Teases your analytical capabilities without listing all tools
4. Invites the user to ask about any game or betting question

Style guidelines:
- Be conversational and confident, not bullet-point heavy
- Keep it punchy (150-200 words max after the analysis)
- Sound like a sharp who actually watches games, not a generic AI
- Use specific numbers and angles when you have them
- End with an invitation to dig deeper

IMPORTANT: Your response will be shown to new users as the opening message in a chat. Make it impressive but inviting."""


def _extract_metadata_from_content(content: str, tool_calls: list) -> tuple[List[str], List[str]]:
    """
    Extract games featured and sports from the agent's response and tool calls.
    
    Returns:
        Tuple of (games_featured, sports)
    """
    games_featured = []
    sports_set = set()
    
    # Extract from tool calls
    for tc in tool_calls:
        tool_name = tc.get("name", "")
        output = tc.get("output", "")
        
        # Detect sport from tool name
        if "nfl" in tool_name.lower():
            sports_set.add("nfl")
        elif "nba" in tool_name.lower():
            sports_set.add("nba")
        elif "nhl" in tool_name.lower():
            sports_set.add("nhl")
        elif "mlb" in tool_name.lower():
            sports_set.add("mlb")
        elif "odds" in tool_name.lower():
            # Check the inputs for sport
            inputs = tc.get("inputs", {})
            sport = inputs.get("sport", "")
            if sport:
                # sport key format: americanfootball_nfl, basketball_nba, etc.
                if "nfl" in sport.lower():
                    sports_set.add("nfl")
                elif "nba" in sport.lower():
                    sports_set.add("nba")
                elif "nhl" in sport.lower():
                    sports_set.add("nhl")
                elif "mlb" in sport.lower():
                    sports_set.add("mlb")
        
        # Try to extract team matchups from output
        if output and isinstance(output, str):
            try:
                import json
                data = json.loads(output)
                if isinstance(data, dict) and "games" in data:
                    for game in data.get("games", [])[:3]:  # Top 3 games
                        home = game.get("home_team", "")
                        away = game.get("away_team", "")
                        if home and away:
                            games_featured.append(f"{away} @ {home}")
            except Exception:
                pass
    
    # Limit to top 5 games
    games_featured = games_featured[:5]
    
    return games_featured, list(sports_set)


@router.get("", response_model=DailyIntroResponse)
async def get_daily_intro():
    """
    Get the current daily intro message.
    
    Returns the dynamically generated intro for today, or a fallback if not available.
    """
    storage = get_storage()
    data = await storage.get_current()
    
    if data is None:
        # Return fallback
        eastern = ZoneInfo("America/New_York")
        now_et = datetime.now(eastern)
        
        return DailyIntroResponse(
            content=FALLBACK_CONTENT,
            generated_at=now_et.isoformat(),
            games_featured=[],
            sports=[],
            date=now_et.strftime("%Y-%m-%d"),
        )
    
    return DailyIntroResponse(
        content=data["content"],
        generated_at=data["generated_at"],
        games_featured=data.get("games_featured", []),
        sports=data.get("sports", []),
        date=data["date"],
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate_daily_intro(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    """
    Generate and store the daily intro.
    
    This endpoint is protected by an API key and should only be called
    by the scheduled GitHub Actions workflow.
    """
    # Verify API key
    if GENERATE_API_KEY:
        if not x_api_key or x_api_key != GENERATE_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    # Create a fresh session for generation
    session = create_session(reasoning="high")
    
    # Generate the intro using Johnny
    prompt = _get_generation_prompt()
    
    try:
        response = await session.chat(prompt)
    except Exception as e:
        print(f"[DailyIntro] Generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
    
    # Extract metadata from the response
    games_featured, sports = _extract_metadata_from_content(
        response, 
        session.last_tool_calls
    )
    
    # Store the intro
    storage = get_storage()
    success = await storage.save(
        content=response,
        games_featured=games_featured,
        sports=sports,
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save intro")
    
    eastern = ZoneInfo("America/New_York")
    now_et = datetime.now(eastern)
    
    return GenerateResponse(
        success=True,
        date=now_et.strftime("%Y-%m-%d"),
        games_featured=games_featured,
        sports=sports,
    )
