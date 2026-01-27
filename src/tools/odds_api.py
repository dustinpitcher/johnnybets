"""
The Odds API Integration
https://the-odds-api.com/

Provides real-time odds from 40+ sportsbooks for comparison with prediction markets.
"""
import os
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta


class OddsAPIClient:
    """Client for The Odds API - aggregates odds from multiple sportsbooks."""
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    # Sports keys for major US sports
    SPORTS = {
        "nfl": "americanfootball_nfl",
        "nba": "basketball_nba",
        "mlb": "baseball_mlb",
        "nhl": "icehockey_nhl",
        "ncaaf": "americanfootball_ncaaf",
        "ncaab": "basketball_ncaab",
    }
    
    # Popular US bookmakers
    DEFAULT_BOOKMAKERS = [
        "draftkings",
        "fanduel", 
        "betmgm",
        "caesars",
        "pointsbetus",
        "bovada",
        "betonlineag",
        "mybookieag",  # MyBookie is included!
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ODDS_API_KEY")
        if not self.api_key:
            raise ValueError("ODDS_API_KEY environment variable required. Get one at https://the-odds-api.com/")
        
        self.remaining_requests = None
        self.used_requests = None

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make API request and track quota usage."""
        params = params or {}
        params["apiKey"] = self.api_key
        
        response = requests.get(f"{self.BASE_URL}/{endpoint}", params=params)
        
        # Track API quota from headers
        self.remaining_requests = response.headers.get("x-requests-remaining")
        self.used_requests = response.headers.get("x-requests-used")
        
        if response.status_code == 401:
            raise ValueError("Invalid API key")
        elif response.status_code == 429:
            raise RuntimeError("API quota exceeded")
        elif response.status_code != 200:
            raise RuntimeError(f"API error {response.status_code}: {response.text}")
            
        return response.json()

    def get_sports(self) -> List[Dict[str, Any]]:
        """Get list of available sports."""
        return self._make_request("sports")

    def get_odds(
        self,
        sport: str = "nfl",
        regions: str = "us",
        markets: str = "h2h,spreads,totals",
        bookmakers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get odds for a specific sport.
        
        Args:
            sport: Sport key (nfl, nba, mlb, nhl, ncaaf, ncaab)
            regions: Comma-separated regions (us, us2, uk, eu, au)
            markets: Comma-separated markets (h2h=moneyline, spreads, totals)
            bookmakers: Optional list of specific bookmakers
            
        Returns:
            List of games with odds from multiple bookmakers
        """
        sport_key = self.SPORTS.get(sport.lower(), sport)
        
        params = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": "american",
        }
        
        if bookmakers:
            params["bookmakers"] = ",".join(bookmakers)
        
        return self._make_request(f"sports/{sport_key}/odds", params)

    def filter_future_games(
        self, 
        games: List[Dict[str, Any]], 
        min_minutes_until_start: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Filter out games that have already started or start too soon.
        
        Args:
            games: List of games from get_odds()
            min_minutes_until_start: Minimum minutes until game start (default 15)
            
        Returns:
            List of games that haven't started yet
        """
        now = datetime.now(timezone.utc)
        cutoff = now + timedelta(minutes=min_minutes_until_start)
        
        future_games = []
        for game in games:
            commence_str = game.get("commence_time")
            if not commence_str:
                continue
            
            try:
                # Parse ISO format timestamp
                commence_time = datetime.fromisoformat(commence_str.replace("Z", "+00:00"))
                if commence_time > cutoff:
                    future_games.append(game)
            except (ValueError, TypeError):
                # If we can't parse, include the game to be safe
                future_games.append(game)
        
        return future_games

    def get_nfl_odds(self, include_mybookie: bool = True, only_future: bool = True) -> List[Dict[str, Any]]:
        """
        Convenience method to get NFL odds.
        
        Args:
            include_mybookie: If True, specifically include mybookieag in results
            only_future: If True, filter out games that have already started
            
        Returns:
            List of NFL games with odds
        """
        bookmakers = self.DEFAULT_BOOKMAKERS if include_mybookie else None
        games = self.get_odds(sport="nfl", bookmakers=bookmakers)
        
        if only_future:
            games = self.filter_future_games(games)
        
        return games

    def get_nba_odds(self, only_future: bool = True) -> List[Dict[str, Any]]:
        """Get NBA odds (future games only by default)."""
        games = self.get_odds(sport="nba")
        if only_future:
            games = self.filter_future_games(games)
        return games

    def format_game_summary(self, game: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a game into a cleaner summary structure.
        
        Args:
            game: Raw game data from API
            
        Returns:
            Formatted game summary with key odds info
        """
        summary = {
            "id": game.get("id"),
            "sport": game.get("sport_key"),
            "commence_time": game.get("commence_time"),
            "home_team": game.get("home_team"),
            "away_team": game.get("away_team"),
            "bookmakers": {},
        }
        
        for bookmaker in game.get("bookmakers", []):
            book_key = bookmaker.get("key")
            book_data = {"title": bookmaker.get("title")}
            
            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                outcomes = {}
                
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name")
                    price = outcome.get("price")
                    point = outcome.get("point")
                    
                    if point is not None:
                        outcomes[name] = {"price": price, "point": point}
                    else:
                        outcomes[name] = {"price": price}
                
                book_data[market_key] = outcomes
            
            summary["bookmakers"][book_key] = book_data
        
        return summary

    def find_best_odds(self, games: List[Dict[str, Any]], market: str = "h2h") -> List[Dict[str, Any]]:
        """
        Find the best odds across all bookmakers for each game.
        
        Args:
            games: List of games from get_odds()
            market: Market type (h2h, spreads, totals)
            
        Returns:
            List of games with best odds highlighted
        """
        results = []
        
        for game in games:
            best_odds = {
                "home_team": game.get("home_team"),
                "away_team": game.get("away_team"),
                "commence_time": game.get("commence_time"),
                "best_home": {"price": -99999, "bookmaker": None},
                "best_away": {"price": -99999, "bookmaker": None},
            }
            
            for bookmaker in game.get("bookmakers", []):
                for mkt in bookmaker.get("markets", []):
                    if mkt.get("key") != market:
                        continue
                    
                    for outcome in mkt.get("outcomes", []):
                        price = outcome.get("price", -99999)
                        name = outcome.get("name")
                        
                        if name == game.get("home_team"):
                            if price > best_odds["best_home"]["price"]:
                                best_odds["best_home"] = {
                                    "price": price,
                                    "bookmaker": bookmaker.get("key"),
                                }
                        elif name == game.get("away_team"):
                            if price > best_odds["best_away"]["price"]:
                                best_odds["best_away"] = {
                                    "price": price,
                                    "bookmaker": bookmaker.get("key"),
                                }
            
            results.append(best_odds)
        
        return results

    def get_quota_status(self) -> Dict[str, Any]:
        """Get current API quota status."""
        return {
            "remaining": self.remaining_requests,
            "used": self.used_requests,
        }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("/Users/dustinpitcher/ai_workspace/.env")
    
    try:
        client = OddsAPIClient()
        print("Odds API client initialized")
        
        # Get NFL odds
        print("\nFetching NFL odds...")
        games = client.get_nfl_odds()
        print(f"Found {len(games)} NFL games")
        
        if games:
            # Show first game details
            game = games[0]
            print(f"\nFirst game: {game.get('away_team')} @ {game.get('home_team')}")
            print(f"Commence: {game.get('commence_time')}")
            print(f"Bookmakers: {len(game.get('bookmakers', []))}")
            
            for book in game.get("bookmakers", [])[:3]:
                print(f"\n  {book.get('title')}:")
                for market in book.get("markets", []):
                    print(f"    {market.get('key')}: {market.get('outcomes')}")
        
        # Check quota
        print(f"\nAPI Quota - Remaining: {client.remaining_requests}, Used: {client.used_requests}")
        
    except Exception as e:
        print(f"Error: {e}")

