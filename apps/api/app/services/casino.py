from __future__ import annotations

import random
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.entities import CasinoSpin, Subscription, SubscriptionStatus, User
from app.services.happ import days_left
from app.services.marzban import MarzbanClient, to_unix
from app.services.provisioning import _now, get_active_subscription, serialize_subscription_with_devices

# 3x3 symbols (index used on reels)
SYMBOLS = ("🍒", "🍋", "🔔", "⭐", "💎")

# 5 paylines on 3x3 grid (row-major indices 0..8)
PAYLINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2),  # top row
    (3, 4, 5),  # mid row
    (6, 7, 8),  # bottom row
    (0, 4, 8),  # diag \
    (2, 4, 6),  # diag /
)

# Paytable: 3-of-a-kind payout in days for one line (bet is always 1 day total)
LINE_PAY: dict[str, int] = {
    "🍒": 1,
    "🍋": 2,
    "🔔": 3,
    "⭐": 5,
    "💎": 10,
}

# Outcome-first distribution: E[payout days] = 0.96 (RTP 96% on 1-day bet)
# payout → probability
PAYOUT_WEIGHTS: tuple[tuple[int, float], ...] = (
    (0, 0.385),
    (1, 0.420),
    (2, 0.120),
    (3, 0.050),
    (5, 0.020),
    (10, 0.005),
)

BET_DAYS = 1
MIN_DAYS_TO_PLAY = 2  # after betting 1 day, at least 1 day must remain


@dataclass(frozen=True)
class SpinResult:
    ok: bool
    message: str
    bet_days: int
    win_days: int
    net_days: int
    grid: list[str]
    winning_lines: list[int]
    days_left: int | None
    subscription: dict | None


def expected_rtp(weights: Sequence[tuple[int, float]] = PAYOUT_WEIGHTS) -> float:
    return sum(payout * weight for payout, weight in weights)


def _pick_payout(rng: random.Random) -> int:
    roll = rng.random()
    acc = 0.0
    for payout, weight in PAYOUT_WEIGHTS:
        acc += weight
        if roll <= acc:
            return payout
    return 0


def _grid_for_payout(payout: int, rng: random.Random) -> tuple[list[str], list[int]]:
    """Build a 3x3 grid that visually matches the chosen payout."""
    cells = [rng.choice(SYMBOLS) for _ in range(9)]
    winning_lines: list[int] = []

    if payout <= 0:
        # Ensure no three-in-a-row on any payline
        for a, b, c in PAYLINES:
            if cells[a] == cells[b] == cells[c]:
                alt = [s for s in SYMBOLS if s != cells[a]]
                cells[c] = rng.choice(alt)
        return cells, winning_lines

    # Pick a symbol that pays exactly this amount on one line if possible
    symbol = next((s for s, pay in LINE_PAY.items() if pay == payout), None)
    if symbol is not None:
        line_idx = rng.randrange(len(PAYLINES))
        a, b, c = PAYLINES[line_idx]
        cells[a] = cells[b] = cells[c] = symbol
        winning_lines = [line_idx]
        # Break other accidental lines
        for i, (x, y, z) in enumerate(PAYLINES):
            if i == line_idx:
                continue
            if cells[x] == cells[y] == cells[z]:
                alt = [s for s in SYMBOLS if s != cells[x]]
                # Prefer changing a cell not on the winning line
                for pos in (z, y, x):
                    if pos not in (a, b, c):
                        cells[pos] = rng.choice(alt)
                        break
                else:
                    cells[z] = rng.choice(alt)
        return cells, winning_lines

    # Composite payout (shouldn't happen with current table) — show mid line cherries
    a, b, c = PAYLINES[1]
    cells[a] = cells[b] = cells[c] = "🍒"
    return cells, [1]


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
            days_left=days_left(sub.ends_at) if sub else None,
            subscription=await serialize_subscription_with_devices(db, sub, settings) if sub else None,
        )

    rng = random.Random(seed if seed is not None else secrets.randbits(64))
    payout = _pick_payout(rng)
    grid, winning_lines = _grid_for_payout(payout, rng)

    now = _now()
    # Deduct bet, then credit win
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
        days_left=days_left(sub.ends_at),
        subscription=sub_data,
    )
