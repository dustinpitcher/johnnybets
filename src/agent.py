import os
import json
import asyncio
from datetime import datetime
from typing import TypedDict, Annotated, List, Dict, Any


def json_serializer(obj):
    """Custom JSON serializer for objects not serializable by default"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from projects.active.sports_betting.src.tools.kalshi import KalshiClient
from projects.active.sports_betting.src.tools.odds_api import OddsAPIClient
from projects.active.sports_betting.src.utils.normalizer import EventNormalizer

# Define State
class AgentState(TypedDict):
    messages: List[BaseMessage]
    kalshi_data: List[Dict[str, Any]]  # Prediction market data (Kalshi)
    sportsbook_data: List[Dict[str, Any]]  # Traditional sportsbook odds (The Odds API)
    matched_events: List[Any]
    arbs: List[Dict[str, Any]]
    strategy_analysis: str

# Node Functions

async def market_fetcher(state: AgentState):
    """Fetch data from both sources: Kalshi (prediction markets) and The Odds API (sportsbooks)"""
    print("--- Fetching Markets ---")
    
    # Initialize tools
    kalshi = KalshiClient()
    
    # Fetch NFL markets from Kalshi (prediction markets)
    kalshi_events = []
    try:
        kalshi_events = kalshi.get_nfl_markets(limit=100)
        print(f"✓ Kalshi: {len(kalshi_events)} NFL prediction markets")
    except Exception as e:
        print(f"✗ Kalshi fetch failed: {e}")

    # Fetch NFL odds from The Odds API (traditional sportsbooks)
    sportsbook_data = []
    try:
        odds_client = OddsAPIClient()
        sportsbook_data = odds_client.get_nfl_odds(include_mybookie=True)
        print(f"✓ Sportsbooks: {len(sportsbook_data)} NFL games from {len(sportsbook_data[0].get('bookmakers', [])) if sportsbook_data else 0} bookmakers")
        print(f"  API quota remaining: {odds_client.remaining_requests}")
    except ValueError as e:
        print(f"✗ Odds API not configured: {e}")
        print("  Get a free API key at https://the-odds-api.com/")
    except Exception as e:
        print(f"✗ Odds API fetch failed: {e}")
        
    return {
        "kalshi_data": kalshi_events,
        "sportsbook_data": sportsbook_data
    }

def arb_scanner(state: AgentState):
    """Scan for arbitrage opportunities between prediction markets and sportsbooks"""
    print("--- Scanning for Arbs ---")
    normalizer = EventNormalizer()
    matches = normalizer.match_events(state["kalshi_data"], state["sportsbook_data"])
    
    arbs = []
    
    # Find best odds across sportsbooks for potential arb calculation
    if state["sportsbook_data"]:
        for game in state["sportsbook_data"]:
            home = game.get("home_team")
            away = game.get("away_team")
            
            # Track best moneyline odds for each side
            best_home = {"price": -99999, "book": None}
            best_away = {"price": -99999, "book": None}
            
            for book in game.get("bookmakers", []):
                for market in book.get("markets", []):
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            price = outcome.get("price", -99999)
                            if outcome.get("name") == home and price > best_home["price"]:
                                best_home = {"price": price, "book": book.get("key")}
                            elif outcome.get("name") == away and price > best_away["price"]:
                                best_away = {"price": price, "book": book.get("key")}
            
            # Check for arb opportunity (implied prob < 100%)
            if best_home["price"] > 0 and best_away["price"] > 0:
                # Both positive odds
                implied_home = 100 / (best_home["price"] + 100)
                implied_away = 100 / (best_away["price"] + 100)
            elif best_home["price"] < 0 and best_away["price"] < 0:
                # Both negative (rare for h2h)
                implied_home = abs(best_home["price"]) / (abs(best_home["price"]) + 100)
                implied_away = abs(best_away["price"]) / (abs(best_away["price"]) + 100)
            else:
                # Mixed - calculate each
                if best_home["price"] > 0:
                    implied_home = 100 / (best_home["price"] + 100)
                else:
                    implied_home = abs(best_home["price"]) / (abs(best_home["price"]) + 100)
                    
                if best_away["price"] > 0:
                    implied_away = 100 / (best_away["price"] + 100)
                else:
                    implied_away = abs(best_away["price"]) / (abs(best_away["price"]) + 100)
            
            total_implied = implied_home + implied_away
            
            if total_implied < 1.0:
                arbs.append({
                    "game": f"{away} @ {home}",
                    "home_odds": best_home,
                    "away_odds": best_away,
                    "total_implied_prob": round(total_implied * 100, 2),
                    "arb_margin": round((1 - total_implied) * 100, 2),
                })
    
    if arbs:
        print(f"  Found {len(arbs)} potential arb opportunities!")
    
    return {"matched_events": matches, "arbs": arbs}

async def strategist(state: AgentState):
    """LLM analysis of market conditions"""
    print("--- Running Strategist ---")
    
    llm = ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="google/gemini-3-pro-preview:online",
    )
    
    # Summarize data for LLM (avoid overwhelming context)
    kalshi_summary = state['kalshi_data'][:10] if state['kalshi_data'] else []
    
    # Summarize sportsbook data - extract key info only
    sportsbook_summary = []
    for game in (state['sportsbook_data'] or [])[:5]:
        game_info = {
            "matchup": f"{game.get('away_team')} @ {game.get('home_team')}",
            "time": game.get("commence_time"),
            "odds_by_book": {}
        }
        for book in game.get("bookmakers", [])[:5]:
            book_odds = {}
            for market in book.get("markets", []):
                book_odds[market.get("key")] = market.get("outcomes")
            game_info["odds_by_book"][book.get("key")] = book_odds
        sportsbook_summary.append(game_info)
    
    # Construct prompt with data context
    prompt = f"""Analyze the following sports betting market data for strategic opportunities.

