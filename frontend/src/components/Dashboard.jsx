import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import CircleProgress from './CircleProgress';
import * as api from '../services/api';

function fmt(ms) {
  if (ms == null) return '--';
  return (ms / 1000).toFixed(1) + 's';
}

function fmtDuration(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function Dashboard() {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const pid = parseInt(profileId, 10);

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getDashboard(pid)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [pid]);

  if (error) {
    return (
      <div style={{ textAlign: 'center', marginTop: 80, color: '#f87171' }}>
        Error: {error}
        <br />
        <button onClick={() => navigate('/')} style={btnStyle}>Back</button>
      </div>
    );
  }

  if (!data) {
    return <div style={{ textAlign: 'center', marginTop: 80 }}>Loading...</div>;
  }

  const { profile, training, today } = data;
  const circleStats = training.circle_stats || {};

  return (
    <div
      data-testid="dashboard"
      style={{ maxWidth: 480, margin: '0 auto', padding: '24px 16px' }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem' }}>{profile.name}</h2>
          <span style={{ color: '#888', fontSize: '0.85rem' }}>
            {profile.total_xp} XP &nbsp;·&nbsp;
            🔥 {profile.current_streak} day streak
          </span>
        </div>
        <button
          onClick={() => navigate('/')}
          style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', fontSize: '0.85rem' }}
        >
          ← Back
        </button>
      </div>

      {/* Today's stats */}
      <div data-testid="today-stats" style={cardStyle}>
        <div style={cardLabelStyle}>Today</div>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <Stat label="Solved" value={today.puzzles_attempted} />
          <Stat label="Correct" value={today.puzzles_correct} />
          <Stat
            label="Accuracy"
            value={
              today.puzzles_attempted > 0
                ? Math.round((today.puzzles_correct / today.puzzles_attempted) * 100) + '%'
                : '--'
            }
          />
          {today.duration_seconds > 0 && (
            <Stat label="Time trained" value={fmtDuration(today.duration_seconds)} />
          )}
        </div>
      </div>

      {/* Active batch */}
      {training.has_active_batch ? (
        <>
          <div data-testid="batch-progress" style={cardStyle}>
            <div style={cardLabelStyle}>Chapter {training.chapter_id} Progress</div>
            <CircleProgress currentCircle={training.current_circle} />
            <div style={{ marginTop: 12, color: '#aaa', fontSize: '0.85rem', textAlign: 'center' }}>
              {training.total_puzzles} puzzles &nbsp;·&nbsp; {training.status}
            </div>
          </div>

          {/* Speed trend across circles */}
          {Object.keys(circleStats).length > 0 && (
            <div data-testid="speed-trend" style={cardStyle}>
              <div style={cardLabelStyle}>Speed Trend</div>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {Object.entries(circleStats).map(([circle, stats]) => (
                  <div key={circle} style={{ textAlign: 'center' }}>
                    <div style={{ color: '#a78bfa', fontSize: '0.75rem' }}>C{circle}</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700 }}>
                      {fmt(stats.avg_time_ms)}
                    </div>
                    <div style={{ color: '#60a5fa', fontSize: '0.7rem' }}>
                      {fmt(stats.median_time_ms)}
                    </div>
                    <div style={{ color: '#888', fontSize: '0.7rem' }}>
                      {stats.correct}/{stats.total}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            data-testid="continue-training-btn"
            onClick={() => navigate(`/train/${pid}`)}
            style={{ ...btnStyle, width: '100%', marginTop: 24, fontSize: '1.1rem' }}
          >
            {today.puzzles_attempted === 0 ? 'Start Training' : 'Continue Training'}
          </button>

          {training.status === 'ready_to_graduate' && (
            <div
              data-testid="graduation-ready"
              style={{ textAlign: 'center', marginTop: 12, color: '#4ade80', fontSize: '0.9rem' }}
            >
              Ready to Graduate! Ask Raj to approve.
            </div>
          )}
        </>
      ) : (
        <div data-testid="no-batch" style={{ textAlign: 'center', marginTop: 32 }}>
          <button
            onClick={() => api.createBatch(pid, 1).then(() => window.location.reload())}
            style={{ marginTop: 8, padding: '10px 28px', background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600, fontSize: '1rem' }}
          >
            Start Chapter 1
          </button>
        </div>
      )}

      {/* Gamification links */}
      <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
        <button
          data-testid="badges-btn"
          onClick={() => navigate(`/badges/${pid}`)}
          style={{ ...btnStyle, flex: 1, background: '#1e1e2e', border: '1px solid #333', fontSize: '0.9rem' }}
        >
          🏅 Badges
        </button>
        <button
          data-testid="leaderboard-btn"
          onClick={() => navigate('/leaderboard')}
          style={{ ...btnStyle, flex: 1, background: '#1e1e2e', border: '1px solid #333', fontSize: '0.9rem' }}
        >
          🏆 Leaderboard
        </button>
      </div>
      {pid === 3 && (
        <button
          onClick={() => navigate('/parent')}
          style={{ ...btnStyle, width: '100%', marginTop: 12, background: '#1e1e2e', border: '1px solid #7c3aed', fontSize: '0.9rem', color: '#a78bfa' }}
        >
          ⚙️ Parent Panel
        </button>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>{value}</div>
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

export default Dashboard;
