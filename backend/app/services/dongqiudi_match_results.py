"""Dongqiudi World Cup match results scraper.

Fetches match schedule/results from Dongqiudi World Cup data page.
Uses the same session/team-mapping infrastructure as the national roster scraper.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from sqlalchemy import func

from ..models.dongqiudi_match import DongqiudiMatch
from ..models.team import Team
from ..services.dongqiudi_national_roster import (
    DONGQIUDI_TEAM_ID_TO_CODE,
    BASE_URL,
    REQUEST_DELAY,
)

logger = logging.getLogger(__name__)

SCHEDULE_URL = "https://pc.dongqiudi.com/data?cid=61&tab=schedule"
# Reverse mapping: Chinese code -> Dongqiudi team id
CODE_TO_DONGQIUDI_ID = {v: k for k, v in DONGQIUDI_TEAM_ID_TO_CODE.items()}

# Stage mapping from Dongqiudi labels to normalized stage names
STAGE_MAP = {
    "小组赛": "group_stage",
    "1/16决赛": "round_of_32",
    "1/8决赛": "round_of_16",
    "1/4决赛": "quarter",
    "半决赛": "semi",
    "决赛": "final",
    "季军赛": "third_place",
}


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _generate_match_id(
    home_code: str, away_code: str, commence_time: datetime | None
) -> str:
    """Generate a unique match ID from team codes and time."""
    if commence_time:
        return f"dqd_{home_code}_{away_code}_{commence_time.strftime('%Y%m%d_%H%M')}"
    return f"dqd_{home_code}_{away_code}_{int(time.time())}"


def _parse_datetime(dt_str: str | None) -> datetime | None:
    """Parse datetime string from Dongqiudi."""
    if not dt_str:
        return None
    for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(dt_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _normalize_stage(stage_raw: str | None) -> str | None:
    """Normalize Dongqiudi stage label to internal stage name."""
    if not stage_raw:
        return None
    return STAGE_MAP.get(stage_raw, stage_raw)


def _infer_group_name(home_code: str, away_code: str, db: Session) -> str | None:
    """Infer group name from team codes."""
    from ..models.team import Team

    home = db.query(Team).filter(Team.code == home_code).first()
    if home and home.group_name:
        return home.group_name
    away = db.query(Team).filter(Team.code == away_code).first()
    if away and away.group_name:
        return away.group_name
    return None


def _load_team_code_map(db: Session) -> dict[str, str]:
    """Build a mapping of Chinese team names to Team codes."""
    from ..models.dongqiudi_data import DongqiudiTeamData

    mapping: dict[str, str] = {}
    teams = db.query(DongqiudiTeamData).filter(
        DongqiudiTeamData.matched_team_code.isnot(None)
    ).all()
    for t in teams:
        if t.name_cn:
            mapping[t.name_cn.strip().lower()] = t.matched_team_code
    return mapping


def fetch_schedule_html(client: httpx.Client | None = None) -> str:
    """Fetch the Dongqiudi World Cup schedule page HTML."""
    close_client = client is None
    client = client or httpx.Client(timeout=15.0)
    try:
        resp = client.get(SCHEDULE_URL, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.text
    finally:
        if close_client:
            client.close()


def fetch_schedule_data(
    client: httpx.Client | None = None,
) -> list[dict]:
    """Try to fetch schedule data from Dongqiudi API.

    Falls back to parsing HTML if the API endpoint is not available.
    """
    close_client = client is None
    client = client or httpx.Client(timeout=15.0)
    try:
        # Try the schedule data API first
        url = "https://pc.dongqiudi.com/sport-data/soccer/biz/dqd/v1/match/schedule"
        params = {"cid": "61", "app": "dqd"}
        resp = client.get(
            url,
            params=params,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://pc.dongqiudi.com/data?cid=61&tab=schedule",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and data.get("code") == 0:
                return data.get("data", []) or []
    except Exception:
        logger.warning("Failed to fetch schedule data from Dongqiudi API", exc_info=True)

    # Fallback: return empty list (HTML parsing could be added if needed)
    return []


def parse_match_from_api(
    item: dict,
    team_name_map: dict[str, str],
    db: Session,
) -> dict | None:
    """Parse a single match item from the Dongqiudi schedule API response."""
    try:
        match_id = str(item.get("id", ""))
        home_name_cn = (item.get("home_team_name") or item.get("home", {}) or {}).get("name", "")
        away_name_cn = (item.get("away_team_name") or item.get("away", {}) or {}).get("name", "")

        if not home_name_cn or not away_name_cn:
            return None

        home_code = team_name_map.get(home_name_cn.strip().lower())
        away_code = team_name_map.get(away_name_cn.strip().lower())

        if not home_code or not away_code:
            return None

        # Parse scores
        score_home_t = item.get("score_home") or (item.get("score", {}) or {}).get("home")
        score_away_t = item.get("score_away") or (item.get("score", {}) or {}).get("away")

        score_home = int(score_home_t) if score_home_t is not None else None
        score_away = int(score_away_t) if score_away_t is not None else None

        # Extra time
        score_home_et_t = item.get("score_home_et") or (item.get("score_et", {}) or {}).get("home")
        score_away_et_t = item.get("score_away_et") or (item.get("score_et", {}) or {}).get("away")
        score_home_et = int(score_home_et_t) if score_home_et_t is not None else None
        score_away_et = int(score_away_et_t) if score_away_et_t is not None else None

        # Penalties
        home_p = item.get("home_penalties") or (item.get("penalties", {}) or {}).get("home")
        away_p = item.get("away_penalties") or (item.get("penalties", {}) or {}).get("away")

        # Status
        status_raw = item.get("status", "")
        if status_raw in ("completed", "finished", "ended", "3"):
            status = "completed"
        elif status_raw in ("live", "playing", "inprogress", "2"):
            status = "live"
        else:
            status = "upcoming"

        # Stage
        stage_raw = item.get("stage") or item.get("round_name") or item.get("round")
        stage = _normalize_stage(stage_raw) if isinstance(stage_raw, str) else stage_raw

        # Time
        time_raw = item.get("commence_time") or item.get("start_time") or item.get("match_time")
        commence_time = _parse_datetime(time_raw) if isinstance(time_raw, str) else None

        # If no match_id, generate one
        if not match_id:
            match_id = _generate_match_id(home_code, away_code, commence_time)

        # Infer group name
        group_name = item.get("group_name") or _infer_group_name(home_code, away_code, db)

        return {
            "match_id": match_id,
            "stage": stage,
            "group_name": group_name,
            "team_home_code": home_code,
            "team_away_code": away_code,
            "team_home_name_cn": home_name_cn,
            "team_away_name_cn": away_name_cn,
            "score_home": score_home,
            "score_away": score_away,
            "score_home_et": score_home_et,
            "score_away_et": score_away_et,
            "home_penalties": int(home_p) if home_p is not None else None,
            "away_penalties": int(away_p) if away_p is not None else None,
            "status": status,
            "commence_time": commence_time,
            "stadium": item.get("stadium") or item.get("venue"),
            "raw_data": _json_dumps(item),
        }
    except Exception:
        logger.warning("Failed to parse match item from API", exc_info=True)
        return None


def upsert_match(db: Session, match_data: dict) -> bool:
    """Upsert a single match into the dongqiudi_matches table."""
    existing = (
        db.query(DongqiudiMatch)
        .filter(DongqiudiMatch.match_id == match_data["match_id"])
        .first()
    )

    if existing:
        for k, v in match_data.items():
            if k != "match_id":
                setattr(existing, k, v)
    else:
        db.add(DongqiudiMatch(**match_data))

    return True


def scrape_all_matches(db: Session) -> dict:
    """Fetch all World Cup matches from Dongqiudi and persist to DB.

    Tries the JSON API first; falls back to HTML parsing if API is unavailable.
    """
    team_name_map = _load_team_code_map(db)
    errors: list[dict] = []
    saved = 0
    total = 0

    with httpx.Client(timeout=15.0) as client:
        # Try JSON API first
        items = fetch_schedule_data(client)

        if items:
            total = len(items)
            for item in items:
                try:
                    match_data = parse_match_from_api(item, team_name_map, db)
                    if match_data:
                        upsert_match(db, match_data)
                        saved += 1
                    time.sleep(REQUEST_DELAY / 2)
                except Exception as exc:
                    errors.append({"match_id": item.get("id"), "error": str(exc)})
        else:
            # Fallback: parse schedule HTML
            try:
                html = fetch_schedule_html(client)
            except Exception as e:
                return {
                    "source": "dongqiudi",
                    "type": "match_results",
                    "matches_found": 0,
                    "matches_saved": 0,
                    "errors": [{"error": f"Failed to fetch schedule HTML: {e}"}],
                }

            entries = parse_schedule_html(html)
            total = len(entries)

            for entry in entries:
                try:
                    home_code = team_name_map.get(entry["team_home_name_cn"].strip().lower())
                    away_code = team_name_map.get(entry["team_away_name_cn"].strip().lower())

                    if not home_code or not away_code:
                        errors.append({
                            "match_id": entry["match_id"],
                            "error": f"Cannot resolve team codes: home={entry['team_home_name_cn']} -> {home_code}, away={entry['team_away_name_cn']} -> {away_code}",
                        })
                        continue

                    match_data = {
                        "match_id": entry["match_id"],
                        "stage": entry["stage"],
                        "group_name": entry.get("group_name"),
                        "team_home_code": home_code,
                        "team_away_code": away_code,
                        "team_home_name_cn": entry["team_home_name_cn"],
                        "team_away_name_cn": entry["team_away_name_cn"],
                        "score_home": entry.get("score_home"),
                        "score_away": entry.get("score_away"),
                        "score_home_et": None,
                        "score_away_et": None,
                        "home_penalties": None,
                        "away_penalties": None,
                        "status": entry.get("status", "upcoming"),
                        "commence_time": entry["commence_time"],
                        "stadium": None,
                        "raw_data": None,
                    }
                    upsert_match(db, match_data)
                    saved += 1
                    time.sleep(REQUEST_DELAY / 2)
                except Exception as exc:
                    errors.append({"match_id": entry.get("match_id"), "error": str(exc)})

        db.commit()

    return {
        "source": "dongqiudi",
        "type": "match_results",
        "matches_found": total,
        "matches_saved": saved,
        "errors": errors,
    }


# ── Smart post-match scraping ──────────────────────────────────────
# Each match is expected to last ~105 min (90' + 15' half-time).
# We wait ESTIMATED_MATCH_DURATION + POST_MATCH_COOLDOWN before scraping.
# This avoids hammering the dongqiudi servers while the match is live.

ESTIMATED_MATCH_DURATION_MIN = 120    # 90' + 15' HT + stoppage
POST_MATCH_COOLDOWN_MIN = 30          # wait 30 min after estimated end


def parse_schedule_html(html: str) -> list[dict]:
    """Parse the Dongqiudi schedule HTML to extract all match entries.

    Returns a list of dicts with keys:
        match_id, team_home_name_cn, team_away_name_cn,
        commence_time (datetime), stage, group_name (if group stage).
    """
    import re

    # Remove <script> blocks to avoid false positives from embedded data
    html_clean = re.sub(
        r'<script[^>]*>.*?</script>',
        '',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # Collect all visible stage header positions (in clean HTML only)
    # Note: HTML uses Arabic numerals (e.g. "小组赛 第1轮"), while the source
    # may also use Chinese numerals (e.g. "小组赛 第一轮") in other contexts
    header_pattern = re.compile(
        r'(小组赛\s*第[一二三四五六七八九十\d]+轮|1/[1-9]\d*决赛|半决赛|季军赛|决赛)',
    )
    header_positions: list[tuple[int, str]] = []
    for m in header_pattern.finditer(html_clean):
        header_positions.append((m.start(), m.group(1)))

    results: list[dict] = []

    # Find all match <a> tags in the clean HTML
    for match_tag in re.finditer(
        r'<a[^>]*href=["\']/match/(\d+)["\'][^>]*>'
        r'(.*?)</a>',
        html_clean,
        re.DOTALL | re.IGNORECASE,
    ):
        match_id = match_tag.group(1)
        inner = match_tag.group(2)

        # Find the nearest preceding stage header
        stage_raw = None
        for h_pos, h_text in reversed(header_positions):
            if h_pos < match_tag.start():
                stage_raw = h_text
                break
        # Match stage by prefix (e.g. "小组赛 第1轮" starts with "小组赛")
        stage = None
        if stage_raw:
            for map_key, map_val in STAGE_MAP.items():
                if stage_raw.startswith(map_key):
                    stage = map_val
                    break
            if stage is None:
                stage = stage_raw

        # Extract time from dp-schedule-row__time
        time_m = re.search(
            r'dp-schedule-row__time[^>]*>\s*([^<]+)\s*<',
            inner,
        )
        time_text = time_m.group(1).strip() if time_m else ""

        dt = None
        time_clean = re.sub(r'[^\d\-:\s]', '', time_text).strip()
        if time_clean:
            dt = _parse_datetime(time_clean)

        # Extract home team name
        home_m = re.search(
            r'dp-schedule-row__team--home[^>]*>\s*([^<]+)\s*<',
            inner,
        )
        home = home_m.group(1).strip() if home_m else ""

        # Extract away team name
        away_m = re.search(
            r'dp-schedule-row__team--away[^>]*>\s*([^<]+)\s*<',
            inner,
        )
        away = away_m.group(1).strip() if away_m else ""

        # Skip placeholder matches (e.g. "A2 - B2")
        skip = False
        for placeholder in (
            "A1", "A2", "B1", "B2", "C1", "C2", "D1", "D2",
            "E1", "E2", "F1", "F2", "G1", "G2", "H1", "H2",
            "I1", "I2", "J1", "J2", "K1", "K2", "L1", "L2",
        ):
            if home == placeholder or away == placeholder:
                skip = True
                break
        if home.startswith("第"):
            skip = True
        if skip:
            continue

        # Extract status and score from the match row
        # Pattern: look for status text (已结束/未开始) and score (X - Y)
        status = "upcoming"
        score_home = None
        score_away = None

        # Check for completed status
        if re.search(r'已结束|已完成|finished|completed', inner, re.IGNORECASE):
            status = "completed"
        elif re.search(r'进行中|上半场|下半场|中场休息|live', inner, re.IGNORECASE):
            status = "live"

        # Extract score pattern: "HOME X - Y AWAY" or similar
        score_m = re.search(
            r'(?:dp-schedule-row__score[^>]*>|>\s*)'
            r'(\d+)\s*[-:]\s*(\d+)'
            r'(?:\s*<|\s*$)',
            inner,
        )
        if score_m:
            try:
                score_home = int(score_m.group(1))
                score_away = int(score_m.group(2))
                if status == "upcoming" and score_home is not None:
                    status = "completed"
            except (ValueError, TypeError):
                pass

        # Derive group name for group stage matches
        group_name = None
        if stage == "group_stage":
            pass

        results.append({
            "match_id": match_id,
            "team_home_name_cn": home,
            "team_away_name_cn": away,
            "commence_time": dt,
            "stage": stage,
            "group_name": group_name,
            "status": status,
            "score_home": score_home,
            "score_away": score_away,
        })

    return results


def fetch_match_detail_page(
    match_id: str,
    client: httpx.Client,
) -> str:
    """Fetch a single match's detail page from Dongqiudi."""
    url = f"{BASE_URL}/match/{match_id}"
    resp = client.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://pc.dongqiudi.com/data?cid=61&tab=schedule",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    resp.raise_for_status()
    return resp.text


