import React from 'react';
import ReactConfetti from 'react-confetti';

/**
 * ConfettiOverlay — renders a full-screen confetti burst when active.
 * Automatically stops producing new pieces after 3 seconds (recycle=false).
 */
function ConfettiOverlay({ active }) {
  if (!active) return null;

  return (
    <div data-testid="confetti-overlay-canvas">
      <ReactConfetti
        recycle={false}
        numberOfPieces={200}
        gravity={0.3}
        style={{ position: 'fixed', top: 0, left: 0, pointerEvents: 'none', zIndex: 999 }}
      />
    </div>
  );
}

export default ConfettiOverlay;
