from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from functools import lru_cache
from random import Random

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.entities import CasinoSpin, Subscription, SubscriptionStatus, User
from app.services.happ import days_left
from app.services.marzban import MarzbanClient, to_unix
from app.services.provisioning import _now, get_active_subscription, serialize_subscription_with_devices

import structlog

log = structlog.get_logger(__name__)

# --- Slot layout -----------------------------------------------------------------
# Regular pay symbols (no bonus / no mult)
PAY_SYMBOLS = ("🍒", "🍋", "🔔", "⭐", "💎", "7️⃣", "👑")
BONUS_SYMBOL = "В"  # scatter — 3× triggers free spins
MULT_SYMBOL = "Х"  # only in bonus rounds — each appearance +1×

PAYLINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 4, 8),
    (2, 4, 6),
)

LINE_PAY: dict[str, int] = {
    "🍒": 1,
    "🍋": 2,
    "🔔": 3,
    "⭐": 5,
    "💎": 10,
    "7️⃣": 15,
    "👑": 30,
}

BET_DAYS = 1
MIN_DAYS_TO_PLAY = 2
MAX_WIN_DAYS = 30  # max single-line / regular book
BONUS_ROUNDS = 7
BOOK_COUNT = 20_000
BONUS_BOOK_COUNT = 200  # 1 in 100
TARGET_RETURN_DAYS = 19_200  # RTP 96% over full book cycle
BOOK_SEED = 20260812_04

# Regular (non-bonus) book win amounts — sum = 17010 across 19800 books
WIN_BOOK_COUNTS: tuple[tuple[int, int], ...] = (
    (30, 30),  # 900
    (15, 60),  # 900
    (10, 150),  # 1500
    (5, 300),  # 1500
    (3, 600),  # 1800
    (2, 1200),  # 2400
    (1, 8010),  # 8010
)

# Bonus books (200): total days credited for trigger + 7 free spins — sum = 2190
BONUS_WIN_COUNTS: tuple[tuple[int, int], ...] = (
    (25, 10),  # 250
    (20, 20),  # 400
    (15, 30),  # 450
    (12, 40),  # 480
    (8, 50),  # 400
    (5, 30),  # 150
    (3, 20),  # 60
)


@dataclass(frozen=True)
class BonusRound:
    grid: tuple[str, ...]
    winning_lines: tuple[int, ...]
    base_win: int
    x_hit: bool
    multiplier: int
    win_days: int

    def as_dict(self) -> dict:
        return {
            "grid": list(self.grid),
            "winning_lines": list(self.winning_lines),
            "base_win": self.base_win,
            "x_hit": self.x_hit,
            "multiplier": self.multiplier,
            "win_days": self.win_days,
        }


