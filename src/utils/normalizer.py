import difflib
from typing import List, Dict, Any, Optional, Tuple

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

