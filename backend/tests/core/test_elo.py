"""Tests for Elo rating system functions."""

import pytest

from app.core.elo import (
    _parse_market_value,
    composite_rating,
    expected_score,
    update_elo,
)


class TestParseMarketValue:
    def test_parses_wan(self):
        assert _parse_market_value("1500万") == 15_000_000

    def test_parses_small_wan(self):
        assert _parse_market_value("25万") == 250_000

    def test_parses_yi(self):
        assert _parse_market_value("1亿") == 100_000_000

    def test_parses_decimal_yi(self):
        assert _parse_market_value("1.8亿") == 180_000_000

    def test_returns_zero_for_empty(self):
        assert _parse_market_value("") == 0.0
        assert _parse_market_value(None) == 0.0

    def test_parses_plain_number(self):
        assert _parse_market_value("5000") == 5000.0


class TestExpectedScore:
    def test_equal_elo_returns_half(self):
        assert expected_score(1500, 1500) == 0.5

    def test_stronger_team_has_higher_score(self):
        assert expected_score(1700, 1500) > 0.5

    def test_weaker_team_has_lower_score(self):
        assert expected_score(1500, 1700) < 0.5

    def test_large_gap_approaches_one(self):
        assert expected_score(2200, 1200) > 0.99


class TestUpdateElo:
    def test_winner_gains_rating(self):
        new_a, new_b = update_elo(1500, 1500, 1.0)
        assert new_a > 1500
        assert new_b < 1500

    def test_draw_benefits_lower_rated(self):
        new_a, new_b = update_elo(1600, 1400, 0.5)
        # Both move toward each other equally on draw
        assert 1600 - new_a > 0
        assert new_b - 1400 > 0
        assert 1600 - new_a == new_b - 1400

    def test_upset_causes_big_swing(self):
        new_a, new_b = update_elo(1200, 2000, 1.0)
        assert new_a > 1200
        assert new_b < 2000
        # Large upset means big absolute delta for both sides
        assert new_a - 1200 > 15
        assert 2000 - new_b > 15

    def test_custom_k_factor(self):
        default_new_a, _ = update_elo(1500, 1500, 1.0)
        higher_new_a, _ = update_elo(1500, 1500, 1.0, k=40.0)
        assert higher_new_a - 1500 > default_new_a - 1500


class TestCompositeRating:
    def test_defaults_to_elo_weight(self):
        rating = composite_rating(1500)
        assert rating == 0.6 * 1500 + 0.3 * 1500 + 0.1 * 1000

    def test_dongqiudi_strength_raises_rating(self):
        with_strength = composite_rating(1500, dongqiudi_strength=85.0)
        without = composite_rating(1500)
        assert with_strength > without

    def test_market_value_raises_rating(self):
        with_value = composite_rating(1500, market_value_eur=1_000_000_000)
        without = composite_rating(1500)
        assert with_value > without

    def test_custom_weights(self):
        rating = composite_rating(1500, w_elo=1.0, w_strength=0.0, w_value=0.0)
        assert rating == 1500
