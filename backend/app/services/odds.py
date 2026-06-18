"""BetExplorer odds client with DB cache strategy."""

import re
from html.parser import HTMLParser
from datetime import datetime, timedelta

import httpx

from ..models.team import Team
from ..models.odds_data import Bookmaker, MatchOdds, MatchOddsHistory, MatchOddsSummary
from ..database import SessionLocal


ODDS_CACHE_TTL_HOURS = 6
BETEXPLORER_BOOKMAKER = {
    "slug": "betexplorer",
    "name": "BetExplorer",
    "country": "INT",
}


class _BetExplorerTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_row = False
        self.in_cell = False
        self.current_cell = []
        self.current_row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.in_row = True
            self.current_row = []
        elif self.in_row and tag in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []
            if attrs.get("data-odd"):
                self.current_cell.append(attrs["data-odd"])
        elif self.in_cell and attrs.get("data-odd"):
            self.current_cell.append(attrs["data-odd"])

    def handle_endtag(self, tag):
        if self.in_row and tag in {"td", "th"}:
            text = re.sub(r"\s+", " ", "".join(self.current_cell)).strip()
            self.current_row.append(text)
            self.current_cell = []
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            self.rows.append(self.current_row)
            self.current_row = []
            self.in_row = False

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)


class OddsClient:
    BETEXPLORER_FIXTURES_URL = "https://www.betexplorer.com/football/world/world-championship-2026/fixtures/"
    BETEXPLORER_RESULTS_URL = "https://www.betexplorer.com/football/world/world-championship-2026/results/"

    def __init__(self):
        self.session = httpx.AsyncClient(
            timeout=20.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

    async def fetch_h2h_odds(self, team_a: Team, team_b: Team) -> dict | None:
        cached = self._query_db_cache(team_a.code, team_b.code)
        if cached:
            return cached

        await self.fetch_all_and_cache()
        return self._query_db_cache(team_a.code, team_b.code)

    async def fetch_all_and_cache(self) -> dict:
        try:
            texts = [
                await self._fetch_betexplorer_text(self.BETEXPLORER_FIXTURES_URL),
                await self._fetch_betexplorer_text(self.BETEXPLORER_RESULTS_URL),
            ]
            matches = self._dedupe_matches([
                match
                for text in texts
                for match in self._parse_betexplorer_matches(text)
            ])
            saved_count = self._save_betexplorer_matches(matches)
            return {
                "status": "ok",
                "source": "betexplorer",
                "matches_returned": len(matches),
                "pairs_saved": saved_count,
                "api_requests_used": 0,
            }
        except Exception as e:
            return {"status": "error", "source": "betexplorer", "reason": str(e), "api_requests_used": 0}

    async def _fetch_betexplorer_text(self, url: str) -> str:
        resp = await self.session.get(url)
        resp.raise_for_status()
        return resp.text

    def _parse_betexplorer_matches(self, html: str) -> list[dict]:
        parser = _BetExplorerTableParser()
        parser.feed(html)

        matches = []
        current_stage = None
        for row in parser.rows:
            cells = [cell for cell in row if cell != ""]
            if not cells:
                continue

            if cells[0].startswith("Group ") and "Round" in cells[0]:
                current_stage = cells[0]
                continue

            fixture = self._parse_fixture_row(cells, current_stage)
            if fixture:
                matches.append(fixture)
                continue

            result = self._parse_result_row(cells, current_stage)
            if result:
                matches.append(result)

        return matches

    def _parse_fixture_row(self, cells: list[str], stage: str | None) -> dict | None:
        if len(cells) < 6 or " - " not in cells[1]:
            return None
        provider_count = self._to_int(cells[2])
        odds_home = self._to_float(cells[3])
        odds_draw = self._to_float(cells[4])
        odds_away = self._to_float(cells[5])
        if odds_home is None or odds_draw is None or odds_away is None:
            return None
        home, away = [part.strip() for part in cells[1].split(" - ", 1)]
        return {
            "stage": stage,
            "time": cells[0],
            "home_team": self._clean_team_name(home),
            "away_team": self._clean_team_name(away),
            "provider_count": provider_count or 1,
            "odds_home": odds_home,
            "odds_draw": odds_draw,
            "odds_away": odds_away,
        }

    def _parse_result_row(self, cells: list[str], stage: str | None) -> dict | None:
        if len(cells) < 5 or " - " not in cells[0] or not re.match(r"^\d+:\d+|CAN\.", cells[1]):
            return None
        odds_home = self._to_float(cells[2])
        odds_draw = self._to_float(cells[3])
        odds_away = self._to_float(cells[4])
        if odds_home is None or odds_draw is None or odds_away is None:
            return None
        home, away = [part.strip() for part in cells[0].split(" - ", 1)]
        return {
            "stage": stage,
            "time": cells[5] if len(cells) > 5 else None,
            "home_team": self._clean_team_name(home),
            "away_team": self._clean_team_name(away),
            "provider_count": 1,
            "odds_home": odds_home,
            "odds_draw": odds_draw,
            "odds_away": odds_away,
        }

    def _save_betexplorer_matches(self, matches: list[dict]) -> int:
        db = SessionLocal()
        try:
            teams = {team.code: team for team in db.query(Team).all()}
            saved_count = 0
            for match in matches:
                team_a_code, team_b_code = self._match_teams(match["home_team"], match["away_team"], teams)
                if not team_a_code:
                    continue
                team_a = teams[team_a_code]
                team_b = teams[team_b_code]
                self._save_to_db(db, team_a, team_b, self._to_odds_data(match))
                self._set_summary_provider_count(db, team_a.code, team_b.code, match["provider_count"])
                saved_count += 1
            db.commit()
            return saved_count
        finally:
            db.close()

    @staticmethod
    def _dedupe_matches(matches: list[dict]) -> list[dict]:
        seen = set()
        deduped = []
        for match in matches:
            key = (match["home_team"].lower(), match["away_team"].lower(), match.get("time"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(match)
        return deduped

    @staticmethod
    def _to_odds_data(match: dict) -> dict:
        return {
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "commence_time": match.get("time"),
            "bookmakers": [{
                "name": BETEXPLORER_BOOKMAKER["name"],
                "slug": BETEXPLORER_BOOKMAKER["slug"],
                "outcomes": {
                    match["home_team"]: match["odds_home"],
                    "Draw": match["odds_draw"],
                    match["away_team"]: match["odds_away"],
                },
            }],
        }

    @staticmethod
    def _to_float(value: str) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value: str) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clean_team_name(name: str) -> str:
        return re.sub(r"\s+", " ", name.replace("**", "")).strip()

    def _query_db_cache(self, code_a: str, code_b: str) -> dict | None:
        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(hours=ODDS_CACHE_TTL_HOURS)

            summary = db.query(MatchOddsSummary).filter(
                MatchOddsSummary.team_a_code == code_a,
                MatchOddsSummary.team_b_code == code_b,
                MatchOddsSummary.updated_at >= cutoff,
            ).first()

            if not summary:
                summary = db.query(MatchOddsSummary).filter(
                    MatchOddsSummary.team_a_code == code_b,
                    MatchOddsSummary.team_b_code == code_a,
                    MatchOddsSummary.updated_at >= cutoff,
                ).first()

            if not summary or not summary.provider_count:
                return None

            odds_list = db.query(MatchOdds).filter(
                ((MatchOdds.team_a_code == code_a) & (MatchOdds.team_b_code == code_b)) |
                ((MatchOdds.team_a_code == code_b) & (MatchOdds.team_b_code == code_a)),
            ).all()

            if not odds_list:
                return None

            team_a = db.query(Team).filter(Team.code == code_a).first()
            team_b = db.query(Team).filter(Team.code == code_b).first()
            if not team_a or not team_b:
                return None

            bookmakers = []
            for odds in odds_list:
                bookmaker = db.query(Bookmaker).filter(Bookmaker.id == odds.bookmaker_id).first()
                if not bookmaker:
                    continue

                if odds.team_a_code == code_a:
                    team_a_odds = odds.odds_win
                    team_b_odds = odds.odds_lose
                else:
                    team_a_odds = odds.odds_lose
                    team_b_odds = odds.odds_win

                outcomes = {}
                if team_a_odds is not None:
                    outcomes[team_a.name] = team_a_odds
                if odds.odds_draw is not None:
                    outcomes["Draw"] = odds.odds_draw
                if team_b_odds is not None:
                    outcomes[team_b.name] = team_b_odds
                bookmakers.append({
                    "name": bookmaker.name,
                    "slug": bookmaker.slug,
                    "outcomes": outcomes,
                })

            if not bookmakers:
                return None

            return {
                "home_team": team_a.name,
                "away_team": team_b.name,
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

    @staticmethod
    def _normalize_team_name(name: str) -> str:
        """归一化队名：去除空格、点号、连字符等分隔符，用于模糊匹配"""
        # 特殊名称映射（BetExplorer 常见别名）
        special_mappings = {
            'bosnia': 'bosniaherzegovina',
            'herzegovina': 'bosniaherzegovina',
            'curacao': 'curacao',
            'curaçao': 'curacao',
            'unitedstates': 'usa',
            'states': 'usa',
        }
        normalized = re.sub(r"[\s.\-&]+", "", name.lower())
        # 检查特殊映射
        for key, mapped in special_mappings.items():
            if key in normalized:
                return mapped
        return normalized

    @staticmethod
    def _match_teams(home_name: str, away_name: str, teams: dict[str, Team]) -> tuple[str | None, str | None]:
        # 归一化后比较（避免 "DR Congo" vs "D.R. Congo" / "D R Congo" 等格式差异）
        home_norm = OddsClient._normalize_team_name(home_name)
        away_norm = OddsClient._normalize_team_name(away_name)
        for code, team in teams.items():
            team_norm = OddsClient._normalize_team_name(team.name)
            if team_norm in home_norm:
                for code2, team2 in teams.items():
                    if code2 != code:
                        team2_norm = OddsClient._normalize_team_name(team2.name)
                        if team2_norm in away_norm:
                            return code, code2
        return None, None

    def _save_to_database(self, team_a: Team, team_b: Team, odds_data: dict):
        db = SessionLocal()
        try:
            self._save_to_db(db, team_a, team_b, odds_data)
            db.commit()
        finally:
            db.close()

    def _save_to_db(self, db, team_a: Team, team_b: Team, odds_data: dict):
        for bm in odds_data["bookmakers"]:
            bookmaker = db.query(Bookmaker).filter(Bookmaker.slug == bm["slug"]).first()
            if not bookmaker:
                bookmaker = Bookmaker(
                    name=bm["name"],
                    slug=bm["slug"],
                    country=BETEXPLORER_BOOKMAKER["country"],
                )
                db.add(bookmaker)
                db.commit()
                db.refresh(bookmaker)

            home_team_name = odds_data["home_team"]
            team_a_is_home = OddsClient._normalize_team_name(team_a.name) in OddsClient._normalize_team_name(home_team_name)

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

        db.flush()
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
            "best_win_provider": BETEXPLORER_BOOKMAKER["name"],
            "best_draw_provider": BETEXPLORER_BOOKMAKER["name"],
            "best_lose_provider": BETEXPLORER_BOOKMAKER["name"],
            "provider_count": len(odds_list),
            "updated_at": now,
        }

        if summary:
            for key, value in row.items():
                setattr(summary, key, value)
        else:
            db.add(MatchOddsSummary(
                team_a_code=team_a_code,
                team_b_code=team_b_code,
                **row,
            ))

        latest_history = (
            db.query(MatchOddsHistory)
            .filter(MatchOddsHistory.team_a_code == team_a_code)
            .filter(MatchOddsHistory.team_b_code == team_b_code)
            .order_by(MatchOddsHistory.recorded_at.desc())
            .first()
        )
        if not latest_history or (
            latest_history.avg_odds_win != row["avg_odds_win"]
            or latest_history.avg_odds_draw != row["avg_odds_draw"]
            or latest_history.avg_odds_lose != row["avg_odds_lose"]
        ):
            db.add(MatchOddsHistory(
                team_a_code=team_a_code,
                team_b_code=team_b_code,
                avg_odds_win=row["avg_odds_win"],
                avg_odds_draw=row["avg_odds_draw"],
                avg_odds_lose=row["avg_odds_lose"],
                provider_count=row["provider_count"],
                recorded_at=now,
            ))

    @staticmethod
    def _set_summary_provider_count(db, team_a_code: str, team_b_code: str, provider_count: int):
        summary = db.query(MatchOddsSummary).filter(
            MatchOddsSummary.team_a_code == team_a_code,
            MatchOddsSummary.team_b_code == team_b_code,
        ).first()
        if summary:
            summary.provider_count = provider_count

    async def close(self):
        await self.session.aclose()


odds_client = OddsClient()
