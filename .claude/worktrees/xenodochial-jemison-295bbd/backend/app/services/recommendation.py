"""Betting recommendation engine.

Calculates expected value (EV), detects value bets, and identifies
discrepancies between system predictions and market odds.
"""

from __future__ import annotations


def implied_probability(odds: float) -> float:
    """Convert decimal odds to implied probability (raw, including margin)."""
    return 1.0 / odds if odds > 0 else 0.0


def remove_margin(probs: dict[str, float]) -> dict[str, float]:
    """Normalize implied probabilities by removing the bookmaker margin."""
    total = sum(probs.values())
    if total <= 0:
        return probs
    return {k: round(v / total, 4) for k, v in probs.items()}


def expected_value(system_prob: float, odds: float) -> float:
    """Calculate expected value per unit bet.

    EV = P_sys × odds - 1
    Positive EV means the bet has value.
    """
    return round(system_prob * odds - 1.0, 4)


def rating_from_ev(ev: float) -> str:
    """Convert EV to a star rating."""
    if ev >= 0.25:
        return "★★★"  # ★★★
    if ev >= 0.15:
        return "★★"
    if ev >= 0.05:
        return "★"
    return ""


class RecommendationEngine:
    def __init__(self, discrepancy_threshold: float = 0.12):
        self.threshold = discrepancy_threshold

    def analyze(
        self,
        system_probs: dict[str, float],
        system_confidence: float,
        odds_data: dict | None,
    ) -> dict:
        """Analyze a match and produce betting recommendations.

        Args:
            system_probs: {"win": 0.42, "draw": 0.26, "lose": 0.32}
            system_confidence: 0.0-1.0
            odds_data: raw output from OddsClient, or None

        Returns:
            dict with recommendations and discrepancy info
        """
        result = {"recommendations": [], "discrepancy": None}

        if not odds_data or not odds_data.get("bookmakers"):
            result["odds_available"] = False
            return result

        result["odds_available"] = True

        # Compute market consensus (average across bookmakers)
        outcome_names = ["win", "draw", "lose"]
        books = odds_data["bookmakers"]

        market_avg = {}
        for outcome in outcome_names:
            prices = []
            for bm in books:
                for o_name, price in bm["outcomes"].items():
                    if outcome == "win" and o_name == odds_data["home_team"]:
                        prices.append(price)
                    elif outcome == "lose" and o_name == odds_data["away_team"]:
                        prices.append(price)
                    elif outcome == "draw" and "draw" in o_name.lower():
                        prices.append(price)
            market_avg[outcome] = round(sum(prices) / len(prices), 2) if prices else 0

        # Compute implied probabilities (after removing margin)
        implied_raw = {outcome: implied_probability(market_avg.get(outcome, 999))
                       for outcome in outcome_names}
        implied_true = remove_margin(implied_raw)

        # Best odds
        best_odds = {}
        for outcome, book_key in [("win", odds_data["home_team"]),
                                   ("draw", "Draw"),
                                   ("lose", odds_data["away_team"])]:
            prices = []
            for bm in books:
                for o_name, price in bm["outcomes"].items():
                    if book_key.lower() in o_name.lower():
                        prices.append((price, bm["name"]))
            if prices:
                best = max(prices, key=lambda x: x[0])
                best_odds[outcome] = best

        result["odds_comparison"] = {
            "provider_count": len(books),
            "market_avg": market_avg,
            "best_odds": {
                k: {"price": v[0], "provider": v[1]} for k, v in best_odds.items()
            },
            "market_implied": implied_true,
        }

        # EV calculation for each outcome
        recommendations = []
        for outcome in outcome_names:
            if outcome not in best_odds:
                continue
            odds = best_odds[outcome][0]
            ev = expected_value(system_probs[outcome], odds)
            rating = rating_from_ev(ev)
            if rating:
                recommendations.append({
                    "outcome": outcome,
                    "odds": odds,
                    "ev": ev,
                    "rating": rating,
                    "system_prob": system_probs[outcome],
                    "market_prob": implied_true.get(outcome, 0),
                })
        result["recommendations"] = sorted(recommendations, key=lambda r: r["ev"], reverse=True)

        # Discrepancy detection
        max_delta = 0.0
        for outcome in outcome_names:
            delta = abs(system_probs[outcome] - implied_true.get(outcome, 0))
            if delta > max_delta:
                max_delta = delta

        if max_delta >= self.threshold and system_confidence >= 0.55:
            result["discrepancy"] = {
                "detected": True,
                "max_delta": round(max_delta, 4),
                "system_confidence": system_confidence,
                "detail": f"System differs from market by {max_delta*100:.1f}%",
            }
        else:
            result["discrepancy"] = {"detected": False}

        return result


recommendation_engine = RecommendationEngine()
