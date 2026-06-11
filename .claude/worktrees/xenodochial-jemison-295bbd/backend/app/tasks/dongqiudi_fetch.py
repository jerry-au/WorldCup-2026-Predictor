"""Dongqiudi scraper batch tasks."""

from ..database import SessionLocal


def run_dongqiudi_scrape() -> dict:
    """Scrape player stats from dongqiudi league pages for configured leagues."""
    from ..services.dongqiudi_scraper import scrape_all_leagues

    db = SessionLocal()
    try:
        results = scrape_all_leagues(db)
    finally:
        db.close()

    total_scraped = sum(r.get("scraped", r.get("scraped_saved", r.get("listing_total", 0))) for r in results)
    total_matched = sum(r.get("matched", 0) for r in results)

    return {
        "source": "dongqiudi",
        "type": "league_players",
        "leagues": results,
        "total_scraped": total_scraped,
        "total_matched": total_matched,
    }


def run_dongqiudi_national_rosters() -> dict:
    """Scrape World Cup national team rosters via Dongqiudi member_v2 API."""
    from ..services.dongqiudi_national_roster import scrape_all_national_rosters

    db = SessionLocal()
    try:
        result = scrape_all_national_rosters(db)
    finally:
        db.close()

    return {
        "source": "dongqiudi",
        "type": "national_rosters",
        **result,
    }
