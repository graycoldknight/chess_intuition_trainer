import React, { useState, useEffect } from 'react';

const SESSION_CAP_SECONDS = 60 * 60;

/**
 * Counts down from 60:00 based on sessionStartedAt (ISO string).
 * Calls onExpired() when the session hits the cap.
 */
function SessionTimer({ sessionStartedAt, onExpired, style }) {
  const [remaining, setRemaining] = useState(SESSION_CAP_SECONDS);

  useEffect(() => {
    if (!sessionStartedAt) return;

    const tick = () => {
      const elapsed = (Date.now() - new Date(sessionStartedAt).getTime()) / 1000;
      const left = Math.max(0, SESSION_CAP_SECONDS - elapsed);
      setRemaining(left);
      if (left === 0 && onExpired) onExpired();
    };

    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [sessionStartedAt]); // eslint-disable-line react-hooks/exhaustive-deps

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const pct = remaining / SESSION_CAP_SECONDS;
  const color = pct > 0.25 ? '#4ade80' : pct > 0.1 ? '#facc15' : '#f87171';

  return (
    <div
      data-testid="session-timer"
      style={{ fontSize: '0.9rem', color, textAlign: 'center', ...style }}
    >
      {formatTime(remaining)} / 60:00
    </div>
  );
}

export default SessionTimer;