def parse_match_detail_html(
    html: str,
    match_id: str,
    team_name_map: dict[str, str],
    db: Session,
) -> dict | None:
    """Parse a single match detail page for the final score.

    Returns the match data dict (same format as parse_match_from_api)
    if the match is finished, or None if it's still upcoming/live.
    """
    import re

    # Try to extract score from the page title/match-header
    # Pattern: look for "HOME SCORE - AWAY SCORE" near "VS" or in the header
    # Also try the __INITIAL_STATE__ JSON
    score_data = {"score_home": None, "score_away": None}

    # Approach 1: look for __INITIAL_STATE__
    json_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
    if json_match:
        try:
            state = json.loads(json_match.group(1))
            match_info = (
                state.get("matchInfo")
                or state.get("match")
                or state.get("data", {}).get("match")
                or {}
            )
            if match_info:
                score_h = match_info.get("score_home") or match_info.get("home_score")
                score_a = match_info.get("score_away") or match_info.get("away_score")
                if score_h is not None and score_a is not None:
                    sh = int(score_h) if str(score_h).isdigit() else None
                    sa = int(score_a) if str(score_a).isdigit() else None
                    if sh is not None and sa is not None:
                        score_data["score_home"] = sh
                        score_data["score_away"] = sa
        except (json.JSONDecodeError, AttributeError, ValueError):
            pass

    if score_data["score_home"] is None:
        # Approach 2: look for score in visible HTML
        # Pattern: "MEXICO 2 - 1 SOUTH AFRICA" in page
        score_pattern = re.compile(
            r'(?:score|比分)[^<]*?(\d+)\s*[:\-—]\s*(\d+)',
            re.IGNORECASE,
        )
        score_m = score_pattern.search(html)
        if score_m:
            score_data["score_home"] = int(score_m.group(1))
            score_data["score_away"] = int(score_m.group(2))

    if score_data["score_home"] is None:
        return None  # No score found — match not finished

    # Infer team codes from match context
    home_code = None
    away_code = None

    # Extract team names from the detail page header
    team_pattern = re.compile(
        r'class=["\'](?:home|team-name)[^"\']*["\'][^>]*>([^<]+)</',
        re.IGNORECASE,
    )
    team_matches = team_pattern.findall(html)
    if len(team_matches) >= 2:
        home_code = team_name_map.get(team_matches[0].strip().lower())
        away_code = team_name_map.get(team_matches[1].strip().lower())

    if not home_code or not away_code:
        return None

    return {
        "match_id": match_id if match_id and match_id.strip() else f"dqd_{home_code}_{away_code}_{int(time.time())}",
        "stage": None,  # Will be filled in by caller
        "group_name": None,
        "team_home_code": home_code,
        "team_away_code": away_code,
        "team_home_name_cn": team_matches[0].strip() if len(team_matches) >= 1 else "",
        "team_away_name_cn": team_matches[1].strip() if len(team_matches) >= 2 else "",
        "score_home": score_data["score_home"],
        "score_away": score_data["score_away"],
        "score_home_et": None,
        "score_away_et": None,
        "home_penalties": None,
        "away_penalties": None,
        "status": "completed",
        "commence_time": None,
        "stadium": None,
        "raw_data": _json_dumps({"source": "match_detail_page", "match_id": match_id}),
    }


