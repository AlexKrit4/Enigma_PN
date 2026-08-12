"use client";

import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";

const PAY_SYMBOLS = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣", "👑"] as const;
const BONUS_SYMBOL = "В";
const MULT_SYMBOL = "Х";

const PAYLINES = [
  [0, 1, 2],
  [3, 4, 5],
  [6, 7, 8],
  [0, 4, 8],
  [2, 4, 6],
];

const CELL = 78;
const VISIBLE = 3;
const GAP = 8;
/** Constant spin speed (cells/sec) — no accel / no ease. */
const SPIN_SPEED = 16;
const SPIN_PAD = [10, 14, 18];
const SPEED_PX = SPIN_SPEED * CELL;
/** Extra travel on reel 3 when reels 1–2 already show «В». */
const ANTICIPATION_SEC = 4;
const TOAST_HOLD_MS = 1800;
const MULT_FLY_MS = 650;

export type BonusRoundView = {
  grid: string[];
  winning_lines: number[];
  base_win: number;
  x_hit: boolean;
  multiplier: number;
  win_days: number;
};

export type WinReveal = {
  baseDays: number;
  multiplier: number;
};

type Props = {
  grid: string[];
  resultGrid: string[] | null;
  winningLines: number[];
  spinning: boolean;
  disabled?: boolean;
  onSpin: () => void;
  onSettled: () => void;
  /** Error / status under the slot (not win/loss copy). */
  message?: string;
  /** Simple win toast inside the slot frame, e.g. "+5 дн." */
  toast?: string | null;
  toastKey?: number;
  onToastDone?: () => void;
  /** Bonus-style reveal: show base, then mult flies in and multiplies (≥2). */
  winReveal?: WinReveal | null;
  winRevealKey?: number;
  onWinRevealDone?: () => void;
  daysLeft?: number | null;
  paytable?: Array<{ symbol: string; pay: number; note?: string }>;
  inBonus?: boolean;
  multiplier?: number;
  bonusSpinsLeft?: number | null;
  bonusTotalDays?: number | null;
  spinLabel?: string;
};

function randFrom(pool: readonly string[]) {
  return pool[Math.floor(Math.random() * pool.length)];
}

function colOf(grid: string[], col: number): [string, string, string] {
  return [grid[col] || "❓", grid[3 + col] || "❓", grid[6 + col] || "❓"];
}

function colHasSymbol(grid: string[], col: number, symbol: string) {
  return [grid[col], grid[3 + col], grid[6 + col]].includes(symbol);
}

function colAllSymbol(grid: string[], col: number, symbol: string) {
  return [grid[col], grid[3 + col], grid[6 + col]].every((s) => s === symbol);
}

function firstSymbolCell(grid: string[], symbol: string): number {
  return grid.findIndex((s) => s === symbol);
}

function buildStripDown(
  lead: [string, string, string],
  finals: [string, string, string] | null,
  pad: number,
  pool: readonly string[]
): string[] {
  const mid = Array.from({ length: pad }, () => randFrom(pool));
  if (!finals) return [...mid, ...lead];
  return [...finals, ...mid, ...lead];
}

function visibleTriple(strip: string[], offset: number): [string, string, string] {
  const start = Math.min(
    Math.max(0, Math.floor(offset / CELL)),
    Math.max(0, strip.length - VISIBLE)
  );
  return [
    strip[start] || "❓",
    strip[start + 1] || "❓",
    strip[start + 2] || "❓",
  ];
}

function cellCenter(idx: number, colW: number): { x: number; y: number } {
  const col = idx % 3;
  const row = Math.floor(idx / 3);
  return {
    x: col * (colW + GAP) + colW / 2,
    y: row * CELL + CELL / 2,
  };
}

