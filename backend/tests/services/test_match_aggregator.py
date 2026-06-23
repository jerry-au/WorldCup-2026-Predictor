from datetime import date, datetime
from types import SimpleNamespace

from app.models.dongqiudi_match import DongqiudiMatch
from app.services.match_aggregator import build_all_matches_response, build_today_matches_response, _query_matches_for_date


def test_query_matches_for_date_uses_48_hour_window_and_excludes_completed(db_session):
    db = db_session
    db.add_all([
        DongqiudiMatch(
            match_id="before-window",
            team_home_code="BRA",
            team_away_code="FRA",
            status="upcoming",
            commence_time=datetime(2026, 6, 10, 23, 59),
        ),
        DongqiudiMatch(
            match_id="at-start",
            team_home_code="ARG",
            team_away_code="MEX",
            status="upcoming",
            commence_time=datetime(2026, 6, 11, 0, 0),
        ),
        DongqiudiMatch(
            match_id="live-in-window",
            team_home_code="ESP",
            team_away_code="GER",
            status="live",
            commence_time=datetime(2026, 6, 12, 20, 0),
        ),
        DongqiudiMatch(
            match_id="completed-in-window",
            team_home_code="ENG",
            team_away_code="USA",
            status="completed",
            commence_time=datetime(2026, 6, 11, 12, 0),
        ),
        DongqiudiMatch(
            match_id="at-end",
            team_home_code="POR",
            team_away_code="URU",
            status="upcoming",
            commence_time=datetime(2026, 6, 13, 0, 0),
        ),
    ])
    db.commit()

    matches = _query_matches_for_date(
        db,
        date(2026, 6, 11),
        now=datetime(2026, 6, 10, 22, 0),
    )

    assert [match.match_id for match in matches] == ["at-start", "live-in-window"]


def test_query_matches_for_date_excludes_matches_past_estimated_finish_time(db_session):
    db = db_session
    db.add_all([
        DongqiudiMatch(
            match_id="already-ended-by-time",
            team_home_code="ESP",
            team_away_code="CPV",
            status="upcoming",
            commence_time=datetime(2026, 6, 16, 0, 0),
        ),
        DongqiudiMatch(
            match_id="currently-playing-by-time",
            team_home_code="BEL",
            team_away_code="EGY",
            status="upcoming",
            commence_time=datetime(2026, 6, 16, 7, 30),
        ),
        DongqiudiMatch(
            match_id="future-match",
            team_home_code="KSA",
            team_away_code="URU",
            status="upcoming",
            commence_time=datetime(2026, 6, 16, 12, 0),
        ),
    ])
    db.commit()

    matches = _query_matches_for_date(
        db,
        date(2026, 6, 16),
        now=datetime(2026, 6, 16, 9, 0),
    )

    assert [match.match_id for match in matches] == ["currently-playing-by-time", "future-match"]


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
    team_a = SimpleNamespace(
        code="BRA",
        name="Brazil",
        name_cn="巴西",
        local_flag_path=None,
        flag_url=None,
    )
    team_b = SimpleNamespace(
        code="FRA",
        name="France",
        name_cn="法国",
        local_flag_path=None,
        flag_url=None,
    )
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
        "app.services.match_aggregator._batch_preload_teams_and_odds",
        lambda db, matches: ({"BRA": team_a, "FRA": team_b}, {("BRA", "FRA"): odds}),
    )
    monkeypatch.setattr(
        "app.services.match_aggregator.engine.predict",
        lambda a, b, db=None, match_type="group": {
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


def test_build_all_matches_response_orders_completed_matches_desc(db_session, monkeypatch):
    db = db_session
    db.add_all([
        DongqiudiMatch(
            match_id="completed-oldest",
            team_home_code="BRA",
            team_away_code="FRA",
            status="completed",
            commence_time=datetime(2026, 6, 11, 12, 0),
            score_home=1,
            score_away=0,
        ),
        DongqiudiMatch(
            match_id="completed-newest",
            team_home_code="ARG",
            team_away_code="MEX",
            status="completed",
            commence_time=datetime(2026, 6, 13, 12, 0),
            score_home=2,
            score_away=1,
        ),
        DongqiudiMatch(
            match_id="completed-middle",
            team_home_code="ESP",
            team_away_code="GER",
            status="completed",
            commence_time=datetime(2026, 6, 12, 12, 0),
            score_home=0,
            score_away=0,
        ),
    ])
    db.commit()
    monkeypatch.setattr("app.services.match_aggregator._batch_preload_teams_and_odds", lambda db, matches: ({}, {}))

    response = build_all_matches_response(db, status="completed", page=1, page_size=10)

    assert [match["match_id"] for match in response["matches"]] == [
        "completed-newest",
        "completed-middle",
        "completed-oldest",
    ]