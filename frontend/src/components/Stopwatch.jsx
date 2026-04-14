import React, { useState, useEffect, useRef } from 'react';

/**
 * Stopwatch for puzzle solving.
 * tickMs controls how often the display refreshes (coarser = less pressure).
 *   Circle 1 → 30 000 ms  (jumps every 30 s)
 *   Circle 2 → 15 000 ms  (jumps every 15 s)
 *   Circle 3 →  1 000 ms  (jumps every 1 s)
 *   Circle 4+ →    50 ms  (smooth ms display)
 * Calls onStop(elapsedMs) with true elapsed time when active → false.
 */
function Stopwatch({ active, onStop, tickMs = 50, style }) {
  const [elapsedMs, setElapsedMs] = useState(0);
  const startRef = useRef(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (active) {
      startRef.current = Date.now();
      setElapsedMs(0);
      intervalRef.current = setInterval(() => {
        setElapsedMs(Date.now() - startRef.current);
      }, tickMs);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      if (startRef.current !== null && onStop) {
        onStop(Date.now() - startRef.current);
      }
      startRef.current = null;
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [active, tickMs]); // eslint-disable-line react-hooks/exhaustive-deps

  const formatMs = (ms) => {
    if (tickMs >= 1000) {
      // Coarse ticks — show whole seconds only
      return `${Math.floor(ms / 1000)}s`;
    }
    const s = Math.floor(ms / 1000);
    const frac = Math.floor((ms % 1000) / 10);
    return `${s}.${String(frac).padStart(2, '0')}s`;
  };

  return (
    <div
      data-testid="stopwatch"
      style={{
        fontSize: '1.4rem',
        fontVariantNumeric: 'tabular-nums',
        color: '#aaa',
        textAlign: 'center',
        ...style,
      }}
    >
      {formatMs(elapsedMs)}
    </div>
  );
}

export default Stopwatch;
