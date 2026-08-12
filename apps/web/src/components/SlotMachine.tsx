"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const ALL = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣", "👑"] as const;
const PAYLINES = [
  [0, 1, 2],
  [3, 4, 5],
  [6, 7, 8],
  [0, 4, 8],
  [2, 4, 6],
];

const CELL = 78;
const VISIBLE = 3;
/** Random symbols before land per column (short spin). */
const SPIN_PAD = [7, 11, 15];
/** Staggered stop: column 1 → 2 → 3 from land start. */
const STOP_MS = [520, 780, 1040];

type Props = {
  grid: string[];
  /** Book from server while spinning — animation must end on these columns. */
  resultGrid: string[] | null;
  winningLines: number[];
  spinning: boolean;
  disabled?: boolean;
  onSpin: () => void;
  /** Called when all three reels have landed on the book. */
  onSettled: () => void;
  message?: string;
  daysLeft?: number | null;
  paytable?: Array<{ symbol: string; pay: number }>;
};

function randSym() {
  return ALL[Math.floor(Math.random() * ALL.length)];
}

function colOf(grid: string[], col: number): [string, string, string] {
  return [grid[col] || "❓", grid[3 + col] || "❓", grid[6 + col] || "❓"];
}

function buildStrip(
  lead: [string, string, string],
  finals: [string, string, string] | null,
  pad: number
): string[] {
  const mid = Array.from({ length: pad }, () => randSym());
  if (!finals) return [...lead, ...mid];
  return [...lead, ...mid, ...finals];
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

function easeInOut(t: number) {
  return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
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
}: Props) {
  const [strips, setStrips] = useState<string[][]>(() => [
    ["❓", "❓", "❓"],
    ["❓", "❓", "❓"],
    ["❓", "❓", "❓"],
  ]);
  const [offsets, setOffsets] = useState<number[]>([0, 0, 0]);
  const [landed, setLanded] = useState<[boolean, boolean, boolean]>([true, true, true]);
  const [showWin, setShowWin] = useState(false);

  const stripsRef = useRef(strips);
  const offsetsRef = useRef(offsets);
  const gridRef = useRef(grid);
  const settledOnce = useRef(false);

  useEffect(() => {
    stripsRef.current = strips;
  }, [strips]);
  useEffect(() => {
    offsetsRef.current = offsets;
  }, [offsets]);
  useEffect(() => {
    gridRef.current = grid;
  }, [grid]);

  const highlight = useMemo(() => {
    const set = new Set<number>();
    if (!showWin) return set;
    for (const li of winningLines) {
      for (const idx of PAYLINES[li] || []) set.add(idx);
    }
    return set;
  }, [winningLines, showWin]);

  // Idle: show settled grid (must match last landed book — no post-swap)
  useEffect(() => {
    if (spinning) return;
    if (grid.length !== 9) return;
    setStrips([colOf(grid, 0), colOf(grid, 1), colOf(grid, 2)]);
    setOffsets([0, 0, 0]);
    setLanded([true, true, true]);
  }, [grid, spinning]);

  // Spin: drift randoms → when book arrives, continue motion and stop col 1→2→3 on book
  useEffect(() => {
    if (!spinning) return;

    let cancelled = false;
    let raf = 0;
    settledOnce.current = false;
    setShowWin(false);
    setLanded([false, false, false]);

    const maxY = (s: string[]) => Math.max(0, (s.length - VISIBLE) * CELL);

    // --- Phase A: waiting for book — old symbols leave down, random scroll ---
    if (!resultGrid || resultGrid.length !== 9) {
      const lead: [string, string, string][] = [
        colOf(gridRef.current, 0),
        colOf(gridRef.current, 1),
        colOf(gridRef.current, 2),
      ];
      const pending = [
        buildStrip(lead[0], null, 36),
        buildStrip(lead[1], null, 40),
        buildStrip(lead[2], null, 44),
      ];
      setStrips(pending);
      stripsRef.current = pending;
      setOffsets([0, 0, 0]);
      offsetsRef.current = [0, 0, 0];

      const t0 = performance.now();
      const speeds = [5.2, 5.8, 6.4]; // cells/sec after ease-in

      const drift = (now: number) => {
        if (cancelled) return;
        const elapsed = (now - t0) / 1000;
        const easeIn = Math.min(1, elapsed / 0.16);
        const accel = easeIn * easeIn;
        const next = [0, 1, 2].map((i) => {
          const y = elapsed * speeds[i] * accel * CELL;
          return Math.min(y, maxY(pending[i]) - CELL * 2);
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

    // --- Phase B: book is here — rebuild strip ending on book, no visual jump ---
    const book = resultGrid;
    const curOff = offsetsRef.current;
    const curStrips = stripsRef.current;

    const leads: [string, string, string][] = [0, 1, 2].map((col) => {
      if (curStrips[col]?.length >= VISIBLE) {
        return visibleTriple(curStrips[col], curOff[col] || 0);
      }
      return colOf(gridRef.current, col);
    });

    const phase = [0, 1, 2].map((i) => (curOff[i] || 0) % CELL);
    const finalStrips = [0, 1, 2].map((col) =>
      buildStrip(leads[col], colOf(book, col), SPIN_PAD[col])
    );

    setStrips(finalStrips);
    stripsRef.current = finalStrips;
    // Keep fractional cell phase so the strip swap doesn't hitch
    const from: [number, number, number] = [phase[0], phase[1], phase[2]];
    const to: [number, number, number] = [
      maxY(finalStrips[0]),
      maxY(finalStrips[1]),
      maxY(finalStrips[2]),
    ];
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
        next[i] = from[i] + (to[i] - from[i]) * easeInOut(t);
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
        // Parent applies grid = book and clears spinning; idle view = same symbols
        onSettled();
      }
    };

    raf = requestAnimationFrame(tick);

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spinning, resultGrid]);

  const busy = spinning || !landed.every(Boolean);

  return (
    <div className="slot-wrap">
      <div className={`slot-frame ${busy ? "is-spinning" : ""}`}>
        <div className="slot-window">
          {[0, 1, 2].map((col) => (
            <div key={col} className="reel">
              <div
                className="reel-strip"
                style={{
                  transform: `translate3d(0, ${-offsets[col]}px, 0)`,
                }}
              >
                {(strips[col] || []).map((sym, idx) => {
                  const finalStart = (strips[col]?.length || 0) - VISIBLE;
                  const isFinal = landed[col] && idx >= finalStart;
                  const row = idx - finalStart;
                  const gridIdx = isFinal ? row * 3 + col : -1;
                  const win = gridIdx >= 0 && highlight.has(gridIdx);
                  return (
                    <div key={`${col}-${idx}-${sym}`} className={`reel-cell ${win ? "win" : ""}`}>
                      <span>{sym}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        <div className="slot-fade top" />
        <div className="slot-fade bot" />
      </div>

      <button
        type="button"
        className="ma-btn ma-btn-primary slot-spin-btn"
        disabled={disabled || busy}
        onClick={onSpin}
      >
        {busy ? "Крутим…" : "Крутить (−1 день)"}
      </button>

      {message ? <p className="ma-casino-msg">{message}</p> : null}
      <p className="ma-muted tiny">
        RTP 96% · макс. выигрыш 30 дней · осталось: <b>{daysLeft ?? "—"}</b>
      </p>

      {paytable?.length ? (
        <div className="slot-paytable">
          {paytable.map((p) => (
            <span key={p.symbol}>
              {p.symbol}×3 → {p.pay}д
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
        .slot-frame.is-spinning {
          box-shadow:
            0 16px 36px rgba(0, 0, 0, 0.35),
            0 0 24px rgba(31, 169, 122, 0.2);
        }
        .slot-window {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
          height: ${CELL * VISIBLE}px;
          position: relative;
          z-index: 1;
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
        .reel-cell.win {
          animation: winpulse 0.65s ease-in-out 2;
        }
        .reel-cell.win span {
          filter: drop-shadow(0 0 8px rgba(196, 163, 90, 0.75));
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
        @keyframes winpulse {
          0%,
          100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.08);
          }
        }
      `}</style>
    </div>
  );
}