def scrape_recently_finished_matches(db: Session) -> dict:
    """Scrape only matches that have recently finished.

    Strategy:
      1. Parse the schedule HTML to get all match entries.
      2. Skip matches already in DB with status="completed".
      3. For each match whose estimated end time + cooldown has passed,
         fetch the match detail page and parse the score.
      4. Save only matches that have scores (i.e., are finished).

    Returns a dict with stats about what was scraped.
    """
    team_name_map = _load_team_code_map(db)
    now = datetime.utcnow()
    errors: list[dict] = []
    saved = 0
    skipped_already = 0
    skipped_too_early = 0
    not_yet_finished = 0

    with httpx.Client(timeout=15.0) as client:
        # Step 1: Fetch schedule page
        try:
            html = fetch_schedule_html(client)
        except Exception as e:
            return {
                "source": "dongqiudi",
                "type": "recently_finished",
                "matches_saved": 0,
                "skipped_already_completed": 0,
                "skipped_too_early": 0,
                "not_yet_finished": 0,
                "total_in_schedule": 0,
                "errors": [{"error": f"Failed to fetch schedule: {e}"}],
            }

        match_entries = parse_schedule_html(html)
        if not match_entries:
            return {
                "source": "dongqiudi",
                "type": "recently_finished",
                "matches_saved": 0,
                "skipped_already_completed": 0,
                "skipped_too_early": 0,
                "not_yet_finished": 0,
                "total_in_schedule": 0,
                "errors": [{"error": "No matches found in schedule HTML"}],
            }

        # Step 2: Check each match
        for entry in match_entries:
            match_id = entry["match_id"]
            commence_time = entry["commence_time"]

            # Skip if already in DB with status "completed"
            existing = (
                db.query(DongqiudiMatch)
                .filter(
                    DongqiudiMatch.match_id == match_id,
                    DongqiudiMatch.status == "completed",
                )
                .first()
            )
            if existing:
                skipped_already += 1
                continue

            # Check if estimated end time + cooldown has passed
            if commence_time:
                end_time = datetime.fromtimestamp(
                    commence_time.timestamp() + (ESTIMATED_MATCH_DURATION_MIN + POST_MATCH_COOLDOWN_MIN) * 60
                )
                if now < end_time:
                    skipped_too_early += 1
                    continue

            # Step 3: Fetch match detail page
            try:
                detail_html = fetch_match_detail_page(match_id, client)
                match_data = parse_match_detail_html(detail_html, match_id, team_name_map, db)
            except Exception as e:
                errors.append({"match_id": match_id, "error": str(e)})
                time.sleep(REQUEST_DELAY)
                continue

            if not match_data:
                not_yet_finished += 1
                time.sleep(REQUEST_DELAY)
                continue

            # Fill in stage and group from schedule entry
            match_data["stage"] = entry.get("stage")
            match_data["group_name"] = entry.get("group_name")
            match_data["commence_time"] = commence_time

            if not match_data["team_home_name_cn"]:
                match_data["team_home_name_cn"] = entry.get("team_home_name_cn", "")
            if not match_data["team_away_name_cn"]:
                match_data["team_away_name_cn"] = entry.get("team_away_name_cn", "")

            # Also use match_id from schedule if parse didn't produce one
            if match_id and (not match_data.get("match_id") or len(match_data["match_id"]) < 5):
                match_data["match_id"] = f"dqd_{match_data['team_home_code']}_{match_data['team_away_code']}_{commence_time.strftime('%Y%m%d_%H%M')}" if commence_time else match_id

            # Step 4: Save to DB
            try:
                upsert_match(db, match_data)
                saved += 1
                db.commit()
            except Exception as e:
                db.rollback()
                errors.append({"match_id": match_id, "error": str(e)})

            time.sleep(REQUEST_DELAY)

    return {
        "source": "dongqiudi",
        "type": "recently_finished",
        "matches_saved": saved,
        "skipped_already_completed": skipped_already,
        "skipped_too_early": skipped_too_early,
        "not_yet_finished": not_yet_finished,
        "total_in_schedule": len(match_entries),
        "errors": errors,
    }


