import asyncio

from app.services.odds import OddsClient


FIXTURES_HTML = """
<table>
<tr><th>Group A - 2. Round</th><th></th><th>B's</th><th>1</th><th>X</th><th>2</th><th></th></tr>
<tr><td>18.06. 18:00</td><td><a href="/football/world/world-championship-2026/czech-republic-south-africa/8nrACRTs/"><span>Czech Republic</span> - <span>South Africa</span></a></td><td></td><td>4</td><td><button data-odd="1.77"></button></td><td><button data-odd="3.71"></button></td><td><button data-odd="4.58"></button></td></tr>
<tr><th>Group B - 2. Round</th><th></th><th>B's</th><th>1</th><th>X</th><th>2</th><th></th></tr>
<tr><td>19.06. 00:00</td><td><a href="/football/world/world-championship-2026/canada-qatar/67vLrBMM/"><span>Canada</span> - <span>Qatar</span></a></td><td></td><td>4</td><td><button data-odd="1.28"></button></td><td><button data-odd="5.55"></button></td><td><button data-odd="11.38"></button></td></tr>
</table>
"""


def test_fetch_all_and_cache_uses_betexplorer_without_odds_api(monkeypatch):
    requested_urls = []

    async def fake_fetch_text(url):
        requested_urls.append(url)
        return FIXTURES_HTML

    client = OddsClient()
    monkeypatch.setattr(client, "_fetch_betexplorer_text", fake_fetch_text)
    monkeypatch.setattr(client, "_save_betexplorer_matches", lambda matches: len(matches))

    result = asyncio.run(client.fetch_all_and_cache())

    assert result == {
        "status": "ok",
        "source": "betexplorer",
        "matches_returned": 2,
        "pairs_saved": 2,
        "api_requests_used": 0,
    }
    assert requested_urls == [client.BETEXPLORER_FIXTURES_URL, client.BETEXPLORER_RESULTS_URL]
    assert all("api.the-odds-api.com" not in url for url in requested_urls)


def test_parse_betexplorer_1x2_rows():
    client = OddsClient()

    matches = client._parse_betexplorer_matches(FIXTURES_HTML)

    assert matches == [
        {
            "stage": "Group A - 2. Round",
            "time": "18.06. 18:00",
            "home_team": "Czech Republic",
            "away_team": "South Africa",
            "provider_count": 4,
            "odds_home": 1.77,
            "odds_draw": 3.71,
            "odds_away": 4.58,
        },
        {
            "stage": "Group B - 2. Round",
            "time": "19.06. 00:00",
            "home_team": "Canada",
            "away_team": "Qatar",
            "provider_count": 4,
            "odds_home": 1.28,
            "odds_draw": 5.55,
            "odds_away": 11.38,
        },
    ]
