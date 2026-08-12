"use client";

import { useEffect, useMemo, useRef, useState } from "react";

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
const GAP = 8; // must match .slot-window gap
/** Random symbols between result (top) and current symbols (bottom). */
const SPIN_PAD = [8, 12, 16];
/** Staggered stop: column 1 → 2 → 3. */
const STOP_MS = [480, 720, 960];
/** Match land average speed: pad_cells / (stop_ms/1000) ≈ 16.67 cells/s */
const DRIFT_SPEED = SPIN_PAD.map((pad, i) => pad / (STOP_MS[i] / 1000));

export type BonusRoundView = {
  grid: string[];
  winning_lines: number[];
  base_win: number;
  x_hit: boolean;
  multiplier: number;
  win_days: number;
};

type Props = {
  grid: string[];
  resultGrid: string[] | null;
  winningLines: number[];
  spinning: boolean;
  disabled?: boolean;
  onSpin: () => void;
  onSettled: () => void;
  message?: string;
  daysLeft?: number | null;
  paytable?: Array<{ symbol: string; pay: number; note?: string }>;
  /** Bonus mode UI */
  inBonus?: boolean;
  multiplier?: number;
  bonusSpinsLeft?: number | null;
  spinLabel?: string;
};

function randFrom(pool: readonly string[]) {
  return pool[Math.floor(Math.random() * pool.length)];
}

function colOf(grid: string[], col: number): [string, string, string] {
  return [grid[col] || "❓", grid[3 + col] || "❓", grid[6 + col] || "❓"];
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

function easeSmooth(t: number) {
  return t * t * t * (t * (t * 6 - 15) + 10);
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
  daysLeft,
  paytable,
  inBonus,
  multiplier = 1,
  bonusSpinsLeft,
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

  const stripsRef = useRef(strips);
  const offsetsRef = useRef(offsets);
  const gridRef = useRef(grid);
  const settledOnce = useRef(false);
  const windowRef = useRef<HTMLDivElement | null>(null);

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

  // Idle
  useEffect(() => {
    if (spinning) return;
    if (grid.length !== 9) return;
    setStrips([colOf(grid, 0), colOf(grid, 1), colOf(grid, 2)]);
    setOffsets([0, 0, 0]);
    setLanded([true, true, true]);
  }, [grid, spinning]);

  // Spin downward
  useEffect(() => {
    if (!spinning) return;

    let cancelled = false;
    let raf = 0;
    settledOnce.current = false;
    setShowWin(false);
    setLanded([false, false, false]);

    const maxY = (s: string[]) => Math.max(0, (s.length - VISIBLE) * CELL);
    const symPool = pool;

    if (!resultGrid || resultGrid.length !== 9) {
      const lead: [string, string, string][] = [
        colOf(gridRef.current, 0),
        colOf(gridRef.current, 1),
        colOf(gridRef.current, 2),
      ];
      const pending = [
        buildStripDown(lead[0], null, 36, symPool),
        buildStripDown(lead[1], null, 40, symPool),
        buildStripDown(lead[2], null, 44, symPool),
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
        const next = [0, 1, 2].map((i) => {
          const traveled = elapsed * DRIFT_SPEED[i] * CELL;
          return Math.max(start[i] - traveled, CELL * 2);
        });
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

    const finalStrips = [0, 1, 2].map((col) =>
      buildStripDown(leads[col], colOf(book, col), SPIN_PAD[col], symPool)
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

    const tick = (now: number) => {
      if (cancelled) return;
      const next: [number, number, number] = [0, 0, 0];
      let allDone = true;

      for (let i = 0; i < 3; i++) {
        const t = Math.min(1, Math.max(0, (now - landStart) / STOP_MS[i]));
        next[i] = from[i] + (to[i] - from[i]) * easeSmooth(t);
        if (t >= 1) {
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
          allDone = false;
        }
      }

      offsetsRef.current = next;
      setOffsets(next);

      if (!allDone) {
        raf = requestAnimationFrame(tick);
        return;
      }

      if (!settledOnce.current) {
        settledOnce.current = true;
        setShowWin(true);
        onSettled();
      }
    };

    raf = requestAnimationFrame(tick);

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spinning, resultGrid, pool]);

  const busy = spinning || !landed.every(Boolean);
  const winH = CELL * VISIBLE;
  const winW = colW * 3 + GAP * 2;

  const linePaths = useMemo(() => {
    if (!showWin || !winningLines.length) return [];
    return winningLines.map((li) => {
      const cells = PAYLINES[li] || [];
      if (cells.length < 2) return null;
      const pts = cells.map((idx) => cellCenter(idx, colW));
      return pts.map((p) => `${p.x},${p.y}`).join(" ");
    }).filter(Boolean) as string[];
  }, [showWin, winningLines, colW]);

  return (
    <div className="slot-wrap">
      {inBonus ? (
        <div className="slot-bonus-bar">
          <span className="slot-mult">{multiplier}×</span>
          {bonusSpinsLeft != null ? (
            <span className="slot-bonus-left">Осталось спинов: {bonusSpinsLeft}</span>
          ) : null}
        </div>
      ) : null}

      <div className={`slot-frame ${busy ? "is-spinning" : ""} ${inBonus ? "is-bonus" : ""}`}>
        <div className="slot-window" ref={windowRef}>
          {[0, 1, 2].map((col) => (
            <div key={col} className="reel">
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

      {!busy && message ? <p className="ma-casino-msg">{message}</p> : null}
      <p className="ma-muted tiny">
        RTP 96% · макс. выигрыш 30 дней · осталось: <b>{daysLeft ?? "—"}</b>
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
          overflow: hidden;
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
      `}</style>
    </div>
  );
}