def compute_tournament_overview(db: Session) -> dict:
    """Compute tournament overview statistics from Dongqiudi match data.

    Returns champion, runner-up, third place, total matches, total goals,
    and match counts per stage.
    """
    from sqlalchemy import func as sa_func

    # Total matches and goals
    stats = (
        db.query(
            sa_func.count(DongqiudiMatch.id).label("total_matches"),
            sa_func.coalesce(sa_func.sum(DongqiudiMatch.score_home), 0)
            + sa_func.coalesce(sa_func.sum(DongqiudiMatch.score_away), 0),
        )
        .filter(DongqiudiMatch.status == "completed")
        .first()
    )
    total_matches = stats[0] or 0
    total_goals = stats[1] or 0

    # Find final match → champion/runner-up
    champion_code = None
    runner_up_code = None
    final_match = (
        db.query(DongqiudiMatch)
        .filter(
            DongqiudiMatch.stage == "final",
            DongqiudiMatch.status == "completed",
        )
        .first()
    )
    if final_match:
        if final_match.score_home is not None and final_match.score_away is not None:
            if final_match.score_home > final_match.score_away:
                champion_code = final_match.team_home_code
                runner_up_code = final_match.team_away_code
            else:
                champion_code = final_match.team_away_code
                runner_up_code = final_match.team_home_code

    # Find third place match
    third_place_code = None
    third_place_match = (
        db.query(DongqiudiMatch)
        .filter(
            DongqiudiMatch.stage == "third_place",
            DongqiudiMatch.status == "completed",
        )
        .first()
    )
    if third_place_match:
        if third_place_match.score_home is not None and third_place_match.score_away is not None:
            if third_place_match.score_home > third_place_match.score_away:
                third_place_code = third_place_match.team_home_code
            else:
                third_place_code = third_place_match.team_away_code

    # Match counts per stage
    stage_counts = {}
    for row in (
        db.query(DongqiudiMatch.stage, sa_func.count(DongqiudiMatch.id))
        .filter(DongqiudiMatch.status == "completed")
        .group_by(DongqiudiMatch.stage)
        .all()
    ):
        stage_counts[row[0]] = row[1]

    # Team names for display
    def _team_name(code: str | None) -> str | None:
        if not code:
            return None
        team = db.query(Team).filter(Team.code == code).first()
        return team.name if team else code

    return {
        "tournament": "2026 FIFA World Cup",
        "host": "Canada, Mexico, USA",
        "champion": {"code": champion_code, "name": _team_name(champion_code)},
        "runner_up": {"code": runner_up_code, "name": _team_name(runner_up_code)},
        "third_place": {"code": third_place_code, "name": _team_name(third_place_code)},
        "total_matches": total_matches,
        "total_goals": total_goals,
        "matches_per_stage": stage_counts,
        "source": "dongqiudi",
    }
