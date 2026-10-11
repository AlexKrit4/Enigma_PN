from __future__ import annotations

from collections import Counter
from random import Random

from app.services.casino import (
    BONUS_BOOK_COUNT,
    BONUS_ROUNDS,
    BONUS_SYMBOL,
    BONUS_WIN_COUNTS,
    BOOK_COUNT,
    JACKPOT_WIN_DAYS,
    LINE_PAY,
    MAX_WIN_DAYS,
    MULT_SYMBOL,
    PAYLINES,
    TARGET_RETURN_DAYS,
    WIN_BOOK_COUNTS,
    books_rtp,
    get_books,
    pick_book,
    pick_bonus_book,
)


def test_books_count_and_rtp() -> None:
    books = get_books()
    assert len(books) == BOOK_COUNT
    assert sum(b.win_days for b in books) == TARGET_RETURN_DAYS
    assert books_rtp() == 0.96
    assert sum(1 for b in books if b.is_bonus) == BONUS_BOOK_COUNT
    assert BOOK_COUNT // BONUS_BOOK_COUNT == 75
    assert sum(1 for b in books if b.win_days > 0) * 4 == BOOK_COUNT  # 25%


def test_regular_distribution_matches_table() -> None:
    regular = [b for b in get_books() if not b.is_bonus]
    counts = Counter(b.win_days for b in regular)
    for amount, expected in WIN_BOOK_COUNTS:
        assert counts[amount] == expected
    expected_zeros = (BOOK_COUNT - BONUS_BOOK_COUNT) - sum(c for _, c in WIN_BOOK_COUNTS)
    assert counts[0] == expected_zeros


def test_bonus_distribution_matches_table() -> None:
    bonus = [b for b in get_books() if b.is_bonus]
    assert len(bonus) == BONUS_BOOK_COUNT
    counts = Counter(b.win_days for b in bonus)
    for amount, expected in BONUS_WIN_COUNTS:
        assert counts[amount] == expected


def test_jackpot_full_crown_board() -> None:
    jackpots = [b for b in get_books() if not b.is_bonus and b.win_days == JACKPOT_WIN_DAYS]
    assert len(jackpots) == 1
    book = jackpots[0]
    assert book.win_days == 365
    assert all(c == "👑" for c in book.grid)
    assert set(book.winning_lines) == set(range(len(PAYLINES)))
    assert LINE_PAY["👑"] == 73
    assert len(PAYLINES) * LINE_PAY["👑"] == JACKPOT_WIN_DAYS == 365
    assert MAX_WIN_DAYS == JACKPOT_WIN_DAYS == 365


def test_bonus_rounds_structure() -> None:
    for book in (b for b in get_books() if b.is_bonus):
        assert len(book.bonus_rounds) == BONUS_ROUNDS
        assert sum(1 for c in book.grid if c == BONUS_SYMBOL) == 3
        assert MULT_SYMBOL not in book.grid
        assert sum(r.win_days for r in book.bonus_rounds) == book.win_days
        mult = 1
        for r in book.bonus_rounds:
            assert BONUS_SYMBOL not in r.grid
            if r.x_hit:
                assert MULT_SYMBOL in r.grid
                mult += 1
            else:
                assert MULT_SYMBOL not in r.grid
            assert r.multiplier == mult


def test_regular_books_no_trigger_or_mult() -> None:
    for book in (b for b in get_books() if not b.is_bonus):
        assert sum(1 for c in book.grid if c == BONUS_SYMBOL) < 3
        assert MULT_SYMBOL not in book.grid
        assert book.win_days <= MAX_WIN_DAYS
        for col in range(3):
            n = sum(1 for row in range(3) if book.grid[row * 3 + col] == BONUS_SYMBOL)
            assert n <= 1


def test_bonus_trigger_one_scatter_per_reel() -> None:
    for book in (b for b in get_books() if b.is_bonus):
        for col in range(3):
            n = sum(1 for row in range(3) if book.grid[row * 3 + col] == BONUS_SYMBOL)
            assert n == 1


