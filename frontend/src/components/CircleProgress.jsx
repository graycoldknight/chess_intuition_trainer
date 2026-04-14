import React from 'react';

/**
 * Shows 5 circle dots (Yoo method has up to 5 circles).
 * Completed circles are filled, current is pulsing, future are dim.
 */
function CircleProgress({ currentCircle, maxCircles = 5 }) {
  return (
    <div
      data-testid="circle-progress"
      style={{ display: 'flex', gap: 10, alignItems: 'center', justifyContent: 'center' }}
    >
      {Array.from({ length: maxCircles }, (_, i) => {
        const circle = i + 1;
        const done = circle < currentCircle;
        const active = circle === currentCircle;
        return (
          <div
            key={circle}
            data-testid={`circle-dot-${circle}`}
            title={`Circle ${circle}`}
            style={{
              width: 18,
              height: 18,
              borderRadius: '50%',
              background: done ? '#7c3aed' : active ? '#a78bfa' : '#333',
              border: active ? '2px solid #a78bfa' : '2px solid transparent',
              boxShadow: active ? '0 0 8px #a78bfa' : 'none',
              transition: 'all 0.3s',
            }}
          />
        );
      })}
      <span style={{ color: '#888', fontSize: '0.8rem', marginLeft: 4 }}>
        Circle {currentCircle}
      </span>
    </div>
  );
}

export default CircleProgress;
