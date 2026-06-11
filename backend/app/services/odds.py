"""The Odds API client with batch fetch + DB cache strategy.

Strategy:
  - Scheduled task: 1 API call → fetch ALL world cup matches → bulk save to DB
  - On-demand (predict): check DB cache first → only call API if cache miss/expired
  - This reduces API usage from ~132 requests/cycle to just 1.
"""

import httpx
from datetime import datetime, timedelta

from ..config import settings
from ..models.team import Team
from ..models.odds_data import Bookmaker, MatchOdds, MatchOddsSummary
from ..database import SessionLocal

ODDS_BASE = "https://api.the-odds-api.com/v4"

DEFAULT_BOOKMAKERS = {
    "pinnacle": {"name": "Pinnacle", "country": "US"},
    "bet365": {"name": "Bet365", "country": "UK"},
    "betfair": {"name": "Betfair", "country": "UK"},
    "williamhill": {"name": "William Hill", "country": "UK"},
    "unibet": {"name": "Unibet", "country": "SE"},
    "ladbrokes": {"name": "Ladbrokes", "country": "UK"},
    "betway": {"name": "Betway", "country": "ZA"},
    "bwin": {"name": "Bwin", "country": "DE"},
}

# Cache TTL for odds data
ODDS_CACHE_TTL_HOURS = 6


