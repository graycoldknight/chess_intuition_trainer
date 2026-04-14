import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import * as api from '../services/api';

function fmt(ms) {
  if (ms == null) return '--';
  return (ms / 1000).toFixed(1) + 's';
}

function pct(correct, total) {
  if (!total) return '--';
  return Math.round((correct / total) * 100) + '%';
}

function ResultsScreen() {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const pid = parseInt(profileId, 10);

  const [data, setData] = useState(null);

  useEffect(() => {
    api.getDashboard(pid).then(setData).catch(console.error);
  }, [pid]);

  if (!data) {
    return <div style={{ textAlign: 'center', marginTop: 80 }}>Loading results...</div>;
  }

  const { training } = data;
  const circleStats = training.circle_stats || {};
  const completedCircle = training.current_circle - 1;
  const prevCircle = completedCircle - 1;

  const current = circleStats[String(completedCircle)];
  const prev = circleStats[String(prevCircle)];

  // Improvement: % faster avg time vs previous circle
  let improvement = null;
  if (current?.avg_time_ms && prev?.avg_time_ms) {
    const delta = prev.avg_time_ms - current.avg_time_ms;
    improvement = Math.round((delta / prev.avg_time_ms) * 100);
  }

  const readyToGraduate = training.status === 'ready_to_graduate';

  return (
    <div
      data-testid="results-screen"
      style={{ maxWidth: 480, margin: '0 auto', padding: '32px 16px', textAlign: 'center' }}
    >
      <h2 style={{ fontSize: '1.6rem', marginBottom: 4 }}>
        Circle {completedCircle} Complete!
      </h2>
      <p style={{ color: '#888', marginBottom: 28 }}>
        Chapter {training.chapter_id}
      </p>

      {/* Circle stats */}
      {current && (
        <div data-testid="circle-stats" style={cardStyle}>
          <div style={cardLabelStyle}>Circle {completedCircle} Stats</div>
          <div style={{ display: 'flex', gap: 24, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Stat label="Accuracy" value={pct(current.correct, current.total)} />
            <Stat label="Avg Time" value={fmt(current.avg_time_ms)} />
            <Stat label="Median Time" value={fmt(current.median_time_ms)} />
            <Stat label="Puzzles" value={`${current.correct}/${current.total}`} />
          </div>

          {improvement != null && (
            <div
              data-testid="improvement"
              style={{
                marginTop: 16,
                color: improvement > 0 ? '#4ade80' : '#f87171',
                fontWeight: 600,
                fontSize: '0.95rem',
              }}
            >
              {improvement > 0
                ? `${improvement}% faster than Circle ${prevCircle}`
                : `${Math.abs(improvement)}% slower than Circle ${prevCircle}`}
            </div>
          )}
        </div>
      )}

      {/* All circles summary */}
      {Object.keys(circleStats).length > 1 && (
        <div data-testid="all-circles-summary" style={cardStyle}>
          <div style={cardLabelStyle}>Progress</div>
          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
            {Object.entries(circleStats).map(([c, stats]) => (
              <div key={c} style={{ textAlign: 'center' }}>
                <div style={{ color: '#a78bfa', fontSize: '0.75rem' }}>C{c}</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 600 }}>{fmt(stats.avg_time_ms)}</div>
                <div style={{ color: '#60a5fa', fontSize: '0.75rem' }}>{fmt(stats.median_time_ms)}</div>
                <div style={{ color: '#888', fontSize: '0.7rem' }}>{pct(stats.correct, stats.total)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {readyToGraduate ? (
        <div data-testid="graduation-ready" style={{ marginBottom: 20 }}>
          <div style={{ color: '#4ade80', fontSize: '1.1rem', fontWeight: 700, marginBottom: 8 }}>
            Ready to Graduate!
          </div>
          <p style={{ color: '#888', fontSize: '0.875rem' }}>
            Average solve time is under 15s. Ask Raj to approve graduation.
          </p>
        </div>
      ) : (
        <p style={{ color: '#888', marginBottom: 20, fontSize: '0.875rem' }}>
          Keep going — graduate when avg solve time is under 15s.
        </p>
      )}

      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
        <button
          data-testid="start-next-circle-btn"
          onClick={() => navigate(`/train/${pid}`)}
          style={btnStyle}
        >
          Start Circle {training.current_circle}
        </button>
        <button
          onClick={() => navigate(`/dashboard/${pid}`)}
          style={{ ...btnStyle, background: '#333' }}
        >
          Dashboard
        </button>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: '1.3rem', fontWeight: 700 }}>{value}</div>
      <div style={{ color: '#888', fontSize: '0.75rem' }}>{label}</div>
    </div>
  );
}

const cardStyle = {
  background: '#222',
  borderRadius: 12,
  padding: '16px',
  marginBottom: 16,
};

const cardLabelStyle = {
  color: '#888',
  fontSize: '0.75rem',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginBottom: 12,
};

const btnStyle = {
  background: '#7c3aed',
  border: 'none',
  borderRadius: 8,
  padding: '12px 24px',
  color: '#fff',
  cursor: 'pointer',
  fontSize: '1rem',
};

export default ResultsScreen;
