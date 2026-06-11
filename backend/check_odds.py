import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.models.odds_data import MatchOdds, MatchOddsSummary, Bookmaker

db = SessionLocal()

# Check if we have any odds data
odds_count = db.query(MatchOdds).count()
summary_count = db.query(MatchOddsSummary).count()
bookmaker_count = db.query(Bookmaker).count()

print(f'MatchOdds count: {odds_count}')
print(f'MatchOddsSummary count: {summary_count}')
print(f'Bookmaker count: {bookmaker_count}')

if odds_count > 0:
    # Show a sample
    sample = db.query(MatchOdds).first()
    print(f'\nSample MatchOdds:')
    print(f'  team_a_code: {sample.team_a_code}')
    print(f'  team_b_code: {sample.team_b_code}')
    print(f'  odds_win: {sample.odds_win}')
    print(f'  odds_draw: {sample.odds_draw}')
    print(f'  odds_lose: {sample.odds_lose}')
    print(f'  expires_at: {sample.expires_at}')
    
    # Check if expired
    from datetime import datetime
    is_expired = sample.expires_at < datetime.utcnow() if sample.expires_at else True
    print(f'  is_expired: {is_expired}')

if summary_count > 0:
    sample_summary = db.query(MatchOddsSummary).first()
    print(f'\nSample MatchOddsSummary:')
    print(f'  team_a_code: {sample_summary.team_a_code}')
    print(f'  team_b_code: {sample_summary.team_b_code}')
    print(f'  avg_odds_win: {sample_summary.avg_odds_win}')
    print(f'  avg_odds_draw: {sample_summary.avg_odds_draw}')
    print(f'  avg_odds_lose: {sample_summary.avg_odds_lose}')
    print(f'  provider_count: {sample_summary.provider_count}')
    print(f'  updated_at: {sample_summary.updated_at}')

if bookmaker_count > 0:
    sample_bm = db.query(Bookmaker).first()
    print(f'\nSample Bookmaker:')
    print(f'  name: {sample_bm.name}')
    print(f'  slug: {sample_bm.slug}')

db.close()
