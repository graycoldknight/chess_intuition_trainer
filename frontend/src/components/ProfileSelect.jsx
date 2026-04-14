import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const PROFILES = [
  { id: 1, name: 'Rishi', role: 'student', emoji: '♟️' },
  { id: 2, name: 'Raghav', role: 'student', emoji: '♞' },
  { id: 3, name: 'Raj', role: 'parent', emoji: '👑' },
];

function ProfileSelect() {
  const navigate = useNavigate();

  return (
    <div style={{ maxWidth: 480, margin: '80px auto', textAlign: 'center' }}>
      <h1 style={{ fontSize: '2rem', marginBottom: 8 }}>Chess Intuition Trainer</h1>
      <p style={{ color: '#888', marginBottom: 40 }}>Who is training today?</p>
      <div style={{ display: 'flex', gap: 20, justifyContent: 'center', flexWrap: 'wrap' }}>
        {PROFILES.map((p) => (
          <button
            key={p.id}
            data-testid={`profile-${p.name.toLowerCase()}`}
            onClick={() => navigate(`/dashboard/${p.id}`)}
            style={{
              background: '#2a2a2a',
              border: '2px solid #444',
              borderRadius: 12,
              padding: '24px 32px',
              cursor: 'pointer',
              color: '#fff',
              fontSize: '1.1rem',
              minWidth: 120,
              transition: 'border-color 0.2s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = '#7c3aed')}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = '#444')}
          >
            <div style={{ fontSize: '2.5rem', marginBottom: 8 }}>{p.emoji}</div>
            <div style={{ fontWeight: 600 }}>{p.name}</div>
            <div style={{ fontSize: '0.75rem', color: '#888', marginTop: 4 }}>{p.role}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

export default ProfileSelect;
