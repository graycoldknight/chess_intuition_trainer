import React, { useEffect, useState } from 'react';

/**
 * XpPopup — shows "+N XP" animating upward and fading out on correct solve.
 * Renders nothing when xp is null.
 */
function XpPopup({ xp }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (xp == null) return;
    setVisible(true);
    const t = setTimeout(() => setVisible(false), 1800);
    return () => clearTimeout(t);
  }, [xp]);

  if (xp == null || !visible) return null;

  return (
    <div
      data-testid="xp-popup"
      style={{
        position: 'fixed',
        top: '30%',
        left: '50%',
        transform: 'translateX(-50%)',
        fontSize: '2rem',
        fontWeight: 900,
        color: '#facc15',
        textShadow: '0 0 12px rgba(250,204,21,0.7)',
        pointerEvents: 'none',
        zIndex: 1000,
        animation: 'xpFloat 1.8s ease-out forwards',
      }}
    >
      +{xp} XP
      <style>{`
        @keyframes xpFloat {
          0%   { opacity: 1; transform: translateX(-50%) translateY(0); }
          80%  { opacity: 1; transform: translateX(-50%) translateY(-60px); }
          100% { opacity: 0; transform: translateX(-50%) translateY(-80px); }
        }
      `}</style>
    </div>
  );
}

export default XpPopup;
