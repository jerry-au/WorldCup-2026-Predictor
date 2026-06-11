import sys
import json
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models.recommendation_cache import RecommendationCache
from app.models.team import Team
from app.core.prediction import PredictionEngine
from app.services.odds import odds_client
from app.services.recommendation import recommendation_engine

db = SessionLocal()
engine = PredictionEngine()

# 检查一场比赛
cache = db.query(RecommendationCache).filter(
    RecommendationCache.cache_type == 'value_bets'
).first()

if cache:
    team_a = db.query(Team).filter(Team.code == cache.team_a_code).first()
    team_b = db.query(Team).filter(Team.code == cache.team_b_code).first()
    print(f'Match: {team_a.name} vs {team_b.name}')
    
    pred = engine.predict(team_a, team_b, 'group')
    print(f'System probs: {pred["probabilities"]}')
    print(f'System confidence: {pred["system_confidence"]}')
    
    odds_data = odds_client._query_db_cache(cache.team_a_code, cache.team_b_code)
    if odds_data:
        print(f'Bookmakers: {len(odds_data.get("bookmakers", []))}')
        print(f'Market avg: {odds_data.get("market_avg")}')
        print(f'Home team key: {odds_data.get("home_team")}')
        print(f'Away team key: {odds_data.get("away_team")}')
        for bm in odds_data.get('bookmakers', [])[:2]:
            print(f'  {bm["name"]}: {bm["outcomes"]}')
        
        # Run analysis manually
        betting = recommendation_engine.analyze(
            system_probs=pred["probabilities"],
            system_confidence=pred["system_confidence"],
            odds_data=odds_data,
        )
        print(f'Recommendations: {betting["recommendations"]}')
        print(f'Discrepancy: {betting["discrepancy"]}')
    else:
        print('No odds data found in DB cache')
    
    print(f'Cached recommendations: {json.loads(cache.result_data)[:2]}')
else:
    print('No cache found')

db.close()
