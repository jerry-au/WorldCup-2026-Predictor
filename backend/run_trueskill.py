"""
TrueSkill 双轨球员实力评估系统
================================
国家队评分（懂球帝）+ 俱乐部评分（season_stats）→ 综合得分

数据流：
1. 从 players 表读取所有球员（含位置、所属球队）
2. 国家队轨道：从 dongqiudi_players 读取国家队比赛数据
3. 俱乐部轨道：从 player_season_stats 读取俱乐部比赛数据
4. 在两套数据上分别运行 TrueSkill
5. 融合两套评分得到综合得分
6. 输出完整排行榜
"""

import re
import csv
import sqlite3
from collections import defaultdict
from typing import Dict, List, Optional

import trueskill
import numpy as np

# ─── 配置 ───────────────────────────────────────────────────────
DB_PATH = "worldcup.db"

# TrueSkill 参数
ENV = trueskill.TrueSkill(
    mu=25.0, sigma=25.0 / 3, beta=25.0 / 6,
    tau=25.0 / 300, draw_probability=0.10,
)

# 国家队评分权重（懂球帝数据：进球、助攻、出场、身价）
W_NT_GOALS = 0.30
W_NT_ASSISTS = 0.25
W_NT_APPEARANCES = 0.15
W_NT_MARKET_VALUE = 0.30

# 俱乐部评分权重（season_stats 数据：进球、助攻、出场、分钟、身价）
W_CL_GOALS = 0.25
W_CL_ASSISTS = 0.20
W_CL_APPEARANCES = 0.15
W_CL_MINUTES = 0.15
W_CL_MARKET_VALUE = 0.25

# 综合得分融合权重
W_NATIONAL = 0.40   # 国家队评分权重
W_CLUB = 0.60       # 俱乐部评分权重


def parse_market_value(text: Optional[str]) -> float:
    """将中文身价文本解析为欧元数值。"""
    if not text or not isinstance(text, str):
        return 0.0
    text = str(text).replace(",", "").strip()
    try:
        if "亿" in text:
            return float(re.search(r"([\d.]+)", text).group(1)) * 100_000_000
        elif "万" in text:
            return float(re.search(r"([\d.]+)", text).group(1)) * 10_000
        else:
            return float(re.search(r"([\d.]+)", text).group(1))
    except (ValueError, AttributeError):
        return 0.0


def safe_zscore(values: List[float]) -> Dict[float, float]:
    """计算 z-score，避免被零除和全相同的情况。"""
    arr = np.array(values)
    mean = np.mean(arr)
    std = np.std(arr)
    if std < 1e-10:
        return {v: 0.0 for v in values}
    return {v: (v - mean) / std for v in values}


