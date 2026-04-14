import React from 'react';

const CATEGORY_COLORS = {
  theme: '#a78bfa',
  speed: '#fbbf24',
  streak: '#f97316',
  milestone: '#34d399',
  improvement: '#60a5fa',
};

function BadgeDisplay({ badges = [], earnedIds = [] }) {
  const earnedSet = new Set(earnedIds);

  return (
    <div
      data-testid="badge-display"
      style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}
    >
      {badges.map((badge) => {
        const earned = earnedSet.has(badge.id);
        const color = CATEGORY_COLORS[badge.category] || '#888';
        return (
          <div
            key={badge.key}
            data-testid={`badge-${badge.key}`}
            data-locked={String(!earned)}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              width: 110,
              padding: '8px 4px',
              borderRadius: 10,
              background: earned ? '#2a2a3a' : '#1e1e1e',
              border: `1px solid ${earned ? color : '#333'}`,
              opacity: earned ? 1 : 0.45,
              cursor: 'default',
            }}
          >
            <div style={{ fontSize: '1.6rem', marginBottom: 4 }}>
              {earned ? '🏅' : '🔒'}
            </div>
            <div
              style={{
                fontSize: '0.65rem',
                color: earned ? color : '#666',
                textAlign: 'center',
                lineHeight: 1.3,
                wordBreak: 'break-word',
              }}
            >
              {badge.name}
            </div>
            <div
              style={{
                fontSize: '0.58rem',
                color: '#555',
                textAlign: 'center',
                marginTop: 3,
                lineHeight: 1.3,
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              {badge.description}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default BadgeDisplay;