@dataclass(frozen=True)
class Book:
    """One pre-rolled book: pattern + locked payout (bonus = 1 spin for RTP)."""

    index: int
    win_days: int
    grid: tuple[str, ...]
    winning_lines: tuple[int, ...]
    is_bonus: bool = False
    bonus_rounds: tuple[BonusRound, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SpinResult:
    ok: bool
    message: str
    bet_days: int
    win_days: int
    net_days: int
    grid: list[str]
    winning_lines: list[int]
    book_index: int | None
    days_left: int | None
    subscription: dict | None
    is_bonus: bool = False
    bonus_rounds: list[dict] = field(default_factory=list)


def _scrub_pay_lines(cells: list[str], rng: Random, protect: set[int] | None = None) -> None:
    protect = protect or set()
    for a, b, c in PAYLINES:
        if cells[a] == cells[b] == cells[c] and cells[a] in LINE_PAY:
            alt = [s for s in PAY_SYMBOLS if s != cells[a]]
            for pos in (c, b, a):
                if pos not in protect:
                    cells[pos] = rng.choice(alt)
                    break


def _place_scatters(
    cells: list[str],
    count: int,
    rng: Random,
    *,
    forbid: set[int] | None = None,
) -> None:
    """Place scatters with at most one «В» per reel (column)."""
    if count <= 0:
        return
    forbid = forbid or set()
    cols = [0, 1, 2]
    rng.shuffle(cols)
    placed = 0
    for col in cols:
        if placed >= count:
            break
        # Already has a scatter on this reel — skip
        if any(cells[row * 3 + col] == BONUS_SYMBOL for row in range(3)):
            continue
        rows = [row for row in range(3) if (row * 3 + col) not in forbid]
        if not rows:
            continue
        cells[rng.choice(rows) * 3 + col] = BONUS_SYMBOL
        placed += 1


def _scatters_per_reel_ok(grid: list[str] | tuple[str, ...]) -> bool:
    for col in range(3):
        n = sum(1 for row in range(3) if grid[row * 3 + col] == BONUS_SYMBOL)
        if n > 1:
            return False
    return True


def _count_symbol(grid: list[str] | tuple[str, ...], symbol: str) -> int:
    return sum(1 for c in grid if c == symbol)


def _fill_loss_grid(rng: Random) -> tuple[list[str], list[int]]:
    cells = [rng.choice(PAY_SYMBOLS) for _ in range(9)]
    _scrub_pay_lines(cells, rng)
    # 0–2 scatters, never 3, max one per reel
    scatter_n = rng.choice([0, 0, 0, 0, 1, 1, 2])
    if scatter_n:
        _place_scatters(cells, scatter_n, rng)
        _scrub_pay_lines(cells, rng)
        # Scrub must not stack scatters on one reel
        assert _scatters_per_reel_ok(cells)
    return cells, []


def _fill_win_grid(payout: int, rng: Random) -> tuple[list[str], list[int]]:
    cells = [rng.choice(PAY_SYMBOLS) for _ in range(9)]
    symbol = next((s for s, pay in LINE_PAY.items() if pay == payout), None)
    if symbol is None:
        symbol = min(LINE_PAY.items(), key=lambda kv: abs(kv[1] - payout))[0]

    line_idx = rng.randrange(len(PAYLINES))
    a, b, c = PAYLINES[line_idx]
    cells[a] = cells[b] = cells[c] = symbol
    winning_lines = [line_idx]
    _scrub_pay_lines(cells, rng, protect={a, b, c})

    # Optional 1–2 scatters off the winning line, still ≤1 per reel
    scatter_n = rng.choice([0, 0, 0, 1, 1, 2])
    if scatter_n:
        _place_scatters(cells, scatter_n, rng, forbid={a, b, c})
        _scrub_pay_lines(cells, rng, protect={a, b, c})
        assert _scatters_per_reel_ok(cells)
    return cells, winning_lines


def _fill_bonus_trigger(rng: Random) -> tuple[list[str], list[int]]:
    """Trigger spin: exactly one «В» on each reel (3 total), no Х, no paying lines."""
    cells = [rng.choice(PAY_SYMBOLS) for _ in range(9)]
    for col in range(3):
        row = rng.randrange(3)
        cells[row * 3 + col] = BONUS_SYMBOL
    _scrub_pay_lines(cells, rng)
    # Restore exactly one scatter per reel after scrub
    for col in range(3):
        idxs = [row * 3 + col for row in range(3)]
        have = [i for i in idxs if cells[i] == BONUS_SYMBOL]
        if len(have) == 1:
            continue
        for i in have:
            cells[i] = rng.choice(PAY_SYMBOLS)
        cells[rng.choice(idxs)] = BONUS_SYMBOL
    _scrub_pay_lines(cells, rng, protect={i for i, s in enumerate(cells) if s == BONUS_SYMBOL})
    # Final enforce
    for col in range(3):
        idxs = [row * 3 + col for row in range(3)]
        have = [i for i in idxs if cells[i] == BONUS_SYMBOL]
        if len(have) != 1:
            for i in idxs:
                cells[i] = rng.choice(PAY_SYMBOLS) if cells[i] == BONUS_SYMBOL else cells[i]
            cells[rng.choice(idxs)] = BONUS_SYMBOL
    assert _count_symbol(cells, BONUS_SYMBOL) == 3
    assert _scatters_per_reel_ok(cells)
    assert MULT_SYMBOL not in cells
    return cells, []


def _eval_line_win(cells: list[str]) -> tuple[int, list[int]]:
    """First matching 3-of-a-kind payline (pay symbols only)."""
    for i, (a, b, c) in enumerate(PAYLINES):
        if cells[a] == cells[b] == cells[c] and cells[a] in LINE_PAY:
            return LINE_PAY[cells[a]], [i]
    return 0, []


def _fill_bonus_round_grid(
    rng: Random,
    *,
    want_x: bool,
    want_base: int,
) -> tuple[list[str], list[int], int, bool]:
    """Build one free-spin grid: no В; optional Х; optional line win = want_base."""
    cells = [rng.choice(PAY_SYMBOLS) for _ in range(9)]
    x_hit = False
    if want_x:
        pos = rng.randrange(9)
        cells[pos] = MULT_SYMBOL
        x_hit = True

    winning_lines: list[int] = []
    base = 0
    if want_base > 0:
        symbol = next((s for s, pay in LINE_PAY.items() if pay == want_base), None)
        if symbol is None:
            # pick closest allowed pay and accept — caller should pass valid pays
            symbol = min(LINE_PAY.items(), key=lambda kv: abs(kv[1] - want_base))[0]
            want_base = LINE_PAY[symbol]
        line_idx = rng.randrange(len(PAYLINES))
        a, b, c = PAYLINES[line_idx]
        # Don't overwrite Х if it sits on the line — move Х
        if want_x and any(cells[p] == MULT_SYMBOL for p in (a, b, c)):
            for i in range(9):
                if cells[i] == MULT_SYMBOL:
                    cells[i] = rng.choice(PAY_SYMBOLS)
            free = [i for i in range(9) if i not in (a, b, c)]
            cells[rng.choice(free)] = MULT_SYMBOL
        cells[a] = cells[b] = cells[c] = symbol
        winning_lines = [line_idx]
        base = want_base
        protect = {a, b, c}
        if want_x:
            protect |= {i for i, s in enumerate(cells) if s == MULT_SYMBOL}
        _scrub_pay_lines(cells, rng, protect=protect)
    else:
        protect = {i for i, s in enumerate(cells) if s == MULT_SYMBOL}
        _scrub_pay_lines(cells, rng, protect=protect)

    assert BONUS_SYMBOL not in cells
    assert (MULT_SYMBOL in cells) == x_hit
    return cells, winning_lines, base, x_hit


def _solve_honest_bases(mults: list[int], target: int, rng: Random) -> list[int] | None:
    """
    Pick LINE_PAY bases (or 0) so sum(base[i]*mults[i]) == target exactly.
    Returns bases or None if unreachable with this multiplier path.
    """
    valid = [0, *sorted(LINE_PAY.values())]
    bases = [0] * len(mults)

    # Greedy fill toward target with random order bias
    order = list(range(len(mults)))
    rng.shuffle(order)
    remaining = target
    for pos, i in enumerate(order):
        m = mults[i]
        last = pos == len(order) - 1
        if last:
            # Must finish exactly
            if remaining == 0:
                bases[i] = 0
                continue
            if remaining % m == 0 and (remaining // m) in LINE_PAY.values():
                bases[i] = remaining // m
                remaining = 0
                continue
            return None
        # leave room for later rounds
        max_here = remaining
        choices = [b for b in valid if b * m <= max_here]
        if not choices:
            bases[i] = 0
            continue
        # prefer spreading: often zero, else near share
        if rng.random() < 0.35:
            bases[i] = 0
        else:
            share = remaining / max(1, len(order) - pos)
            bases[i] = min(choices, key=lambda b: abs(b * m - share))
        remaining -= bases[i] * m

    if remaining != 0:
        return None
    if sum(b * m for b, m in zip(bases, mults)) != target:
        return None
    return bases


def _build_bonus_book_body(total: int, rng: Random) -> tuple[list[str], list[int], tuple[BonusRound, ...]]:
    """
    Trigger (one «В» per reel) + 7 free spins.
    Every credited day is exactly base_win × multiplier (no ghost top-ups).
    """
    trigger, trigger_lines = _fill_bonus_trigger(rng)

    bases: list[int] | None = None
    x_flags: list[bool] = []
    mults_after: list[int] = []

    for _attempt in range(80):
        x_flags = []
        mult = 1
        mults_after = []
        for i in range(BONUS_ROUNDS):
            want_x = rng.random() < (0.2 + 0.05 * i) and mult < 8
            if want_x:
                mult += 1
            x_flags.append(want_x)
            mults_after.append(mult)
        bases = _solve_honest_bases(mults_after, total, rng)
        if bases is not None:
            break
    else:
        # Guaranteed reachable path: no X, pack pays that sum to total
        x_flags = [False] * BONUS_ROUNDS
        mults_after = [1] * BONUS_ROUNDS
        bases = _solve_honest_bases(mults_after, total, rng)
        if bases is None:
            # Last resort: put total into one cherry-stacked path using only valid pays
            # by splitting total into sum of LINE_PAY values across rounds (mult=1)
            valid = sorted(LINE_PAY.values(), reverse=True)
            bases = [0] * BONUS_ROUNDS
            rem = total
            for i in range(BONUS_ROUNDS):
                for v in valid:
                    if v <= rem:
                        bases[i] = v
                        rem -= v
                        break
            if rem != 0:
                raise RuntimeError(f"Cannot build honest bonus body for total={total}")

    rounds: list[BonusRound] = []
    for i in range(BONUS_ROUNDS):
        m = mults_after[i]
        base = bases[i]
        credited = base * m
        grid, lines, base_out, _x = _fill_bonus_round_grid(
            rng, want_x=x_flags[i], want_base=base if base in LINE_PAY.values() else 0
        )
        # Grid builder must return the requested base
        if base_out != base:
            # rebuild once more strictly
            grid, lines, base_out, _x = _fill_bonus_round_grid(
                rng, want_x=x_flags[i], want_base=base if base > 0 else 0
            )
        assert base_out == base or (base == 0 and base_out == 0)
        rounds.append(
            BonusRound(
                grid=tuple(grid),
                winning_lines=tuple(lines),
                base_win=base_out,
                x_hit=x_flags[i],
                multiplier=m,
                win_days=base_out * m,
            )
        )

    assert sum(r.win_days for r in rounds) == total
    assert all(r.win_days == r.base_win * r.multiplier for r in rounds)
    assert len(rounds) == BONUS_ROUNDS
    return trigger, trigger_lines, tuple(rounds)


def _build_books(seed: int = BOOK_SEED) -> tuple[Book, ...]:
    regular_wins: list[int] = []
    for amount, count in WIN_BOOK_COUNTS:
        regular_wins.extend([amount] * count)
    regular_slots = BOOK_COUNT - BONUS_BOOK_COUNT
    zero_count = regular_slots - len(regular_wins)
    if zero_count < 0:
        raise RuntimeError("WIN_BOOK_COUNTS exceed regular book slots")
    regular_wins.extend([0] * zero_count)

    bonus_wins: list[int] = []
    for amount, count in BONUS_WIN_COUNTS:
        bonus_wins.extend([amount] * count)
    if len(bonus_wins) != BONUS_BOOK_COUNT:
        raise RuntimeError("BONUS_WIN_COUNTS must sum to BONUS_BOOK_COUNT")

    assert len(regular_wins) + len(bonus_wins) == BOOK_COUNT
    assert sum(regular_wins) + sum(bonus_wins) == TARGET_RETURN_DAYS

    rng = Random(seed)
    # Build typed list then shuffle
    specs: list[tuple[str, int]] = [("regular", w) for w in regular_wins] + [
        ("bonus", w) for w in bonus_wins
    ]
    rng.shuffle(specs)

    books: list[Book] = []
    for idx, (kind, win) in enumerate(specs):
        local = Random(seed * 1_000_003 + idx)
        if kind == "bonus":
            grid, lines, rounds = _build_bonus_book_body(win, local)
            books.append(
                Book(
                    index=idx,
                    win_days=win,
                    grid=tuple(grid),
                    winning_lines=tuple(lines),
                    is_bonus=True,
                    bonus_rounds=rounds,
                )
            )
        elif win <= 0:
            grid, lines = _fill_loss_grid(local)
            books.append(
                Book(index=idx, win_days=0, grid=tuple(grid), winning_lines=tuple(lines))
            )
        else:
            grid, lines = _fill_win_grid(win, local)
            books.append(
                Book(index=idx, win_days=win, grid=tuple(grid), winning_lines=tuple(lines))
            )
    return tuple(books)


@lru_cache(maxsize=1)
def get_books() -> tuple[Book, ...]:
    books = _build_books()
    assert len(books) == BOOK_COUNT
    assert sum(b.win_days for b in books) == TARGET_RETURN_DAYS
    assert sum(1 for b in books if b.is_bonus) == BONUS_BOOK_COUNT
    assert max((b.win_days for b in books if not b.is_bonus), default=0) <= MAX_WIN_DAYS
    for b in books:
        assert _scatters_per_reel_ok(b.grid)
        if b.is_bonus:
            assert len(b.bonus_rounds) == BONUS_ROUNDS
            assert _count_symbol(b.grid, BONUS_SYMBOL) == 3
            assert MULT_SYMBOL not in b.grid
            assert sum(r.win_days for r in b.bonus_rounds) == b.win_days
            for r in b.bonus_rounds:
                assert BONUS_SYMBOL not in r.grid
                assert r.win_days >= 0
                assert r.win_days == r.base_win * r.multiplier
                if r.x_hit:
                    assert MULT_SYMBOL in r.grid
                else:
                    assert MULT_SYMBOL not in r.grid
                if r.base_win > 0:
                    assert r.winning_lines
                else:
                    assert not r.winning_lines or r.win_days == 0
        else:
            assert _count_symbol(b.grid, BONUS_SYMBOL) < 3
            assert MULT_SYMBOL not in b.grid
    return books


def books_rtp() -> float:
    return TARGET_RETURN_DAYS / (BOOK_COUNT * BET_DAYS)


def paytable_public() -> list[dict]:
    rows = [{"symbol": s, "pay": LINE_PAY[s]} for s in PAY_SYMBOLS]
    rows.append({"symbol": BONUS_SYMBOL, "pay": 0, "note": "bonus"})
    rows.append({"symbol": MULT_SYMBOL, "pay": 0, "note": "mult"})
    return rows


def pick_book(rng: Random | None = None) -> Book:
    books = get_books()
    if rng is None:
        return books[secrets.randbelow(len(books))]
    return books[rng.randrange(len(books))]


def casino_eligible(sub: Subscription | None) -> tuple[bool, str]:
    if not sub:
        return False, "Нужна активная подписка."
    if sub.traffic_limit_gb is not None:
        return False, "Казино доступно только при безлимитном трафике (вечный тариф)."
    left = days_left(sub.ends_at)
    if left < MIN_DAYS_TO_PLAY:
        return False, f"Нужно минимум {MIN_DAYS_TO_PLAY} дня подписки, чтобы поставить {BET_DAYS} день."
    return True, "OK"


async def _sync_expire(sub: Subscription, settings: Settings) -> None:
    if not sub.marzban_username:
        return
    try:
        marzban = MarzbanClient(settings)
        data_limit = int(sub.traffic_limit_gb * 1024**3) if sub.traffic_limit_gb else 0
        status = "active" if sub.status in {SubscriptionStatus.active, SubscriptionStatus.trial} else "disabled"
        await marzban.modify_user(
            sub.marzban_username,
            expire_ts=to_unix(sub.ends_at),
            status=status,
            data_limit_bytes=data_limit,
        )
    except Exception as exc:  # noqa: BLE001 — casino must not 500 if Marzban is down
        log.warning("casino_marzban_sync_failed", username=sub.marzban_username, error=str(exc))


async def spin_casino(
    db: AsyncSession,
    *,
    user: User,
    settings: Settings | None = None,
    seed: int | None = None,
) -> SpinResult:
    settings = settings or get_settings()
    if not settings.casino_enabled:
        return SpinResult(
            ok=False,
            message="Казино временно выключено.",
            bet_days=BET_DAYS,
            win_days=0,
            net_days=0,
            grid=[],
            winning_lines=[],
            book_index=None,
            days_left=None,
            subscription=None,
        )

    sub = await get_active_subscription(db, user.id)
    ok, msg = casino_eligible(sub)
    if not ok or sub is None:
        return SpinResult(
            ok=False,
            message=msg,
            bet_days=BET_DAYS,
            win_days=0,
            net_days=0,
            grid=[],
            winning_lines=[],
            book_index=None,
            days_left=days_left(sub.ends_at) if sub else None,
            subscription=await serialize_subscription_with_devices(db, sub, settings) if sub else None,
        )

    rng = Random(seed) if seed is not None else None
    book = pick_book(rng)
    payout = book.win_days
    grid = list(book.grid)
    winning_lines = list(book.winning_lines)
    bonus_payload = [r.as_dict() for r in book.bonus_rounds] if book.is_bonus else []

    now = _now()
    sub.ends_at = sub.ends_at - timedelta(days=BET_DAYS)
    if payout > 0:
        base = sub.ends_at if sub.ends_at > now else now
        sub.ends_at = base + timedelta(days=payout)
    if sub.ends_at <= now:
        sub.status = SubscriptionStatus.expired

    net = -BET_DAYS + payout
    spin = CasinoSpin(
        user_id=user.id,
        subscription_id=sub.id,
        bet_days=BET_DAYS,
        win_days=payout,
        net_days=net,
        grid=grid,
        winning_lines=winning_lines,
    )
    db.add(spin)
    await _sync_expire(sub, settings)
    await db.commit()
    await db.refresh(sub)

    sub_data = await serialize_subscription_with_devices(db, sub, settings, include_devices=True)
    return SpinResult(
        ok=True,
        message="OK",
        bet_days=BET_DAYS,
        win_days=payout,
        net_days=net,
        grid=grid,
        winning_lines=winning_lines,
        book_index=book.index,
        days_left=days_left(sub.ends_at),
        subscription=sub_data,
        is_bonus=book.is_bonus,
        bonus_rounds=bonus_payload,
    )
