from datetime import date, datetime
from types import SimpleNamespace
from app.services.match_aggregator import build_today_matches_response


def test_build_today_matches_response_empty(monkeypatch):
    monkeypatch.setattr("app.services.match_aggregator._query_matches_for_date", lambda db, target_date: [])
    response = build_today_matches_response(db=object(), target_date=date(2026, 6, 11))
    assert response["matches"] == []
    assert response["total"] == 0
    assert response["cache"]["ttl_seconds"] == 300


def test_build_today_matches_response_with_prediction_and_odds(monkeypatch):
    match = SimpleNamespace(
        match_id="BRA-FRA-2026-06-11",
        stage="group_stage",
        group_name="E",
        team_home_code="BRA",
        team_away_code="FRA",
        team_home_name="Brazil",
        team_away_name="France",
        commence_time=datetime(2026, 6, 11, 20, 0),
        fetched_at=datetime(2026, 6, 11, 10, 0),
    )
    team_a = SimpleNamespace(code="BRA", name="Brazil")
    team_b = SimpleNamespace(code="FRA", name="France")
    odds = SimpleNamespace(
        avg_odds_win=2.1,
        avg_odds_draw=3.4,
        avg_odds_lose=2.9,
        best_odds_win=2.2,
        best_odds_draw=3.5,
        best_odds_lose=3.0,
        best_win_provider="Book A",
        best_draw_provider="Book B",
        best_lose_provider="Book C",
        provider_count=3,
        updated_at=datetime(2026, 6, 11, 9, 0),
    )

    class FakeQuery:
        def __init__(self, value):
            self.value = value
        def filter(self, *args):
            return self
        def first(self):
            return self.value

    class FakeDb:
        def query(self, model):
            name = model.__name__
            if name == "Team":
                return FakeQuery(team_a if getattr(self, "team_calls", 0) == 0 else team_b)
            if name == "MatchOddsSummary":
                return FakeQuery(odds)
            return FakeQuery(None)

    fake_db = FakeDb()
    original_query = fake_db.query
    calls = {"team": 0}
    def query(model):
        if model.__name__ == "Team":
            value = team_a if calls["team"] == 0 else team_b
            calls["team"] += 1
            return FakeQuery(value)
        return original_query(model)
    fake_db.query = query

    monkeypatch.setattr("app.services.match_aggregator._query_matches_for_date", lambda db, target_date: [match])
    monkeypatch.setattr(
        "app.services.match_aggregator.engine.predict",
        lambda a, b, match_type: {
            "probabilities": {"win": 0.42, "draw": 0.28, "lose": 0.30},
            "system_confidence": 0.75,
        },
    )

    response = build_today_matches_response(db=fake_db, target_date=date(2026, 6, 11))
    assert response["total"] == 1
    item = response["matches"][0]
    assert item["match_id"] == "BRA-FRA-2026-06-11"
    assert item["home"]["code"] == "BRA"
    assert item["away"]["code"] == "FRA"
    assert item["prediction"]["win"] == 0.42
    assert item["odds"]["avg_win"] == 2.1
    assert item["odds"]["provider_count"] == 3