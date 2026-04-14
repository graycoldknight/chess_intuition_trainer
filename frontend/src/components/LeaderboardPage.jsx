import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Leaderboard from './Leaderboard';
import * as api from '../services/api';

function LeaderboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getLeaderboard()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div style={{ color: '#f87171', textAlign: 'center', marginTop: 80 }}>Error: {error}</div>;
  if (!data) return <div style={{ textAlign: 'center', marginTop: 80 }}>Loading...</div>;

  return (
    <div data-testid="leaderboard-page" style={{ maxWidth: 540, margin: '0 auto', padding: '24px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24, gap: 16 }}>
        <button
          onClick={() => navigate('/')}
          style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer' }}
        >
          ← Home
        </button>
        <h2 style={{ margin: 0, fontSize: '1.3rem' }}>Leaderboard</h2>
      </div>
      <div style={{ background: '#222', borderRadius: 12, padding: 16 }}>
        <Leaderboard data={data} />
      </div>
    </div>
  );
}

export default LeaderboardPage;
