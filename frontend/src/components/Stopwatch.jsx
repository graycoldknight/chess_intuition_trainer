import React, { useState, useEffect, useRef } from 'react';

/**
 * Millisecond-precision stopwatch for puzzle solving.
 * Starts when active=true, stops and resets when active=false.
 * Calls onStop(elapsedMs) when active transitions from true to false.
 */
function Stopwatch({ active, onStop, style }) {
  const [elapsedMs, setElapsedMs] = useState(0);
  const startRef = useRef(null);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (active) {
      startRef.current = Date.now();
      setElapsedMs(0);
      intervalRef.current = setInterval(() => {
        setElapsedMs(Date.now() - startRef.current);
      }, 50);
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
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  const formatMs = (ms) => {
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
