import asyncio
import os
from playwright.async_api import async_playwright, Page, Browser
from typing import List, Dict, Any, Optional

class MyBookieScraper:
    BASE_URL = "https://mybookie.ag/sportsbook"

    def __init__(self, headless: bool = True, username: Optional[str] = None, password: Optional[str] = None):
        self.headless = headless
        self.username = username or os.getenv("MYBOOKIE_AG_USERNAME")
        self.password = password or os.getenv("MYBOOKIE_AG_PASSWORD")

    async def fetch_nfl_odds(self) -> List[Dict[str, Any]]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            
            try:
                # Navigate to NFL betting page
                await page.goto(f"{self.BASE_URL}/nfl/", timeout=60000)
                await page.wait_for_selector(".game-lines", timeout=30000)

                # Extract game data
                games = await page.evaluate("""() => {
                    const data = [];
                    const gameCards = document.querySelectorAll('.game-lines');
                    
                    gameCards.forEach(card => {
                        const teams = [];
                        card.querySelectorAll('.teams .team-name').forEach(el => teams.push(el.innerText.trim()));
                        
                        // Extract spreads, moneyline, total
                        // This structure depends on the specific site layout at the time
                        // Need to be generic or inspect the DOM structure carefully
                        
                        const lines = {};
                        // ... simplified extraction logic ...
                        
                        if (teams.length >= 2) {
                            data.push({
                                home_team: teams[1],
                                away_team: teams[0],
                                raw_lines: lines // Placeholder
                            });
                        }
                    });
                    return data;
                }""")
                
                return games
            except Exception as e:
                print(f"Error scraping MyBookie: {e}")
                return []
            finally:
                await browser.close()

if __name__ == "__main__":
    scraper = MyBookieScraper(headless=True)
    try:
        data = asyncio.run(scraper.fetch_nfl_odds())
        print(f"Fetched {len(data)} games")
    except Exception as e:
        print(f"Run error: {e}")