export function SlotMachine({
  grid,
  resultGrid,
  winningLines,
  spinning,
  disabled,
  onSpin,
  onSettled,
  message,
  toast,
  toastKey = 0,
  onToastDone,
  winReveal,
  winRevealKey = 0,
  onWinRevealDone,
  daysLeft,
  paytable,
  inBonus,
  multiplier = 1,
  bonusSpinsLeft,
  bonusTotalDays,
  spinLabel,
}: Props) {
  const pool = useMemo(
    () => (inBonus ? [...PAY_SYMBOLS, MULT_SYMBOL] : [...PAY_SYMBOLS, BONUS_SYMBOL]),
    [inBonus]
  );

  const [strips, setStrips] = useState<string[][]>(() => [
    ["❓", "❓", "❓"],
    ["❓", "❓", "❓"],
    ["❓", "❓", "❓"],
  ]);
  const [offsets, setOffsets] = useState<number[]>([0, 0, 0]);
  const [landed, setLanded] = useState<[boolean, boolean, boolean]>([true, true, true]);
  const [showWin, setShowWin] = useState(false);
  const [colW, setColW] = useState(CELL);
  const [anticipate, setAnticipate] = useState(false);
  const [localMult, setLocalMult] = useState(multiplier);
  const [fly, setFly] = useState<{
    kind: "x" | "mult";
    label: string;
    x: number;
    y: number;
    tx: number;
    ty: number;
    active: boolean;
  } | null>(null);
  const [toastPhase, setToastPhase] = useState<"off" | "in" | "hold" | "out">("off");
  const [toastText, setToastText] = useState("");
  const [toastPop, setToastPop] = useState(false);
  const [multLaunching, setMultLaunching] = useState(false);

  const stripsRef = useRef(strips);
  const offsetsRef = useRef(offsets);
  const gridRef = useRef(grid);
  const settledOnce = useRef(false);
  const windowRef = useRef<HTMLDivElement | null>(null);
  const frameRef = useRef<HTMLDivElement | null>(null);
  const multRef = useRef<HTMLSpanElement | null>(null);
  const toastRef = useRef<HTMLDivElement | null>(null);
  const revealBusy = useRef(false);
  const onWinRevealDoneRef = useRef(onWinRevealDone);
  onWinRevealDoneRef.current = onWinRevealDone;

  useEffect(() => {
    stripsRef.current = strips;
  }, [strips]);
  useEffect(() => {
    offsetsRef.current = offsets;
  }, [offsets]);
  useEffect(() => {
    gridRef.current = grid;
  }, [grid]);
  useEffect(() => {
    if (!fly?.active) setLocalMult(multiplier);
  }, [multiplier, fly?.active]);

  useEffect(() => {
    const el = windowRef.current;
    if (!el) return;
    const measure = () => {
      const w = el.clientWidth;
      setColW(Math.max(40, (w - GAP * 2) / 3));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Simple win toast (non-reveal)
  useEffect(() => {
    if (winReveal && winReveal.baseDays > 0) return;
    if (!toast) {
      setToastPhase("off");
      setToastText("");
      setToastPop(false);
      return;
    }
    setToastText(toast);
    setToastPhase("in");
    setToastPop(false);
    const tHold = window.setTimeout(() => setToastPhase("hold"), 280);
    const tOut = window.setTimeout(() => setToastPhase("out"), 280 + TOAST_HOLD_MS);
    const tDone = window.setTimeout(() => {
      setToastPhase("off");
      setToastText("");
      onToastDone?.();
    }, 280 + TOAST_HOLD_MS + 320);
    return () => {
      window.clearTimeout(tHold);
      window.clearTimeout(tOut);
      window.clearTimeout(tDone);
    };
  }, [toast, toastKey, onToastDone, winReveal]);

  // Bonus win reveal: +base → mult flies from top → +base*mult
  useEffect(() => {
    if (!winReveal || winReveal.baseDays <= 0) return;
    let cancelled = false;
    revealBusy.current = true;

    const sleep = (ms: number) => new Promise<void>((r) => window.setTimeout(r, ms));

    (async () => {
      const base = winReveal.baseDays;
      const mult = Math.max(1, winReveal.multiplier);
      setToastPop(false);
      setToastText(`+${base} дн.`);
      setToastPhase("in");
      await sleep(280);
      if (cancelled) return;
      setToastPhase("hold");
      await sleep(420);
      if (cancelled) return;

      if (mult >= 2 && frameRef.current && multRef.current) {
        // Ensure toast node is measured
        await sleep(30);
        const toastEl = toastRef.current;
        if (toastEl) {
          const frame = frameRef.current.getBoundingClientRect();
          const multBox = multRef.current.getBoundingClientRect();
          const toastBox = toastEl.getBoundingClientRect();
          const startX = multBox.left - frame.left + multBox.width / 2;
          const startY = multBox.top - frame.top + multBox.height / 2;
          const endX = toastBox.left - frame.left + toastBox.width / 2;
          const endY = toastBox.top - frame.top + toastBox.height / 2;
          setMultLaunching(true);
          setFly({
            kind: "mult",
            label: `${mult}×`,
            x: startX,
            y: startY,
            tx: endX,
            ty: endY,
            active: false,
          });
          await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
          if (cancelled) return;
          setFly({
            kind: "mult",
            label: `${mult}×`,
            x: startX,
            y: startY,
            tx: endX,
            ty: endY,
            active: true,
          });
          await sleep(MULT_FLY_MS);
          if (cancelled) return;
          setFly(null);
          setMultLaunching(false);
          setToastText(`+${base * mult} дн.`);
          setToastPop(true);
          await sleep(480);
          if (cancelled) return;
          setToastPop(false);
        }
      }

      await sleep(TOAST_HOLD_MS);
      if (cancelled) return;
      setToastPhase("out");
      await sleep(320);
      if (cancelled) return;
      setToastPhase("off");
      setToastText("");
      setToastPop(false);
      revealBusy.current = false;
      onWinRevealDoneRef.current?.();
    })();

    return () => {
      cancelled = true;
      revealBusy.current = false;
      setMultLaunching(false);
    };
  }, [winReveal, winRevealKey]);

  // Idle
  useEffect(() => {
    if (spinning) return;
    if (grid.length !== 9) return;
    setStrips([colOf(grid, 0), colOf(grid, 1), colOf(grid, 2)]);
    setOffsets([0, 0, 0]);
    setLanded([true, true, true]);
    setAnticipate(false);
  }, [grid, spinning]);

  // Spin downward (constant speed)
  useEffect(() => {
    if (!spinning) return;

    let cancelled = false;
    let raf = 0;
    settledOnce.current = false;
    setShowWin(false);
    setLanded([false, false, false]);
    setAnticipate(false);
    setFly(null);

    const maxY = (s: string[]) => Math.max(0, (s.length - VISIBLE) * CELL);
    const symPool = pool;

    if (!resultGrid || resultGrid.length !== 9) {
      const lead: [string, string, string][] = [
        colOf(gridRef.current, 0),
        colOf(gridRef.current, 1),
        colOf(gridRef.current, 2),
      ];
      const pending = [
        buildStripDown(lead[0], null, 40, symPool),
        buildStripDown(lead[1], null, 40, symPool),
        buildStripDown(lead[2], null, 40, symPool),
      ];
      const start: [number, number, number] = [
        maxY(pending[0]),
        maxY(pending[1]),
        maxY(pending[2]),
      ];
      setStrips(pending);
      stripsRef.current = pending;
      setOffsets(start);
      offsetsRef.current = start;

      const t0 = performance.now();
      const drift = (now: number) => {
        if (cancelled) return;
        const elapsed = (now - t0) / 1000;
        const traveled = elapsed * SPEED_PX;
        const next = [0, 1, 2].map((i) => Math.max(start[i] - traveled, CELL * 2));
        offsetsRef.current = next;
        setOffsets(next);
        raf = requestAnimationFrame(drift);
      };
      raf = requestAnimationFrame(drift);

      return () => {
        cancelled = true;
        cancelAnimationFrame(raf);
      };
    }

    const book = resultGrid;
    const curOff = offsetsRef.current;
    const curStrips = stripsRef.current;

    const leads: [string, string, string][] = [0, 1, 2].map((col) => {
      if (curStrips[col]?.length >= VISIBLE) {
        return visibleTriple(curStrips[col], curOff[col] || 0);
      }
      return colOf(gridRef.current, col);
    });

    const prelude =
      !inBonus &&
      ((colHasSymbol(book, 0, BONUS_SYMBOL) && colHasSymbol(book, 1, BONUS_SYMBOL)) ||
        (colAllSymbol(book, 0, "👑") && colAllSymbol(book, 1, "👑")));
    const pads = [
      SPIN_PAD[0],
      SPIN_PAD[1],
      SPIN_PAD[2] + (prelude ? Math.round(SPIN_SPEED * ANTICIPATION_SEC) : 0),
    ];

    const finalStrips = [0, 1, 2].map((col) =>
      buildStripDown(leads[col], colOf(book, col), pads[col], symPool)
    );

    setStrips(finalStrips);
    stripsRef.current = finalStrips;

    const from: [number, number, number] = [
      maxY(finalStrips[0]),
      maxY(finalStrips[1]),
      maxY(finalStrips[2]),
    ];
    const to: [number, number, number] = [0, 0, 0];
    setOffsets(from);
    offsetsRef.current = from;

    const landStart = performance.now();
    const colDone: [boolean, boolean, boolean] = [false, false, false];
    let preludeLit = false;

    const finishAfterFx = async () => {
      if (cancelled || settledOnce.current) return;
      settledOnce.current = true;
      setAnticipate(false);

      // Fly «Х» into multiplier during bonus
      if (inBonus) {
        const xIdx = firstSymbolCell(book, MULT_SYMBOL);
        if (xIdx >= 0 && frameRef.current && multRef.current && windowRef.current) {
          const frame = frameRef.current.getBoundingClientRect();
          const winBox = windowRef.current.getBoundingClientRect();
          const multBox = multRef.current.getBoundingClientRect();
          const c = cellCenter(xIdx, colW);
          const startX = winBox.left - frame.left + c.x;
          const startY = winBox.top - frame.top + c.y;
          const endX = multBox.left - frame.left + multBox.width / 2;
          const endY = multBox.top - frame.top + multBox.height / 2;
          setFly({
            kind: "x",
            label: MULT_SYMBOL,
            x: startX,
            y: startY,
            tx: endX,
            ty: endY,
            active: false,
          });
          await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
          if (cancelled) return;
          setFly({
            kind: "x",
            label: MULT_SYMBOL,
            x: startX,
            y: startY,
            tx: endX,
            ty: endY,
            active: true,
          });
          await new Promise((r) => setTimeout(r, 620));
          if (cancelled) return;
          setLocalMult((m) => m + 1);
          setFly(null);
        }
      }

      setShowWin(true);
      onSettled();
    };

    const tick = (now: number) => {
      if (cancelled) return;
      const elapsed = (now - landStart) / 1000;
      const traveled = elapsed * SPEED_PX;
      const next: [number, number, number] = [0, 0, 0];
      let allDone = true;

      for (let i = 0; i < 3; i++) {
        const y = from[i] - traveled;
        if (y <= to[i]) {
          next[i] = to[i];
          if (!colDone[i]) {
            colDone[i] = true;
            setLanded((prev) => {
              const n: [boolean, boolean, boolean] = [...prev];
              n[i] = true;
              return n;
            });
          }
        } else {
          next[i] = y;
          allDone = false;
        }
      }

      // Prelude highlight: reels 1–2 stopped, reel 3 still rolling
      if (prelude && colDone[0] && colDone[1] && !colDone[2] && !preludeLit) {
        preludeLit = true;
        setAnticipate(true);
      }

      offsetsRef.current = next;
      setOffsets(next);

      if (!allDone) {
        raf = requestAnimationFrame(tick);
        return;
      }

      void finishAfterFx();
    };

    raf = requestAnimationFrame(tick);

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spinning, resultGrid, pool, inBonus, colW]);

  const busy = spinning || !landed.every(Boolean) || !!fly;
  const winH = CELL * VISIBLE;
  const winW = colW * 3 + GAP * 2;

  const linePaths = useMemo(() => {
    if (!showWin || !winningLines.length) return [];
    return winningLines
      .map((li) => {
        const cells = PAYLINES[li] || [];
        if (cells.length < 2) return null;
        const pts = cells.map((idx) => cellCenter(idx, colW));
        return pts.map((p) => `${p.x},${p.y}`).join(" ");
      })
      .filter(Boolean) as string[];
  }, [showWin, winningLines, colW]);

  const spinsLabel =
    bonusSpinsLeft == null
      ? "Бонус"
      : bonusSpinsLeft <= 0
        ? "Последний спин"
        : `Осталось: ${bonusSpinsLeft}`;

  return (
    <div className="slot-wrap">
      {inBonus ? (
        <div className="slot-bonus-bar">
          <span className={`slot-mult ${multLaunching ? "is-launching" : ""}`} ref={multRef}>
            {localMult}×
          </span>
          <span className="slot-bonus-left">
            {spinsLabel}
            {bonusTotalDays != null ? ` · Итого: +${bonusTotalDays} дн.` : ""}
          </span>
        </div>
      ) : (
        <span ref={multRef} className="slot-mult-anchor" aria-hidden />
      )}

      <div
        ref={frameRef}
        className={`slot-frame ${busy ? "is-spinning" : ""} ${inBonus ? "is-bonus" : ""}`}
      >
        <div className="slot-window" ref={windowRef}>
          {[0, 1, 2].map((col) => (
            <div
              key={col}
              className={`reel ${anticipate && col === 2 ? "is-anticipate" : ""}`}
            >
              <div
                className="reel-strip"
                style={{
                  transform: `translate3d(0, ${-offsets[col]}px, 0)`,
                }}
              >
                {(strips[col] || []).map((sym, idx) => (
                  <div key={`${col}-${idx}-${sym}`} className="reel-cell">
                    <span>{sym}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {linePaths.length ? (
            <svg
              className="slot-lines"
              width={winW}
              height={winH}
              viewBox={`0 0 ${winW} ${winH}`}
            >
              {linePaths.map((pts, i) => (
                <polyline
                  key={i}
                  points={pts}
                  fill="none"
                  stroke="rgba(196, 163, 90, 0.95)"
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              ))}
            </svg>
          ) : null}
        </div>

        <div className="slot-fade top" />
        <div className="slot-fade bot" />

        {toastPhase !== "off" && toastText ? (
          <div
            ref={toastRef}
            className={`slot-toast phase-${toastPhase} ${toastPop ? "is-pop" : ""}`}
          >
            <span>{toastText}</span>
          </div>
        ) : null}

        {fly ? (
          <div
            className={`slot-fly-x ${fly.kind === "mult" ? "is-mult" : ""} ${fly.active ? "is-flying" : ""}`}
            style={
              {
                "--sx": `${fly.x}px`,
                "--sy": `${fly.y}px`,
                "--ex": `${fly.tx}px`,
                "--ey": `${fly.ty}px`,
              } as CSSProperties
            }
          >
            {fly.label}
          </div>
        ) : null}
      </div>

      <button
        type="button"
        className="ma-btn ma-btn-primary slot-spin-btn"
        disabled={disabled || busy || inBonus}
        onClick={onSpin}
      >
        {busy
          ? "Крутим…"
          : spinLabel || (inBonus ? "Бонус…" : "Крутить (−1 день)")}
      </button>

      {message ? <p className="ma-casino-msg">{message}</p> : null}
      <p className="ma-muted tiny">
        RTP 96% · макс. выигрыш 365 дней · осталось: <b>{daysLeft ?? "—"}</b>
      </p>

      {paytable?.length ? (
        <div className="slot-paytable">
          {paytable.map((p) => (
            <span key={p.symbol}>
              {p.note === "bonus"
                ? `${p.symbol}×3 → бонус`
                : p.note === "mult"
                  ? `${p.symbol} → +1×`
                  : `${p.symbol}×3 → ${p.pay}д`}
            </span>
          ))}
        </div>
      ) : null}

      <style jsx>{`
        .slot-wrap {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .slot-bonus-bar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }
        .slot-mult {
          font-family: var(--font-display);
          font-size: 1.6rem;
          font-weight: 800;
          color: #c4a35a;
          letter-spacing: 0.02em;
          display: inline-flex;
          min-width: 2.4rem;
          transition: transform 0.25s ease, color 0.25s ease, opacity 0.2s ease;
        }
        .slot-mult.is-launching {
          opacity: 0.25;
          transform: scale(0.92);
        }
        .slot-mult-anchor {
          position: absolute;
          width: 0;
          height: 0;
          overflow: hidden;
        }
        .slot-bonus-left {
          font-size: 0.9rem;
          color: rgba(232, 238, 247, 0.7);
        }
        .slot-frame {
          position: relative;
          border-radius: 22px;
          padding: 12px;
          background:
            linear-gradient(160deg, rgba(196, 163, 90, 0.32), rgba(31, 169, 122, 0.1) 45%, #08131f),
            #0a1624;
          border: 1px solid rgba(196, 163, 90, 0.35);
          box-shadow: 0 16px 36px rgba(0, 0, 0, 0.35);
          overflow: visible;
        }
        .slot-frame.is-bonus {
          border-color: rgba(31, 169, 122, 0.55);
        }
        .slot-frame.is-spinning {
          box-shadow:
            0 16px 36px rgba(0, 0, 0, 0.35),
            0 0 24px rgba(31, 169, 122, 0.2);
        }
        .slot-window {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: ${GAP}px;
          height: ${CELL * VISIBLE}px;
          position: relative;
          z-index: 1;
        }
        .slot-lines {
          position: absolute;
          inset: 0;
          pointer-events: none;
          z-index: 3;
          overflow: visible;
        }
        .reel {
          position: relative;
          height: 100%;
          overflow: hidden;
          border-radius: 14px;
          background: radial-gradient(circle at 30% 20%, #1a2d44, #060d16 75%);
          border: 1px solid rgba(232, 238, 247, 0.1);
          transition:
            box-shadow 0.25s ease,
            border-color 0.25s ease;
        }
        .reel.is-anticipate {
          border-color: rgba(196, 163, 90, 0.95);
          box-shadow:
            0 0 0 2px rgba(196, 163, 90, 0.55),
            0 0 22px rgba(196, 163, 90, 0.45);
          animation: anticipatePulse 0.85s ease-in-out infinite;
        }
        .reel-strip {
          will-change: transform;
        }
        .reel-cell {
          height: ${CELL}px;
          display: grid;
          place-items: center;
          font-size: 2rem;
          line-height: 1;
        }
        .slot-fade {
          pointer-events: none;
          position: absolute;
          left: 12px;
          right: 12px;
          height: 28px;
          z-index: 2;
        }
        .slot-fade.top {
          top: 12px;
          background: linear-gradient(to bottom, rgba(8, 19, 31, 0.85), transparent);
          border-radius: 14px 14px 0 0;
        }
        .slot-fade.bot {
          bottom: 12px;
          background: linear-gradient(to top, rgba(8, 19, 31, 0.85), transparent);
          border-radius: 0 0 14px 14px;
        }
        .slot-toast {
          position: absolute;
          left: 50%;
          top: 50%;
          z-index: 8;
          transform: translate(-50%, -50%) scale(0.86);
          opacity: 0;
          pointer-events: none;
          padding: 12px 18px;
          border-radius: 16px;
          background: linear-gradient(180deg, rgba(20, 36, 52, 0.96), rgba(8, 18, 30, 0.96));
          border: 1px solid rgba(196, 163, 90, 0.65);
          box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
          color: #f3e2b0;
          font-family: var(--font-display);
          font-size: 1.25rem;
          font-weight: 700;
          letter-spacing: 0.01em;
          white-space: nowrap;
        }
        .slot-toast.phase-in {
          animation: toastIn 0.28s ease-out forwards;
        }
        .slot-toast.phase-hold {
          opacity: 1;
          transform: translate(-50%, -50%) scale(1);
        }
        .slot-toast.phase-out {
          animation: toastOut 0.32s ease-in forwards;
        }
        .slot-toast.is-pop {
          animation: toastPop 0.45s cubic-bezier(0.2, 1.2, 0.3, 1);
        }
        .slot-fly-x {
          position: absolute;
          left: 0;
          top: 0;
          z-index: 9;
          font-size: 2rem;
          line-height: 1;
          pointer-events: none;
          transform: translate(calc(var(--sx) - 0.5em), calc(var(--sy) - 0.5em)) scale(1);
          filter: drop-shadow(0 0 10px rgba(196, 163, 90, 0.8));
        }
        .slot-fly-x.is-mult {
          font-family: var(--font-display);
          font-weight: 800;
          color: #c4a35a;
          font-size: 1.7rem;
        }
        .slot-fly-x.is-flying {
          animation: flyX 0.65s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
        }
        .slot-fly-x.is-mult.is-flying {
          animation: flyMult 0.65s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
        }
        .slot-spin-btn {
          margin-top: 2px;
        }
        .slot-paytable {
          display: flex;
          flex-wrap: wrap;
          gap: 8px 12px;
          font-size: 0.78rem;
          color: rgba(232, 238, 247, 0.55);
        }
        @keyframes anticipatePulse {
          0%,
          100% {
            box-shadow:
              0 0 0 2px rgba(196, 163, 90, 0.45),
              0 0 16px rgba(196, 163, 90, 0.3);
          }
          50% {
            box-shadow:
              0 0 0 3px rgba(196, 163, 90, 0.85),
              0 0 28px rgba(196, 163, 90, 0.55);
          }
        }
        @keyframes toastIn {
          from {
            opacity: 0;
            transform: translate(-50%, -42%) scale(0.82);
          }
          to {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
          }
        }
        @keyframes toastOut {
          from {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
          }
          to {
            opacity: 0;
            transform: translate(-50%, -58%) scale(0.9);
          }
        }
        @keyframes toastPop {
          0% {
            transform: translate(-50%, -50%) scale(1);
          }
          40% {
            transform: translate(-50%, -50%) scale(1.18);
          }
          100% {
            transform: translate(-50%, -50%) scale(1);
          }
        }
        @keyframes flyX {
          0% {
            transform: translate(calc(var(--sx) - 0.5em), calc(var(--sy) - 0.5em)) scale(1);
            opacity: 1;
          }
          60% {
            transform: translate(calc(var(--ex) - 0.5em), calc(var(--ey) - 0.5em)) scale(1.35);
            opacity: 1;
          }
          100% {
            transform: translate(calc(var(--ex) - 0.5em), calc(var(--ey) - 0.5em)) scale(0.4);
            opacity: 0;
          }
        }
        @keyframes flyMult {
          0% {
            transform: translate(calc(var(--sx) - 0.5em), calc(var(--sy) - 0.5em)) scale(1);
            opacity: 1;
          }
          55% {
            transform: translate(calc(var(--ex) - 0.5em), calc(var(--ey) - 0.5em)) scale(1.45);
            opacity: 1;
          }
          100% {
            transform: translate(calc(var(--ex) - 0.5em), calc(var(--ey) - 0.5em)) scale(0.55);
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
}