## Your Task:
1. Compare Kalshi prediction market prices with sportsbook odds
2. Identify Line Freezes (where books are taking a stand)
3. Apply Key Number Math (3, 7, 10, 14 for NFL spreads)
4. Look for Situational Correlations between the prediction markets and traditional lines

## Kalshi Prediction Markets ({len(state['kalshi_data'])} markets):
These are parlay/prop combinations from Kalshi's prediction market:
{json.dumps(kalshi_summary, indent=2, default=json_serializer)}

## Sportsbook Odds ({len(state['sportsbook_data'])} games from multiple books):
Traditional moneyline, spread, and totals from DraftKings, FanDuel, BetMGM, MyBookie, etc:
{json.dumps(sportsbook_summary, indent=2, default=json_serializer)}

## Arb Scanner Results:
- Arbs found: {len(state['arbs'])}
- Details: {json.dumps(state['arbs'], indent=2) if state['arbs'] else 'None detected'}

## Analysis Request:
1. Where do Kalshi prices disagree with traditional sportsbooks?
2. Which sportsbook lines look frozen or unusual?
3. Are there value opportunities combining Kalshi props with sportsbook bets?
4. What's your recommended action based on this data?"""
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return {"strategy_analysis": response.content}

def reporter(state: AgentState):
    """Format the output"""
    print("--- Generating Report ---")
    return {"messages": [AIMessage(content=f"Analysis Complete.\n\n{state['strategy_analysis']}")]}

# Build Graph
workflow = StateGraph(AgentState)

workflow.add_node("market_fetcher", market_fetcher)
workflow.add_node("arb_scanner", arb_scanner)
workflow.add_node("strategist", strategist)
workflow.add_node("reporter", reporter)

workflow.set_entry_point("market_fetcher")
workflow.add_edge("market_fetcher", "arb_scanner")
workflow.add_edge("arb_scanner", "strategist")
workflow.add_edge("strategist", "reporter")
workflow.add_edge("reporter", END)

app = workflow.compile()

async def run_agent():
    inputs = {
        "messages": [HumanMessage(content="Start run")],
        "kalshi_data": [],
        "sportsbook_data": [],
        "matched_events": [],
        "arbs": [],
        "strategy_analysis": ""
    }
    async for output in app.astream(inputs):
        for key, value in output.items():
            print(f"Finished node: {key}")
            if key == "reporter" and "messages" in value:
                print("\n" + "="*50)
                print(value["messages"][-1].content)
                print("="*50 + "\n")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(run_agent())

