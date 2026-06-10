"""The Odds API client for fetching betting odds."""

import httpx

from ..config import settings
from ..models.team import Team

ODDS_BASE = "https://api.the-odds-api.com/v4"
RELEVANT_BOOKMAKERS = {"pinnacle", "bet365", "betfair", "williamhill", "unibet"}


class OddsClient:
    def __init__(self):
        self.key = settings.odds_api_key

    async def fetch_h2h_odds(self, team_a: Team, team_b: Team) -> dict | None:
        """Fetch head-to-head odds for a specific match.

        Returns None if no odds found.
        """
        if not self.key:
            return None

        url = f"{ODDS_BASE}/sports/soccer_fifa_world_cup/odds/"
        params = {
            "apiKey": self.key,
            "regions": "uk",
            "markets": "h2h",
            "bookmakers": "pinnacle,bet365,betfair,williamhill,unibet",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            matches = resp.json()

        # Match by team name
        for m in matches:
            if (team_a.name.lower() in m["home_team"].lower()
                    and team_b.name.lower() in m["away_team"].lower()):
                return self._extract_odds(m)
        return None

    def _extract_odds(self, match_data: dict) -> dict:
        bookmakers = []
        for bm in match_data.get("bookmakers", []):
            outcomes = {}
            for o in bm["markets"][0]["outcomes"]:
                outcomes[o["name"]] = o["price"]
            bookmakers.append({
                "name": bm["title"],
                "outcomes": outcomes,
                "last_update": bm.get("last_update"),
            })

        return {
            "home_team": match_data["home_team"],
            "away_team": match_data["away_team"],
            "commence_time": match_data["commence_time"],
            "bookmakers": bookmakers,
        }


odds_client = OddsClient()