def test_bonus_rounds_honest_payout() -> None:
    for book in (b for b in get_books() if b.is_bonus):
        assert sum(r.win_days for r in book.bonus_rounds) == book.win_days
        for r in book.bonus_rounds:
            assert r.win_days == r.base_win * r.multiplier
            if r.base_win > 0:
                assert r.base_win in LINE_PAY.values()
                assert r.winning_lines
            else:
                assert r.win_days == 0


def test_books_grids_consistent() -> None:
    for book in get_books()[::211]:
        assert len(book.grid) == 9
        if book.is_bonus:
            continue
        if book.win_days == 0:
            assert book.winning_lines == ()
        elif book.win_days == JACKPOT_WIN_DAYS:
            assert all(c == "👑" for c in book.grid)
            assert set(book.winning_lines) == set(range(len(PAYLINES)))
        else:
            assert book.winning_lines
            line = book.winning_lines[0]
            a, b, c = PAYLINES[line]
            assert book.grid[a] == book.grid[b] == book.grid[c]
            assert LINE_PAY[book.grid[a]] == book.win_days


def test_pick_bonus_book_always_bonus() -> None:
    for seed in range(20):
        book = pick_bonus_book(Random(seed))
        assert book.is_bonus
        assert book.bonus_rounds


def test_bonus_buy_constants() -> None:
    from app.services.casino import BONUS_BUY_MULT, GOD_MODE_BUY_MULT, BET_OPTIONS

    assert BONUS_BUY_MULT == 15
    assert GOD_MODE_BUY_MULT == 80
    assert BET_OPTIONS == (1, 2, 3, 5, 10)
    assert BOOK_COUNT // BONUS_BOOK_COUNT == 75


def test_normalize_bet_and_scale() -> None:
    from app.services.casino import normalize_bet_days, scale_bonus_rounds, BonusRound

    assert normalize_bet_days(5) == 5
    try:
        normalize_bet_days(7)
        assert False, "expected ValueError"
    except ValueError:
        pass
    rounds = (
        BonusRound(
            grid=("🍒",) * 9,
            winning_lines=(0,),
            base_win=3,
            x_hit=False,
            multiplier=2,
            win_days=6,
        ),
    )
    scaled = scale_bonus_rounds(rounds, 3)
    assert scaled[0]["base_win"] == 9
    assert scaled[0]["win_days"] == 18


def test_god_mode_pool() -> None:
    from app.services.casino import (
        GOD_MODE_JACKPOT_COUNT,
        GOD_MODE_NEAR_MISS_COUNT,
        JACKPOT_WIN_DAYS,
        get_god_mode_books,
        pick_god_mode_book,
    )

    books = get_god_mode_books()
    assert len(books) == GOD_MODE_NEAR_MISS_COUNT + GOD_MODE_JACKPOT_COUNT == 5
    near = [b for b in books if b.win_days == 0]
    jack = [b for b in books if b.win_days == JACKPOT_WIN_DAYS]
    assert len(near) == 4
    assert len(jack) == 1
    for b in near:
        for row in range(3):
            assert b.grid[row * 3 + 0] == "👑"
            assert b.grid[row * 3 + 1] == "👑"
            assert b.grid[row * 3 + 2] == "🍒"
        assert b.winning_lines == ()
    assert all(c == "👑" for c in jack[0].grid)
    # Uniform pick covers both kinds over many draws
    kinds = {pick_god_mode_book(Random(i)).win_days for i in range(200)}
    assert 0 in kinds and JACKPOT_WIN_DAYS in kinds


def test_pick_book_deterministic_with_seed() -> None:
    a = pick_book(Random(1))
    b = pick_book(Random(1))
    assert a.index == b.index
    assert a.grid == b.grid
    assert a.is_bonus == b.is_bonus