class OddsClient:
    def __init__(self):
        self.key = settings.odds_api_key
        self.session = httpx.AsyncClient(timeout=15.0)

    # ── Public: on-demand with cache-first ──────────────────

    async def fetch_h2h_odds(self, team_a: Team, team_b: Team) -> dict | None:
        """Get odds for a pair of teams. Checks DB cache first."""
        # 1) Try database cache
        cached = self._query_db_cache(team_a.code, team_b.code)
        if cached:
            return cached

        # 2) Cache miss → call API for this specific pair
        if not self.key:
            return None
        result = await self._call_api_for_pair(team_a, team_b)
        if result:
            self._save_to_database(team_a, team_b, result)
        return result

    # ── Public: batch fetch (scheduled task) ────────────────

    async def fetch_all_and_cache(self) -> dict:
        """Single API call to fetch ALL world cup odds, save everything to DB.

        Returns stats dict for logging.
        """
        if not self.key:
            return {"status": "skipped", "reason": "no_api_key"}

        db = SessionLocal()
        try:
            # Single API call
            params = {
                "apiKey": self.key,
                "regions": "uk,us,eu",
                "markets": "h2h",
                "bookmakers": ",".join(DEFAULT_BOOKMAKERS.keys()),
            }
            resp = await self.session.get(f"{ODDS_BASE}/sports/soccer_fifa_world_cup/odds/", params=params)
            resp.raise_for_status()
            matches = resp.json()

            teams = {t.code: t for t in db.query(Team).all()}
            saved_count = 0
            matched_pairs = set()

            for m in matches:
                home_name = m.get("home_team", "")
                away_name = m.get("away_team", "")

                # Match to our teams by name fuzzy match
                team_a_code, team_b_code = self._match_teams(home_name, away_name, teams)
                if not team_a_code:
                    continue

                pair_key = frozenset([team_a_code, team_b_code])
                if pair_key in matched_pairs:
                    continue
                matched_pairs.add(pair_key)

                team_a = teams[team_a_code]
                team_b = teams[team_b_code]

                result = self._extract_odds(m)
                if result:
                    self._save_to_db(db, team_a, team_b, result)
                    saved_count += 1

            db.commit()
            return {
                "status": "ok",
                "api_matches_returned": len(matches),
                "pairs_saved": saved_count,
                "api_requests_used": 1,
            }

        except Exception as e:
            return {"status": "error", "reason": str(e)}
        finally:
            db.close()

    # ── Private: DB cache layer ────────────────────────────

    def _query_db_cache(self, code_a: str, code_b: str) -> dict | None:
        """Check if we have fresh enough odds in DB for this pair."""
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=ODDS_CACHE_TTL_HOURS)

            summary = db.query(MatchOddsSummary).filter(
                MatchOddsSummary.team_a_code == code_a,
                MatchOddsSummary.team_b_code == code_b,
                MatchOddsSummary.updated_at >= cutoff,
            ).first()

            if not summary:
                # Try reversed order
                summary = db.query(MatchOddsSummary).filter(
                    MatchOddsSummary.team_a_code == code_b,
                    MatchOddsSummary.team_b_code == code_a,
                    MatchOddsSummary.updated_at >= cutoff,
                ).first()

            if not summary or not summary.provider_count:
                return None

            # Reconstruct from summary + latest bookmaker details
            odds_list = db.query(MatchOdds).filter(
                ((MatchOdds.team_a_code == code_a) & (MatchOdds.team_b_code == code_b)) |
                ((MatchOdds.team_a_code == code_b) & (MatchOdds.team_b_code == code_a)),
            ).all()

            if not odds_list:
                return None

            bookmakers = []
            for o in odds_list:
                bm = db.query(Bookmaker).filter(Bookmaker.id == o.bookmaker_id).first()
                if not bm:
                    continue
                outcomes = {}
                if o.odds_win is not None:
                    outcomes["home"] = o.odds_win
                if o.odds_draw is not None:
                    outcomes["draw"] = o.odds_draw
                if o.odds_lose is not None:
                    outcomes["away"] = o.odds_lose
                bookmakers.append({
                    "name": bm.name,
                    "slug": bm.slug,
                    "outcomes": outcomes,
                })

            if not bookmakers:
                return None

            return {
                "bookmakers": bookmakers,
                "provider_count": summary.provider_count,
                "market_avg": {
                    "win": summary.avg_odds_win,
                    "draw": summary.avg_odds_draw,
                    "lose": summary.avg_odds_lose,
                },
                "best_odds": {
                    "win": summary.best_odds_win,
                    "draw": summary.best_odds_draw,
                    "lose": summary.best_odds_lose,
                    "provider": summary.best_win_provider,
                },
            }
        finally:
            db.close()

    # ── Private: API call helpers ───────────────────────────

    async def _call_api_for_pair(self, team_a: Team, team_b: Team) -> dict | None:
        """Call The Odds API and find matching match for this pair."""
        params = {
            "apiKey": self.key,
            "regions": "uk,us,eu",
            "markets": "h2h",
            "bookmakers": ",".join(DEFAULT_BOOKMAKERS.keys()),
        }
        try:
            resp = await self.session.get(f"{ODDS_BASE}/sports/soccer_fifa_world_cup/odds/", params=params)
            resp.raise_for_status()
            matches = resp.json()
        except Exception:
            return None

        for m in matches:
            home_lower = m["home_team"].lower()
            away_lower = m["away_team"].lower()
            ta = team_a.name.lower()
            tb = team_b.name.lower()

            if (ta in home_lower and tb in away_lower) or \
               (tb in home_lower and ta in away_lower):
                return self._extract_odds(m)
        return None

    @staticmethod
    def _match_teams(home_name: str, away_name: str, teams: dict[str, Team]) -> tuple[str | None, str | None]:
        """Fuzzy-match API team names to our Team codes."""
        home_low = home_name.lower()
        away_low = away_name.lower()
        for code, t in teams.items():
            name_low = t.name.lower()
            if name_low in home_low:
                code_a = code
                for code2, t2 in teams.items():
                    if code2 == code_a:
                        continue
                    if t2.name.lower() in away_low:
                        return code_a, code2
        return None, None

    # ── Private: extract & persist ───────────────────────────

    def _extract_odds(self, match_data: dict) -> dict | None:
        bookmakers = []
        for bm in match_data.get("bookmakers", []):
            if bm["key"] not in DEFAULT_BOOKMAKERS:
                continue
            outcomes = {}
            for o in bm["markets"][0]["outcomes"]:
                outcomes[o["name"]] = o["price"]
            bookmakers.append({
                "name": bm["title"],
                "slug": bm["key"],
                "outcomes": outcomes,
                "last_update": bm.get("last_update"),
            })
        if not bookmakers:
            return None
        return {
            "home_team": match_data["home_team"],
            "away_team": match_data["away_team"],
            "commence_time": match_data["commence_time"],
            "bookmakers": bookmakers,
        }

    def _save_to_database(self, team_a: Team, team_b: Team, odds_data: dict):
        """Save odds to DB (used by on-demand path)."""
        db = SessionLocal()
        try:
            self._save_to_db(db, team_a, team_b, odds_data)
            db.commit()
        finally:
            db.close()

    def _save_to_db(self, db, team_a: Team, team_b: Team, odds_data: dict):
        """Core save logic shared by both paths."""
        for bm in odds_data["bookmakers"]:
            bookmaker = db.query(Bookmaker).filter(Bookmaker.slug == bm["slug"]).first()
            if not bookmaker:
                bm_info = DEFAULT_BOOKMAKERS.get(bm["slug"], {})
                bookmaker = Bookmaker(
                    name=bm["name"],
                    slug=bm["slug"],
                    country=bm_info.get("country", "UK"),
                )
                db.add(bookmaker)
                db.commit()
                db.refresh(bookmaker)

            home_team_name = odds_data["home_team"]
            team_a_is_home = team_a.name.lower() in home_team_name.lower()

            outcomes = bm["outcomes"]
            odds_win = outcomes.get(home_team_name)
            odds_lose = None
            odds_draw = None
            for name, price in outcomes.items():
                if "draw" in name.lower():
                    odds_draw = price
                elif name.lower() != home_team_name.lower():
                    odds_lose = price

            if team_a_is_home:
                team_a_odds, team_b_odds = odds_win, odds_lose
            else:
                team_a_odds, team_b_odds = odds_lose, odds_win

            existing = db.query(MatchOdds).filter(
                MatchOdds.team_a_code == team_a.code,
                MatchOdds.team_b_code == team_b.code,
                MatchOdds.bookmaker_id == bookmaker.id,
            ).first()

            now = datetime.utcnow()
            expires_at = now + timedelta(hours=ODDS_CACHE_TTL_HOURS)

            if existing:
                existing.odds_win = team_a_odds
                existing.odds_draw = odds_draw
                existing.odds_lose = team_b_odds
                existing.updated_at = now
                existing.expires_at = expires_at
            else:
                db.add(MatchOdds(
                    team_a_code=team_a.code,
                    team_b_code=team_b.code,
                    bookmaker_id=bookmaker.id,
                    odds_win=team_a_odds,
                    odds_draw=odds_draw,
                    odds_lose=team_b_odds,
                    expires_at=expires_at,
                ))

        self._update_summary(db, team_a.code, team_b.code)

    def _update_summary(self, db, team_a_code: str, team_b_code: str):
        odds_list = db.query(MatchOdds).filter(
            MatchOdds.team_a_code == team_a_code,
            MatchOdds.team_b_code == team_b_code,
        ).all()
        if not odds_list:
            return

        win_prices = [o.odds_win for o in odds_list if o.odds_win is not None]
        draw_prices = [o.odds_draw for o in odds_list if o.odds_draw is not None]
        lose_prices = [o.odds_lose for o in odds_list if o.odds_lose is not None]

        summary = db.query(MatchOddsSummary).filter(
            MatchOddsSummary.team_a_code == team_a_code,
            MatchOddsSummary.team_b_code == team_b_code,
        ).first()

        now = datetime.utcnow()
        row = {
            "avg_odds_win": round(sum(win_prices) / len(win_prices), 2) if win_prices else None,
            "avg_odds_draw": round(sum(draw_prices) / len(draw_prices), 2) if draw_prices else None,
            "avg_odds_lose": round(sum(lose_prices) / len(lose_prices), 2) if lose_prices else None,
            "best_odds_win": max(win_prices) if win_prices else None,
            "best_odds_draw": max(draw_prices) if draw_prices else None,
            "best_odds_lose": max(lose_prices) if lose_prices else None,
            "provider_count": len(odds_list),
            "updated_at": now,
        }

        if summary:
            for k, v in row.items():
                setattr(summary, k, v)
        else:
            db.add(MatchOddsSummary(
                team_a_code=team_a_code,
                team_b_code=team_b_code,
                **row,
            ))

    async def close(self):
        await self.session.aclose()


odds_client = OddsClient()
