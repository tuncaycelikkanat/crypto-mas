import React, { useCallback, useEffect, useState, memo } from "react";

// Minimal 5x7 Font Definition
const GLYPHS: Record<string, number[]> = {
  "0": [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
  "1": [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
  "2": [0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111],
  "3": [0b01110, 0b10001, 0b00001, 0b00110, 0b00001, 0b10001, 0b01110],
  "4": [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
  "5": [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
  "6": [0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
  "7": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
  "8": [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
  "9": [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100],
  ":": [0b00000, 0b00100, 0b00000, 0b00000, 0b00000, 0b00100, 0b00000],
  "-": [0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000],
  "+": [0b00000, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0b00000],
  "/": [0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b00000, 0b00000],
  "$": [0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100],
  "%": [0b11001, 0b11010, 0b00100, 0b01000, 0b10110, 0b10011, 0b00000],
  "!": [0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100, 0b00000],
  "?": [0b01110, 0b10001, 0b00010, 0b00100, 0b00100, 0b00000, 0b00100],
  ".": [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100, 0b00000],
  " ": [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
  "A": [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
  "B": [0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
  "C": [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
  "D": [0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110],
  "E": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
  "F": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
  "G": [0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01110],
  "H": [0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
  "I": [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
  "J": [0b00011, 0b00001, 0b00001, 0b00001, 0b10001, 0b10001, 0b01110],
  "K": [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
  "L": [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
  "M": [0b10001, 0b11011, 0b10101, 0b10001, 0b10001, 0b10001, 0b10001],
  "N": [0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001],
  "O": [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
  "P": [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
  "Q": [0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b01110, 0b00001],
  "R": [0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
  "S": [0b01110, 0b10001, 0b10000, 0b01110, 0b00001, 0b10001, 0b01110],
  "T": [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
  "U": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
  "V": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
  "W": [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
  "X": [0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
  "Y": [0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
  "Z": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
};

// Build wide bitmap stripe for arbitrary text length
function buildTextBitmap(str: string): { bitmap: boolean[][]; width: number } {
  const chars = str.toUpperCase().split("");
  const gw = 5;
  const gh = 7;
  const totalW = chars.length * (gw + 1);
  const bitmap: boolean[][] = Array.from({ length: gh }, () => Array(totalW).fill(false));

  let ox = 0;
  for (const c of chars) {
    const rowsBits = GLYPHS[c] || GLYPHS[" "];
    for (let y = 0; y < gh; y++) {
      for (let x = 0; x < gw; x++) {
        bitmap[y][ox + x] = !!(rowsBits[y] & (1 << (gw - 1 - x)));
      }
    }
    ox += gw + 1;
  }
  return { bitmap, width: totalW };
}

// ── Smart Multi-Mode Disk Component ─────────────────────────────
// When mode === "text": Crisp Solid LED diode (instant, zero blur, no stroboscopic distortion)
// When mode !== "text": Classic 3D Flip X mechanical rotating disk
const Disk = memo(({ on, isTextMode }: { on: boolean; isTextMode: boolean }) => {
  
  if (isTextMode) {
    // 💡 Text Mode: Clean Solid LED (Fast, Crisp, Solid)
    return (
      <div
        style={{
          position: "relative",
          width: "100%",
          aspectRatio: "1/1",
          cursor: "crosshair",
        }}
      >
        {/* Unlit Dark Socket Housing */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            backgroundColor: "rgba(22, 22, 26, 0.95)",
            border: "1px solid rgba(255, 255, 255, 0.06)",
            boxShadow: "inset 0 1px 3px rgba(0, 0, 0, 0.9)",
          }}
        />
        {/* Crisp Solid LED Dot */}
        <div
          style={{
            position: "absolute",
            inset: "1px",
            borderRadius: "50%",
            backgroundColor: on ? "#E5FD52" : "transparent",
            border: on ? "1px solid #c4db3f" : "1px solid transparent",
            opacity: on ? 1 : 0,
            transform: on ? "scale(1)" : "scale(0.85)",
            transition: "opacity 45ms ease-out, transform 45ms ease-out",
          }}
        />
      </div>
    );
  }

  // 🔄 Time / Wave / Noise Modes: Classic 3D Flip X Mechanical Disk
  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        aspectRatio: "1/1",
        cursor: "crosshair",
        perspective: "400px",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          transformStyle: "preserve-3d",
          transform: on ? "rotateX(180deg)" : "rotateX(0deg)",
          transition: "transform 420ms cubic-bezier(0.34, 1.56, 0.64, 1)",
        }}
      >
        {/* Off State (Dark Socket) */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            backgroundColor: "rgba(24, 24, 27, 0.9)",
            border: "1px solid rgba(255, 255, 255, 0.08)",
            boxShadow: "inset 0 2px 4px rgba(0, 0, 0, 0.8)",
            backfaceVisibility: "hidden",
          }}
        />
        {/* On State (Solid Neon Lime Disk) */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            backgroundColor: "#E5FD52",
            border: "1px solid #c4db3f",
            boxShadow: "inset 0 -2px 5px rgba(0, 0, 0, 0.25)",
            backfaceVisibility: "hidden",
            transform: "rotateX(180deg)",
          }}
        />
      </div>
    </div>
  );
});
Disk.displayName = "Disk";

export function FlipDiskMatrix() {
  const cols = 31;
  const rows = 11;
  const [mode, setMode] = useState<"text" | "time" | "wave" | "noise">("text");
  const [text, setText] = useState<string>("CRYPTO MAS");
  const [scrollOffset, setScrollOffset] = useState<number>(0);

  const [bits, setBits] = useState(() =>
    Array.from({ length: rows }, () => Array(cols).fill(false))
  );

  // Pre-calculate full bitmap for current text
  const textData = React.useMemo(() => {
    const raw = text.trim() || "MAS";
    const padded = raw.length > 5 ? raw + "    " : raw;
    return buildTextBitmap(padded);
  }, [text]);

  const isLongText = textData.width > cols;

  // Step scroll offset for continuous marquee
  useEffect(() => {
    if (mode !== "text" || !isLongText) {
      setScrollOffset(0);
      return;
    }

    const interval = setInterval(() => {
      setScrollOffset((prev) => (prev + 1) % textData.width);
    }, 110); // 110ms crisp smooth marquee tick

    return () => clearInterval(interval);
  }, [mode, isLongText, textData.width]);

  const computeTarget = useCallback(
    (t: number): boolean[][] => {
      const grid = Array.from({ length: rows }, () => Array(cols).fill(false));
      const gh = 7;
      const oy = Math.max(0, Math.floor((rows - gh) / 2));

      if (mode === "time") {
        const timeStr = new Date().toLocaleTimeString("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        });
        const timeBitmap = buildTextBitmap(timeStr);
        const ox = Math.max(0, Math.floor((cols - timeBitmap.width) / 2));
        for (let y = 0; y < gh; y++) {
          for (let x = 0; x < timeBitmap.width; x++) {
            if (oy + y < rows && ox + x < cols) {
              grid[oy + y][ox + x] = timeBitmap.bitmap[y][x];
            }
          }
        }
        return grid;
      }

      if (mode === "text") {
        if (!isLongText) {
          const ox = Math.max(0, Math.floor((cols - textData.width) / 2));
          for (let y = 0; y < gh; y++) {
            for (let x = 0; x < textData.width; x++) {
              if (oy + y < rows && ox + x < cols) {
                grid[oy + y][ox + x] = textData.bitmap[y][x];
              }
            }
          }
        } else {
          for (let y = 0; y < gh; y++) {
            for (let x = 0; x < cols; x++) {
              const srcX = (scrollOffset + x) % textData.width;
              if (oy + y < rows) {
                grid[oy + y][x] = textData.bitmap[y][srcX];
              }
            }
          }
        }
        return grid;
      }

      if (mode === "wave") {
        return Array.from({ length: rows }, (_, y) =>
          Array.from({ length: cols }, (_, x) => {
            const v = Math.sin(x * 0.2 + t * 3) * Math.cos(y * 0.3 + t * 2);
            return v > 0.2;
          })
        );
      }

      // Noise pattern
      return Array.from({ length: rows }, () =>
        Array.from({ length: cols }, () => Math.random() > 0.6)
      );
    },
    [mode, textData, isLongText, scrollOffset, cols, rows]
  );

  useEffect(() => {
    let raf = 0;
    let last = 0;

    const getInterval = () => {
      if (mode === "text") return isLongText ? 100 : 300;
      if (mode === "wave") return 150;
      if (mode === "noise") return 250;
      return 1000;
    };

    const loop = (now: number) => {
      if (now - last > getInterval()) {
        last = now;
        const t = now / 1000;
        const next = computeTarget(t);

        setBits((prev) => {
          let changed = false;
          const newBits = prev.map((row, y) =>
            row.map((cell, x) => {
              if (cell !== next[y][x]) changed = true;
              return next[y][x];
            })
          );
          return changed ? newBits : prev;
        });
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [computeTarget, mode, isLongText]);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16, width: "100%" }}>
      
      {/* Top Controls: Mode Switcher (Clean & Minimalist) */}
      <div style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: 4,
        background: "var(--bg-raised)",
        borderRadius: "var(--radius-full)",
        border: "1px solid var(--border)",
      }}>
        {(["text", "time", "wave", "noise"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            style={{
              padding: "5px 14px",
              fontSize: "0.75rem",
              fontFamily: "'JetBrains Mono', monospace",
              textTransform: "uppercase",
              borderRadius: "var(--radius-full)",
              border: "none",
              cursor: "pointer",
              transition: "all 0.18s ease",
              background: mode === m ? "#E5FD52" : "transparent",
              color: mode === m ? "#000000" : "var(--text-muted)",
              fontWeight: mode === m ? 700 : 500,
              boxShadow: mode === m ? "0 0 12px rgba(229, 253, 82, 0.35)" : "none",
            }}
          >
            {m === "text" ? "✍️ Text" : m === "time" ? "⏰ Time" : m === "wave" ? "🌊 Wave" : "🎲 Noise"}
          </button>
        ))}
      </div>

      {/* Dynamic Text Input Box (Only in 'text' mode, unlimited length) */}
      {mode === "text" && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "100%", maxWidth: "460px" }}>
          <input
            type="text"
            value={text}
            onChange={(e) => {
              const filtered = e.target.value.toUpperCase().replace(/[^A-Z0-9: \-+$.%!]/g, "");
              setText(filtered);
            }}
            placeholder="TYPE ANY TEXT (AUTO-SCROLLS IF LONG)…"
            className="form-input mono"
            style={{
              width: "100%",
              textAlign: "center",
              letterSpacing: "0.15em",
              fontSize: "0.85rem",
              padding: "8px 16px",
              borderRadius: "var(--radius-full)",
              background: "var(--bg-raised)",
              borderColor: text ? "var(--text-primary)" : "var(--border)",
            }}
          />
        </div>
      )}

      {/* 3D Matrix Frame */}
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: "840px",
          padding: "16px",
          borderRadius: "20px",
          backgroundColor: "rgba(10, 10, 12, 0.95)",
          border: "1px solid var(--border-strong)",
          boxShadow: "inset 0 4px 20px rgba(0, 0, 0, 0.8), 0 20px 40px rgba(0, 0, 0, 0.6)",
        }}
      >
        {/* Inner Screen Bezel */}
        <div
          style={{
            position: "relative",
            backgroundColor: "#050507",
            borderRadius: "12px",
            padding: "14px 18px",
            border: "1px solid rgba(255, 255, 255, 0.05)",
            boxShadow: "inset 0 2px 14px rgba(0, 0, 0, 0.95)",
          }}
        >
          <div
            style={{
              display: "grid",
              gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`,
              gap: "min(0.4vw, 3px)",
              width: "100%",
            }}
          >
            {bits.map((row, y) =>
              row.map((on, x) => (
                <Disk key={`${x}-${y}`} on={on} isTextMode={mode === "text"} />
              ))
            )}
          </div>
        </div>
      </div>

    </div>
  );
}

export default FlipDiskMatrix;