class TrueSkillEngine:
    """基于 TrueSkill 的评分引擎，可独立运行于不同数据源。"""

    def __init__(self, name: str, market_values: Dict[int, float] = None):
        self.name = name
        self.env = ENV
        self.ratings: Dict[int, trueskill.Rating] = {}
        self.market_values = market_values or {}

        if self.market_values:
            values = sorted(self.market_values.values())
            n = len(values)
            self._mv_p25 = values[int(n * 0.25)] if n > 4 else 0
            self._mv_p50 = values[int(n * 0.50)] if n > 2 else 0
            self._mv_p75 = values[int(n * 0.75)] if n > 4 else 0
            self._mv_p90 = values[int(n * 0.90)] if n > 10 else 0
        else:
            self._mv_p25 = self._mv_p50 = self._mv_p75 = self._mv_p90 = 0

    def _get_initial_mu(self, player_id: int) -> float:
        mv = self.market_values.get(player_id, 0)
        if mv == 0:
            return 25.0
        if mv >= self._mv_p90:
            return 35.0
        elif mv >= self._mv_p75:
            return 30.0
        elif mv >= self._mv_p50:
            return 25.0
        elif mv >= self._mv_p25:
            return 20.0
        else:
            return 15.0

    def get_or_create_rating(self, player_id: int) -> trueskill.Rating:
        if player_id not in self.ratings:
            self.ratings[player_id] = self.env.create_rating(
                mu=self._get_initial_mu(player_id))
        return self.ratings[player_id]

    def update(self, player_scores: Dict[int, float],
               position_groups: Dict[int, str]):
        """在各自位置组内构建虚拟对战，更新 TrueSkill 评分。"""
        for position in ["GK", "DF", "MF", "FW"]:
            pos_players = [(pid, score) for pid, score in player_scores.items()
                           if position_groups.get(pid) == position]
            if len(pos_players) < 2:
                continue
            pos_players.sort(key=lambda x: x[1], reverse=True)

            # 第一轮：相邻配对
            for i in range(0, len(pos_players) - 1, 2):
                w_id, _ = pos_players[i]
                l_id, _ = pos_players[i + 1]
                r1, r2 = self.env.rate_1vs1(
                    self.get_or_create_rating(w_id),
                    self.get_or_create_rating(l_id))
                self.ratings[w_id] = r1
                self.ratings[l_id] = r2

            # 第二轮：隔一配对
            for i in range(0, len(pos_players) - 2, 2):
                w_id, _ = pos_players[i]
                l_id, _ = pos_players[i + 2]
                if w_id == l_id:
                    continue
                r1, r2 = self.env.rate_1vs1(
                    self.get_or_create_rating(w_id),
                    self.get_or_create_rating(l_id))
                self.ratings[w_id] = r1
                self.ratings[l_id] = r2

    def get_all_ratings(self) -> Dict[int, dict]:
        """返回 {player_id: {mu, sigma, conservative}}"""
        result = {}
        for pid, r in self.ratings.items():
            result[pid] = {
                "mu": round(r.mu, 2),
                "sigma": round(r.sigma, 2),
                "conservative": round(r.mu - 3 * r.sigma, 2),
            }
        return result


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ─── 1. 球队 & 球员基本信息 ────────────────────────────
    cur.execute("SELECT id, code, name FROM teams")
    team_code_map = {r["id"]: r["code"] for r in cur.fetchall()}

    cur.execute("SELECT id, name, position, team_id FROM players")
    player_names = {}
    player_positions = {}
    player_teams = {}
    for r in cur.fetchall():
        pid = r["id"]
        player_names[pid] = r["name"]
        player_positions[pid] = r["position"] or "N/A"
        player_teams[pid] = r["team_id"]

    total_players = len(player_names)
    print(f"{'='*60}")
    print(f"📊 共读取 {total_players} 名球员, {len(team_code_map)} 支球队")
    print(f"{'='*60}")

    # ═══════════════════════════════════════════════════════
    # ─── 轨道 A：国家队评分（懂球帝数据）───────────────
    # ═══════════════════════════════════════════════════════

    print(f"\n{'─'*60}")
    print(f"🏁 轨道 A：国家队评分（数据源：懂球帝）")
    print(f"{'─'*60}")

    cur.execute("""
        SELECT matched_player_id,
               SUM(goals) as total_goals,
               SUM(assists) as total_assists,
               SUM(appearances) as total_appearances
        FROM dongqiudi_players
        WHERE matched_player_id IS NOT NULL AND appearances > 0
        GROUP BY matched_player_id
    """)
    nt_stats = {}
    for r in cur.fetchall():
        nt_stats[r["matched_player_id"]] = {
            "goals": r["total_goals"] or 0,
            "assists": r["total_assists"] or 0,
            "appearances": r["total_appearances"] or 0,
        }
    print(f"  国家队有出场数据的球员: {len(nt_stats)} 人")

    # 身价数据（国家队和俱乐部轨道共享）
    cur.execute("""
        SELECT matched_player_id,
               MAX(CAST(REPLACE(REPLACE(market_value_text,'亿','00000000'),'万','0000') AS INTEGER)) as mv_raw
        FROM dongqiudi_players
        WHERE matched_player_id IS NOT NULL
          AND market_value_text IS NOT NULL AND market_value_text != ''
        GROUP BY matched_player_id
    """)
    market_values = {}
    for r in cur.fetchall():
        mv = parse_market_value(
            cur.execute("SELECT market_value_text FROM dongqiudi_players WHERE matched_player_id=? AND market_value_text!='' LIMIT 1",
                       (r["matched_player_id"],)).fetchone())
        if isinstance(mv, sqlite3.Row):
            mv = parse_market_value(mv[0])
        else:
            mv = r["mv_raw"] or 0
        if mv > 0:
            market_values[r["matched_player_id"]] = mv

    # 重新读取身价（简化版）
    market_values = {}
    cur.execute("""
        SELECT matched_player_id, market_value_text
        FROM dongqiudi_players
        WHERE matched_player_id IS NOT NULL
          AND market_value_text IS NOT NULL AND market_value_text != ''
    """)
    for r in cur.fetchall():
        pid = r["matched_player_id"]
        mv = parse_market_value(r["market_value_text"])
        if pid and mv > 0:
            if pid not in market_values or mv > market_values[pid]:
                market_values[pid] = mv

    # 球队身价回退
    cur.execute("SELECT id, market_value_eur FROM teams WHERE market_value_eur > 0")
    team_mv = {r["id"]: r["market_value_eur"] * 1_000_000 for r in cur.fetchall()}

    def fill_market_values(pid_set):
        for pid in pid_set:
            if pid not in market_values:
                tid = player_teams.get(pid, 0)
                if tid in team_mv:
                    team_players = [p for p in pid_set if player_teams.get(p, 0) == tid]
                    market_values[pid] = team_mv[tid] / max(len(team_players), 1)

    fill_market_values(set(nt_stats.keys()))
    print(f"  有身价数据的球员: {len(market_values)} 人")

    # 国家队 z-score
    def compute_scores(stats_dict, weights, mv_data, has_minutes=False):
        scores = {}
        match_counts = {}
        by_pos = defaultdict(list)
        for pid in stats_dict:
            by_pos[player_positions.get(pid, "N/A")].append(pid)

        for pos, pids in by_pos.items():
            if len(pids) < 2:
                for pid in pids:
                    scores[pid] = 0.0
                    match_counts[pid] = 0
                continue

            gv = [stats_dict[pid]["goals"] for pid in pids]
            av = [stats_dict[pid]["assists"] for pid in pids]
            apv = [stats_dict[pid]["appearances"] for pid in pids]
            mvv = [mv_data.get(pid, 0) for pid in pids]

            gz = safe_zscore(gv)
            az = safe_zscore(av)
            apz = safe_zscore(apv)
            mvz = safe_zscore(mvv)

            if has_minutes:
                minv = [stats_dict[pid].get("minutes_played", 0) for pid in pids]
                minz = safe_zscore(minv)
                for i, pid in enumerate(pids):
                    scores[pid] = (
                        weights["goals"] * gz[gv[i]] +
                        weights["assists"] * az[av[i]] +
                        weights["appearances"] * apz[apv[i]] +
                        weights["minutes"] * minz[minv[i]] +
                        weights["market_value"] * mvz[mvv[i]]
                    )
            else:
                for i, pid in enumerate(pids):
                    scores[pid] = (
                        weights["goals"] * gz[gv[i]] +
                        weights["assists"] * az[av[i]] +
                        weights["appearances"] * apz[apv[i]] +
                        weights["market_value"] * mvz[mvv[i]]
                    )
            match_counts.update({pid: stats_dict[pid]["appearances"] for pid in pids})
        return scores, match_counts

    nt_weights = {
        "goals": W_NT_GOALS, "assists": W_NT_ASSISTS,
        "appearances": W_NT_APPEARANCES, "market_value": W_NT_MARKET_VALUE,
    }
    nt_scores, nt_matches = compute_scores(nt_stats, nt_weights, market_values)

    nt_engine = TrueSkillEngine("国家队", market_values=market_values)
    nt_engine.update(nt_scores, player_positions)
    nt_ratings = nt_engine.get_all_ratings()

    # ═══════════════════════════════════════════════════════
    # ─── 轨道 B：俱乐部评分（season_stats 数据）─────────
    # ═══════════════════════════════════════════════════════

    print(f"\n{'─'*60}")
    print(f"🏁 轨道 B：俱乐部评分（数据源：football-data.org）")
    print(f"{'─'*60}")

    cur.execute("""
        SELECT player_id,
               SUM(goals) as total_goals,
               SUM(assists) as total_assists,
               SUM(appearances) as total_appearances,
               SUM(minutes_played) as total_minutes
        FROM player_season_stats
        GROUP BY player_id
    """)
    cl_stats = {}
    for r in cur.fetchall():
        cl_stats[r["player_id"]] = {
            "goals": r["total_goals"] or 0,
            "assists": r["total_assists"] or 0,
            "appearances": r["total_appearances"] or 0,
            "minutes_played": r["total_minutes"] or 0,
        }
    print(f"  俱乐部有出场数据的球员: {len(cl_stats)} 人")

    fill_market_values(set(cl_stats.keys()))

    cl_weights = {
        "goals": W_CL_GOALS, "assists": W_CL_ASSISTS,
        "appearances": W_CL_APPEARANCES, "minutes": W_CL_MINUTES,
        "market_value": W_CL_MARKET_VALUE,
    }
    cl_scores, cl_matches = compute_scores(cl_stats, cl_weights, market_values, has_minutes=True)

    cl_engine = TrueSkillEngine("俱乐部", market_values=market_values)
    cl_engine.update(cl_scores, player_positions)
    cl_ratings = cl_engine.get_all_ratings()

    # ═══════════════════════════════════════════════════════
    # ─── 融合：综合得分 ─────────────────────────────────
    # ═══════════════════════════════════════════════════════

    print(f"\n{'─'*60}")
    print(f"🏆 融合综合得分（国家队{W_NATIONAL:.0%} + 俱乐部{W_CLUB:.0%}）")
    print(f"{'─'*60}")

    all_pids = set(nt_ratings.keys()) | set(cl_ratings.keys())
    leaderboard = []

    for pid in all_pids:
        nt = nt_ratings.get(pid, {"mu": 25.0, "sigma": 8.33, "conservative": 0.0})
        cl = cl_ratings.get(pid, {"mu": 25.0, "sigma": 8.33, "conservative": 0.0})

        has_nt = pid in nt_ratings
        has_cl = pid in cl_ratings

        if has_nt and has_cl:
            combined_mu = round(W_NATIONAL * nt["mu"] + W_CLUB * cl["mu"], 2)
            combined_sigma = round(
                np.sqrt(W_NATIONAL**2 * nt["sigma"]**2 + W_CLUB**2 * cl["sigma"]**2), 2)
        elif has_nt:
            combined_mu = nt["mu"]
            combined_sigma = nt["sigma"]
        else:
            combined_mu = cl["mu"]
            combined_sigma = cl["sigma"]

        combined_conservative = round(combined_mu - 3 * combined_sigma, 2)
        matches = nt_matches.get(pid, 0) + cl_matches.get(pid, 0)

        leaderboard.append({
            "player_id": pid,
            "name": player_names.get(pid, f"#{pid}"),
            "position": player_positions.get(pid, "N/A"),
            "team": team_code_map.get(player_teams.get(pid, 0), "N/A"),
            "nt_mu": nt["mu"],
            "nt_sigma": nt["sigma"],
            "cl_mu": cl["mu"],
            "cl_sigma": cl["sigma"],
            "combined_mu": combined_mu,
            "combined_sigma": combined_sigma,
            "combined_rating": combined_conservative,
            "matches": matches,
            "has_nt": has_nt,
            "has_cl": has_cl,
        })

    leaderboard.sort(key=lambda x: x["combined_rating"], reverse=True)

    # ─── 输出结果 ─────────────────────────────────────────

    print(f"\n{'='*68}")
    print(f"🏆 球员综合实力排行榜 TOP 30")
    print(f"{'='*68}")
    print(f"{'排名':<4} {'球员姓名':<22} {'位':<2} {'队':<3} "
          f"{'综合mu':<7} {'国家mu':<7} {'俱乐部mu':<7} {'出场':<4}")
    print(f"{'-'*4} {'-'*22} {'-'*2} {'-'*3} "
          f"{'-'*7} {'-'*7} {'-'*7} {'-'*4}")

    for i, e in enumerate(leaderboard[:30], 1):
        nt_tag = f"{e['nt_mu']:<7}" if e['has_nt'] else "  N/A  "
        cl_tag = f"{e['cl_mu']:<7}" if e['has_cl'] else "  N/A  "
        print(f"{i:<4} {e['name']:<22} {e['position']:<2} {e['team']:<3} "
              f"{e['combined_mu']:<7} {nt_tag} {cl_tag} {e['matches']:<4}")

    # 各位置 TOP 5
    for pos in ["FW", "MF", "DF", "GK"]:
        pos_board = [e for e in leaderboard if e["position"] == pos][:5]
        if pos_board:
            print(f"\n├─ {pos} TOP 5 ────────────────────────────────────")
            for i, e in enumerate(pos_board, 1):
                print(f"  {i}. {e['name']:<20} 综合={e['combined_mu']:<6} "
                      f"国家={e['nt_mu'] if e['has_nt'] else '  N/A':<6} "
                      f"俱乐部={e['cl_mu'] if e['has_cl'] else '  N/A':<6}")

    # CSV 输出
    csv_path = "player_trueskill_ranking.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "排名", "球员姓名", "位置", "球队",
            "综合mu", "综合sigma", "综合保守评分",
            "国家队_mu", "国家队_sigma",
            "俱乐部_mu", "俱乐部_sigma",
            "总出场",
        ])
        w.writeheader()
        for i, e in enumerate(leaderboard, 1):
            w.writerow({
                "排名": i,
                "球员姓名": e["name"],
                "位置": e["position"],
                "球队": e["team"],
                "综合mu": e["combined_mu"],
                "综合sigma": e["combined_sigma"],
                "综合保守评分": e["combined_rating"],
                "国家队_mu": e["nt_mu"] if e["has_nt"] else "",
                "国家队_sigma": e["nt_sigma"] if e["has_nt"] else "",
                "俱乐部_mu": e["cl_mu"] if e["has_cl"] else "",
                "俱乐部_sigma": e["cl_sigma"] if e["has_cl"] else "",
                "总出场": e["matches"],
            })
    print(f"\n📁 完整排行榜已保存至: {csv_path}")
    conn.close()


if __name__ == "__main__":
    main()
