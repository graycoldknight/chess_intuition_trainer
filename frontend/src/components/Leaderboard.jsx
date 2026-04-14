import React from 'react';

const METRICS = [
  { key: 'total_xp', label: 'XP', testId: 'xp', format: (v) => v ?? 0 },
  { key: 'current_streak', label: 'Streak', testId: 'streak', format: (v) => v ?? 0 },
  { key: 'chapters_graduated', label: 'Chapters', testId: 'chapters', format: (v) => v ?? 0 },
];

function Leaderboard({ data = [] }) {
  // Compute leaders per metric
  const leaders = {};
  for (const metric of METRICS) {
    let best = null;
    let bestVal = -Infinity;
    for (const row of data) {
      const val = row[metric.key] ?? 0;
      if (val > bestVal) {
        bestVal = val;
        best = row.id;
      }
    }
    leaders[metric.key] = best;
  }

  if (data.length === 0) {
    return (
      <div data-testid="leaderboard" style={{ textAlign: 'center', color: '#888', padding: 24 }}>
        No players yet.
      </div>
    );
  }

  return (
    <div data-testid="leaderboard" style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
        <thead>
          <tr>
            <th style={thStyle}>Player</th>
            {METRICS.map((m) => (
              <th key={m.key} style={thStyle}>{m.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[...data].sort((a, b) => (b.total_xp ?? 0) - (a.total_xp ?? 0)).map((row) => {
            const nameSlug = row.name.toLowerCase();
            return (
              <tr key={row.id} data-testid={`leaderboard-${nameSlug}`}>
                <td style={tdStyle}>
                  <strong style={{ color: '#e5e7eb' }}>{row.name}</strong>
                </td>
                {METRICS.map((m) => {
                  const isLeader = leaders[m.key] === row.id;
                  return (
                    <td
                      key={m.key}
                      data-testid={`leaderboard-${nameSlug}-${m.testId}`}
                      data-leader={String(isLeader)}
                      style={{
                        ...tdStyle,
                        color: isLeader ? '#fbbf24' : '#9ca3af',
                        fontWeight: isLeader ? 700 : 400,
                      }}
                    >
                      {isLeader && <span aria-hidden="true">⭐ </span>}{m.format(row[m.key])}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const thStyle = {
  padding: '8px 12px',
  textAlign: 'left',
  color: '#6b7280',
  fontSize: '0.75rem',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  borderBottom: '1px solid #333',
};

const tdStyle = {
  padding: '10px 12px',
  borderBottom: '1px solid #222',
};

export default Leaderboard;
