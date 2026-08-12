from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from random import Random

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.entities import CasinoSpin, Subscription, SubscriptionStatus, User
from app.services.happ import days_left
from app.services.marzban import MarzbanClient, to_unix
from app.services.provisioning import _now, get_active_subscription, serialize_subscription_with_devices

# --- Slot layout -----------------------------------------------------------------
SYMBOLS = ("🍒", "🍋", "🔔", "⭐", "💎", "7️⃣", "👑")

PAYLINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 4, 8),
    (2, 4, 6),
)

# Visual paytable: 3-of-a-kind on a line → days returned (bet is always 1 day)
LINE_PAY: dict[str, int] = {
    "🍒": 1,
    "🍋": 2,
    "🔔": 3,
    "⭐": 5,
    "💎": 10,
    "7️⃣": 15,
    "👑": 30,  # max win = 1 month
}

BET_DAYS = 1
MIN_DAYS_TO_PLAY = 2
MAX_WIN_DAYS = 30
BOOK_COUNT = 10_000
TARGET_RETURN_DAYS = 9_600  # RTP 96% over full book cycle
BOOK_SEED = 20260812

# How many books of each win amount (sum of wins * count = 9600, total books = 10000)
WIN_BOOK_COUNTS: tuple[tuple[int, int], ...] = (
    (30, 20),  # 600
    (15, 40),  # 600
    (10, 100),  # 1000
    (5, 200),  # 1000
    (3, 400),  # 1200
    (2, 800),  # 1600
    (1, 3600),  # 3600
)
# zeros fill the rest: 10000 - 5160 = 4840


@dataclass(frozen=True)
class Book:
    """One pre-rolled spin: symbol pattern + locked payout."""

    index: int
    win_days: int
    grid: tuple[str, ...]
    winning_lines: tuple[int, ...]


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


def _fill_loss_grid(rng: Random) -> tuple[list[str], list[int]]:
    cells = [rng.choice(SYMBOLS) for _ in range(9)]
    for a, b, c in PAYLINES:
        if cells[a] == cells[b] == cells[c]:
            alt = [s for s in SYMBOLS if s != cells[a]]
            cells[c] = rng.choice(alt)
    return cells, []


def _fill_win_grid(payout: int, rng: Random) -> tuple[list[str], list[int]]:
    cells = [rng.choice(SYMBOLS) for _ in range(9)]
    symbol = next((s for s, pay in LINE_PAY.items() if pay == payout), None)
    if symbol is None:
        # Fallback: crown for max-ish
        symbol = "👑" if payout >= MAX_WIN_DAYS else "🍒"
        payout_sym = LINE_PAY[symbol]
        if payout_sym != payout and payout <= MAX_WIN_DAYS:
            # still show closest visual
            symbol = min(LINE_PAY.items(), key=lambda kv: abs(kv[1] - payout))[0]

    line_idx = rng.randrange(len(PAYLINES))
    a, b, c = PAYLINES[line_idx]
    cells[a] = cells[b] = cells[c] = symbol
    winning_lines = [line_idx]

    for i, (x, y, z) in enumerate(PAYLINES):
        if i == line_idx:
            continue
        if cells[x] == cells[y] == cells[z]:
            alt = [s for s in SYMBOLS if s != cells[x]]
            for pos in (z, y, x):
                if pos not in (a, b, c):
                    cells[pos] = rng.choice(alt)
                    break
            else:
                cells[z] = rng.choice(alt)
    return cells, winning_lines


def _build_books(seed: int = BOOK_SEED) -> tuple[Book, ...]:
    win_list: list[int] = []
    for amount, count in WIN_BOOK_COUNTS:
        win_list.extend([amount] * count)
    zero_count = BOOK_COUNT - len(win_list)
    if zero_count < 0:
        raise RuntimeError("WIN_BOOK_COUNTS exceed BOOK_COUNT")
    win_list.extend([0] * zero_count)
    assert len(win_list) == BOOK_COUNT
    assert sum(win_list) == TARGET_RETURN_DAYS

    rng = Random(seed)
    rng.shuffle(win_list)

    books: list[Book] = []
    for idx, win in enumerate(win_list):
        # Per-book RNG derived from master seed + index for stable grids
        local = Random(seed * 1_000_003 + idx)
        if win <= 0:
            grid, lines = _fill_loss_grid(local)
        else:
            grid, lines = _fill_win_grid(win, local)
        books.append(
            Book(
                index=idx,
                win_days=win,
                grid=tuple(grid),
                winning_lines=tuple(lines),
            )
        )
    return tuple(books)


@lru_cache(maxsize=1)
def get_books() -> tuple[Book, ...]:
    books = _build_books()
    assert len(books) == BOOK_COUNT
    assert sum(b.win_days for b in books) == TARGET_RETURN_DAYS
    assert max(b.win_days for b in books) <= MAX_WIN_DAYS
    return books


def books_rtp() -> float:
    return TARGET_RETURN_DAYS / (BOOK_COUNT * BET_DAYS)


def paytable_public() -> list[dict]:
    return [{"symbol": s, "pay": LINE_PAY[s]} for s in SYMBOLS]


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
    marzban = MarzbanClient(settings)
    data_limit = int(sub.traffic_limit_gb * 1024**3) if sub.traffic_limit_gb else 0
    status = "active" if sub.status in {SubscriptionStatus.active, SubscriptionStatus.trial} else "disabled"
    await marzban.modify_user(
        sub.marzban_username,
        expire_ts=to_unix(sub.ends_at),
        status=status,
        data_limit_bytes=data_limit,
    )


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
    )
