import os
import kalshi_python
from typing import Dict, Any, List, Optional

class KalshiClient:
    def __init__(self, key_id: Optional[str] = None, private_key_path: Optional[str] = None):
        self.key_id = key_id or os.getenv("KALSHI_API_KEY")
        self.private_key_path = private_key_path or os.getenv("KALSHI_PRIVATE_KEY_FILE")
        
        # Initialize SDK Client
        config = kalshi_python.Configuration()
        config.host = "https://api.elections.kalshi.com/trade-api/v2"
        
        self.api_client = kalshi_python.KalshiClient(config)
        
        # Initialize APIs
        self.events_api = kalshi_python.EventsApi(self.api_client)
        self.markets_api = kalshi_python.MarketsApi(self.api_client)
        
        self.authenticated = False

    def authenticate(self):
        """Authenticate using RSA keys"""
        if not self.key_id or not self.private_key_path:
            # Check if file exists if path is provided
            if self.private_key_path and not os.path.exists(self.private_key_path):
                 raise ValueError(f"Private key file not found: {self.private_key_path}")
            
            raise ValueError("KALSHI_API_KEY and KALSHI_PRIVATE_KEY_FILE required")
            
        try:
            self.api_client.set_kalshi_auth(
                key_id=self.key_id,
                private_key_path=self.private_key_path
            )
            self.authenticated = True
        except Exception as e:
            raise RuntimeError(f"Failed to authenticate with Kalshi: {e}")

    def get_events(self, series_ticker: str = "NFL", limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch events for a specific series (e.g., NFL)"""
        if not self.authenticated:
            self.authenticate()
            
        try:
            response = self.events_api.get_events(
                series_ticker=series_ticker,
                limit=limit,
                status="open"
            )
            if hasattr(response, 'events'):
                return [e.to_dict() for e in response.events]
            return response.to_dict().get('events', [])
        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def get_nfl_markets(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Fetch NFL single game markets directly"""
        if not self.authenticated:
            self.authenticate()
            
        try:
            response = self.markets_api.get_markets(limit=limit, status="open")
            nfl_markets = []
            
            # Filter for NFL game markets
            for m in response.markets:
                ticker = (m.ticker or "").upper()
                title = (m.title or "").lower()
                
                # NFL markets use KXMVENFLSINGLEGAME prefix
                if "NFLSINGLEGAME" in ticker or "nfl" in title:
                    nfl_markets.append(m.to_dict())
                    
            return nfl_markets
        except Exception as e:
            print(f"Error fetching NFL markets: {e}")
            return []

    def get_sports_markets(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Fetch all sports-related markets"""
        if not self.authenticated:
            self.authenticate()
            
        try:
            response = self.markets_api.get_markets(limit=limit, status="open")
            sports_keywords = [
                'nfl', 'nba', 'mlb', 'nhl', 'ncaa', 'super bowl', 'football', 
                'basketball', 'baseball', 'hockey', 'playoff', 'championship'
            ]
            sports_markets = []
            
            for m in response.markets:
                ticker = (m.ticker or "").lower()
                title = (m.title or "").lower()
                
                if any(kw in ticker or kw in title for kw in sports_keywords):
                    sports_markets.append(m.to_dict())
                    
            return sports_markets
        except Exception as e:
            print(f"Error fetching sports markets: {e}")
            return []

    def get_markets(self, event_ticker: str) -> List[Dict[str, Any]]:
        """Fetch markets for a specific event"""
        if not self.authenticated:
            self.authenticate()
            
        try:
            response = self.markets_api.get_markets(event_ticker=event_ticker)
            if hasattr(response, 'markets'):
                return [m.to_dict() for m in response.markets]
            return response.to_dict().get('markets', [])
        except Exception as e:
            print(f"Error fetching markets: {e}")
            return []

    def get_orderbook(self, market_ticker: str) -> Dict[str, Any]:
        """Get orderbook for a specific market"""
        if not self.authenticated:
            self.authenticate()
            
        try:
            response = self.markets_api.get_market_orderbook(market_ticker)
            if hasattr(response, 'orderbook'):
                return response.orderbook.to_dict()
            return response.to_dict().get('orderbook', {})
        except Exception as e:
            print(f"Error fetching orderbook: {e}")
            return {}

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        client = KalshiClient()
        print("Kalshi client initialized")
        # client.authenticate()
        # events = client.get_events()
        # print(f"Events found: {len(events)}")
    except Exception as e:
        print(f"Error: {e}")
