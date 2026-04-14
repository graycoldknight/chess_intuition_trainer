import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import BadgeDisplay from './BadgeDisplay';
import * as api from '../services/api';

function BadgesPage() {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const pid = parseInt(profileId, 10);

  const [badges, setBadges] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getBadges(pid)
      .then(setBadges)
      .catch((e) => setError(e.message));
  }, [pid]);

  if (error) return <div style={{ color: '#f87171', textAlign: 'center', marginTop: 80 }}>Error: {error}</div>;
  if (!badges) return <div style={{ textAlign: 'center', marginTop: 80 }}>Loading...</div>;

  const earnedIds = badges.filter((b) => b.earned).map((b) => b.id);

  return (
    <div data-testid="badges-page" style={{ maxWidth: 540, margin: '0 auto', padding: '24px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 24, gap: 16 }}>
        <button
          onClick={() => navigate(`/dashboard/${pid}`)}
          style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer' }}
        >
          ← Dashboard
        </button>
        <h2 style={{ margin: 0, fontSize: '1.3rem' }}>Badge Gallery</h2>
        <span style={{ color: '#888', fontSize: '0.85rem' }}>
          {earnedIds.length}/{badges.length} earned
        </span>
      </div>
      <BadgeDisplay badges={badges} earnedIds={earnedIds} />
    </div>
  );
}

export default BadgesPage;
