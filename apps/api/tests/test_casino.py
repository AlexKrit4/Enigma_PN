from __future__ import annotations

from app.services.casino import PAYOUT_WEIGHTS, _grid_for_payout, _pick_payout, expected_rtp
import random


def test_casino_rtp_target() -> None:
    assert abs(expected_rtp() - 0.96) < 1e-9


def test_casino_empirical_rtp() -> None:
    rng = random.Random(42)
    n = 100_000
    total = sum(_pick_payout(rng) for _ in range(n))
    empirical = total / n
    assert 0.94 <= empirical <= 0.98


def test_loss_grid_has_no_three_kind() -> None:
    rng = random.Random(7)
    for _ in range(200):
        grid, lines = _grid_for_payout(0, rng)
        assert lines == []
        assert len(grid) == 9


def test_win_grid_has_matching_line() -> None:
    rng = random.Random(9)
    for payout in (1, 2, 3, 5, 10):
        grid, lines = _grid_for_payout(payout, rng)
        assert lines
        a, b, c = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 4, 8), (2, 4, 6)][lines[0]]
        assert grid[a] == grid[b] == grid[c]


def test_weights_sum_to_one() -> None:
    assert abs(sum(w for _, w in PAYOUT_WEIGHTS) - 1.0) < 1e-9
