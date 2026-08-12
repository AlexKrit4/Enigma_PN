from __future__ import annotations

from collections import Counter

from app.services.casino import (
    BOOK_COUNT,
    LINE_PAY,
    MAX_WIN_DAYS,
    TARGET_RETURN_DAYS,
    WIN_BOOK_COUNTS,
    books_rtp,
    get_books,
    pick_book,
)
from random import Random


def test_books_count_and_rtp() -> None:
    books = get_books()
    assert len(books) == BOOK_COUNT
    assert sum(b.win_days for b in books) == TARGET_RETURN_DAYS
    assert books_rtp() == 0.96
    assert max(b.win_days for b in books) == MAX_WIN_DAYS


def test_books_distribution_matches_table() -> None:
    counts = Counter(b.win_days for b in get_books())
    for amount, expected in WIN_BOOK_COUNTS:
        assert counts[amount] == expected
    expected_zeros = BOOK_COUNT - sum(c for _, c in WIN_BOOK_COUNTS)
    assert counts[0] == expected_zeros


def test_books_grids_consistent() -> None:
    for book in get_books()[::97]:  # sample
        assert len(book.grid) == 9
        if book.win_days == 0:
            assert book.winning_lines == ()
        else:
            assert book.winning_lines
            line = book.winning_lines[0]
            from app.services.casino import PAYLINES

            a, b, c = PAYLINES[line]
            assert book.grid[a] == book.grid[b] == book.grid[c]
            assert LINE_PAY[book.grid[a]] == book.win_days


def test_pick_book_deterministic_with_seed() -> None:
    a = pick_book(Random(1))
    b = pick_book(Random(1))
    assert a.index == b.index
    assert a.grid == b.grid


def test_max_win_capped() -> None:
    assert all(b.win_days <= MAX_WIN_DAYS for b in get_books())
