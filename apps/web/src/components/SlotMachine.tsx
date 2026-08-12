"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const SYMBOLS = ["🍒", "🍋", "🔔", "⭐", "💎", "7️⃣", "👑"];
const PAYLINES = [
  [0, 1, 2],
  [3, 4, 5],
  [6, 7, 8],
  [0, 4, 8],
  [2, 4, 6],
];

type Props = {
  grid: string[];
  winningLines: number[];
  spinning: boolean;
  disabled?: boolean;
  onSpin: () => void;
  message?: string;
  daysLeft?: number | null;
  paytable?: Array<{ symbol: string; pay: number }>;
};

function stripFor(finalSym: string, length = 24): string[] {
  const out: string[] = [];
  for (let i = 0; i < length - 1; i++) {
    out.push(SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)]);
  }
  out.push(finalSym);
  return out;
}

export function SlotMachine({
  grid,
  winningLines,
  spinning,
  disabled,
  onSpin,
  message,
  daysLeft,
  paytable,
}: Props) {
  const [phase, setPhase] = useState<"idle" | "spin" | "stop">("idle");
  const [display, setDisplay] = useState<string[]>(grid.length === 9 ? grid : Array(9).fill("❓"));
  const [strips, setStrips] = useState<string[][]>([[], [], []]);
  const [colStopped, setColStopped] = useState<[boolean, boolean, boolean]>([true, true, true]);
  const stopTimers = useRef<number[]>([]);

  const highlight = useMemo(() => {
    const set = new Set<number>();
    for (const li of winningLines) {
      for (const idx of PAYLINES[li] || []) set.add(idx);
    }
    return set;
  }, [winningLines]);

  useEffect(() => {
    if (!spinning) return;
    // Start spin visuals immediately
    setPhase("spin");
    setColStopped([false, false, false]);
    // placeholder strips until result arrives
    setStrips([
      stripFor(SYMBOLS[0]),
      stripFor(SYMBOLS[1]),
      stripFor(SYMBOLS[2]),
    ]);
  }, [spinning]);

  useEffect(() => {
    if (spinning) return;
    if (grid.length !== 9) return;
    // Result landed: rebuild strips ending on final symbols, stagger stop
    const cols = [0, 1, 2].map((col) =>
      stripFor(grid[col], 18 + col * 4).concat([grid[3 + col], grid[6 + col]])
    );
    // For 3x3 we show 3 rows — each column strip ends with top,mid,bot of that column
    const colStrips = [0, 1, 2].map((col) => {
      const finals = [grid[col], grid[3 + col], grid[6 + col]];
      const pad: string[] = [];
      for (let i = 0; i < 16 + col * 6; i++) {
        pad.push(SYMBOLS[Math.floor(Math.random() * SYMBOLS.length)]);
      }
      return [...pad, ...finals];
    });
    setStrips(colStrips);
    setPhase("spin");
    setColStopped([false, false, false]);
    stopTimers.current.forEach((t) => window.clearTimeout(t));
    const delays = [900, 1400, 1900];
    delays.forEach((ms, i) => {
      const id = window.setTimeout(() => {
        setColStopped((prev) => {
          const next = [...prev] as [boolean, boolean, boolean];
          next[i] = true;
          return next;
        });
        if (i === 2) {
          setDisplay(grid);
          setPhase("stop");
        }
      }, ms);
      stopTimers.current.push(id);
    });
    return () => stopTimers.current.forEach((t) => window.clearTimeout(t));
  }, [grid, spinning]);

  // Visible cell from strip: last 3 symbols when stopped, animated offset when spinning
  function cellSymbol(row: number, col: number): string {
    if (colStopped[col] || phase === "idle" || phase === "stop") {
      return display[row * 3 + col] || "❓";
    }
    const strip = strips[col] || [];
    if (!strip.length) return "❓";
    // fake motion: cycle by time
    const t = Date.now();
    const idx = (Math.floor(t / 50) + row * 3 + col * 7) % strip.length;
    return strip[idx];
  }

  // Force re-render while spinning columns
  const [, bump] = useState(0);
  useEffect(() => {
    if (colStopped.every(Boolean)) return;
    const id = window.setInterval(() => bump((n) => n + 1), 50);
    return () => window.clearInterval(id);
  }, [colStopped]);

  return (
    <div className="slot-wrap">
      <div className={`slot-frame ${phase === "spin" && !colStopped.every(Boolean) ? "is-spinning" : ""}`}>
        <div className="slot-shine" />
        <div className="slot-grid">
          {[0, 1, 2].map((row) =>
            [0, 1, 2].map((col) => {
              const i = row * 3 + col;
              const sym = cellSymbol(row, col);
              const win = highlight.has(i) && colStopped.every(Boolean);
              return (
                <div
                  key={`${row}-${col}`}
                  className={`slot-cell ${!colStopped[col] ? "rolling" : ""} ${win ? "win" : ""}`}
                >
                  <span className="slot-sym">{sym}</span>
                </div>
              );
            })
          )}
        </div>
        <div className="slot-lines" aria-hidden>
          {[0, 1, 2].map((r) => (
            <span key={r} className="slot-hline" style={{ top: `${(r + 0.5) * 33.333}%` }} />
          ))}
        </div>
      </div>

      <button
        type="button"
        className="ma-btn ma-btn-primary slot-spin-btn"
        disabled={disabled || spinning || !colStopped.every(Boolean)}
        onClick={onSpin}
      >
        {spinning || !colStopped.every(Boolean) ? "Крутим…" : "Крутить (−1 день)"}
      </button>

      {message ? <p className="ma-casino-msg">{message}</p> : null}
      <p className="ma-muted tiny">
        Ставка фикс. 1 день · макс. 30 дней · осталось: <b>{daysLeft ?? "—"}</b>
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
          padding: 14px;
          background:
            linear-gradient(160deg, rgba(196, 163, 90, 0.35), rgba(31, 169, 122, 0.12) 40%, rgba(8, 18, 30, 0.95)),
            #0a1624;
          border: 1px solid rgba(196, 163, 90, 0.35);
          box-shadow:
            0 0 0 1px rgba(255, 255, 255, 0.04) inset,
            0 18px 40px rgba(0, 0, 0, 0.35);
          overflow: hidden;
        }
        .slot-frame.is-spinning {
          box-shadow:
            0 0 0 1px rgba(255, 255, 255, 0.06) inset,
            0 0 28px rgba(31, 169, 122, 0.25);
        }
        .slot-shine {
          pointer-events: none;
          position: absolute;
          inset: -40% -20%;
          background: linear-gradient(
            115deg,
            transparent 40%,
            rgba(255, 255, 255, 0.08) 50%,
            transparent 60%
          );
          animation: sheen 3.5s ease-in-out infinite;
        }
        .slot-grid {
          position: relative;
          z-index: 1;
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 10px;
        }
        .slot-cell {
          aspect-ratio: 1;
          display: grid;
          place-items: center;
          border-radius: 16px;
          background: radial-gradient(circle at 30% 25%, #1a2d44, #071018 70%);
          border: 1px solid rgba(232, 238, 247, 0.1);
          overflow: hidden;
        }
        .slot-cell.rolling .slot-sym {
          animation: tumble 0.12s linear infinite;
          filter: blur(1.2px);
          opacity: 0.85;
        }
        .slot-cell.win {
          border-color: #c4a35a;
          box-shadow:
            0 0 0 1px rgba(196, 163, 90, 0.55),
            0 0 22px rgba(196, 163, 90, 0.35);
          animation: winpulse 0.7s ease-in-out 2;
        }
        .slot-sym {
          font-size: 2rem;
          line-height: 1;
          display: block;
          transform: translateZ(0);
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
        @keyframes tumble {
          0% {
            transform: translateY(-35%);
          }
          100% {
            transform: translateY(35%);
          }
        }
        @keyframes winpulse {
          0%,
          100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.04);
          }
        }
        @keyframes sheen {
          0%,
          100% {
            transform: translateX(-20%);
            opacity: 0.2;
          }
          50% {
            transform: translateX(20%);
            opacity: 0.55;
          }
        }
      `}</style>
    </div>
  );
}
