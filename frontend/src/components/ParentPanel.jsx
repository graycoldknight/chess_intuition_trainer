import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Chessboard } from 'react-chessboard';
import * as api from '../services/api';

const STATUS_COLOR = {
  pending: '#6b7280',
  extracting: '#f59e0b',
  review: '#3b82f6',
  verified: '#10b981',
};

function StatusBadge({ chapterId, status }) {
  return (
    <span
      data-testid={`status-badge-${chapterId}`}
      data-status={status}
      style={{
        padding: '2px 8px',
        borderRadius: 12,
        fontSize: 11,
        fontWeight: 600,
        background: STATUS_COLOR[status] || '#6b7280',
        color: '#fff',
        textTransform: 'uppercase',
        letterSpacing: 1,
      }}
    >
      {status === 'pending' ? 'Awaiting JSON' : status}
    </span>
  );
}

function ChaptersTab({ chapters }) {
  return (
    <div data-testid="chapters-tab">
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ color: '#9ca3af', fontSize: 12, textAlign: 'left', borderBottom: '1px solid #374151' }}>
            <th style={{ padding: '8px 12px' }}>#</th>
            <th style={{ padding: '8px 12px' }}>Chapter</th>
            <th style={{ padding: '8px 12px' }}>Status</th>
            <th style={{ padding: '8px 12px' }}>Puzzles</th>
          </tr>
        </thead>
        <tbody>
          {chapters.map((ch) => (
            <tr
              key={ch.id}
              style={{ borderBottom: '1px solid #1f2937', fontSize: 14 }}
            >
              <td style={{ padding: '10px 12px', color: '#6b7280' }}>{ch.id}</td>
              <td style={{ padding: '10px 12px' }}>{ch.title}</td>
              <td style={{ padding: '10px 12px' }}>
                <StatusBadge chapterId={ch.id} status={ch.extraction_status} />
              </td>
              <td style={{ padding: '10px 12px', color: '#9ca3af' }}>
                {ch.puzzle_count || 0}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PuzzleReviewTab() {
  const [chapters, setChapters] = useState([]);
  const [selectedChapter, setSelectedChapter] = useState(null);
  const [puzzles, setPuzzles] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getChapters().then((chs) => {
      const reviewable = chs.filter(
        (c) => c.extraction_status === 'review' || c.extraction_status === 'verified'
      );
      setChapters(reviewable);
    });
  }, []);

  function loadPuzzles(chapterId) {
    setSelectedChapter(chapterId);
    setLoading(true);
    api.getUnverifiedPuzzles(chapterId).then((ps) => {
      setPuzzles(ps);
      setLoading(false);
    });
  }

  return (
    <div data-testid="puzzle-review-tab">
      <div style={{ marginBottom: 16 }}>
        <select
          style={{
            background: '#374151',
            color: '#fff',
            border: '1px solid #4b5563',
            borderRadius: 6,
            padding: '6px 12px',
            fontSize: 14,
          }}
          value={selectedChapter || ''}
          onChange={(e) => loadPuzzles(Number(e.target.value))}
        >
          <option value="">Select chapter to review</option>
          {chapters.map((ch) => (
            <option key={ch.id} value={ch.id}>
              Ch {ch.id}: {ch.title}
            </option>
          ))}
        </select>
      </div>

      {loading && <div style={{ color: '#9ca3af' }}>Loading puzzles...</div>}

      {!loading && selectedChapter && puzzles.length === 0 && (
        <div style={{ color: '#6b7280', textAlign: 'center', padding: 32 }}>
          No unverified puzzles in this chapter.
        </div>
      )}

      {puzzles.map((p) => (
        <div
          key={p.id}
          style={{
            display: 'flex',
            gap: 24,
            padding: 16,
            background: '#1f2937',
            borderRadius: 8,
            marginBottom: 12,
            alignItems: 'flex-start',
          }}
        >
          <div style={{ flex: 1 }}>
            <div style={{ color: '#9ca3af', fontSize: 12, marginBottom: 4 }}>
              Puzzle #{p.puzzle_number}
            </div>
            <div style={{ fontFamily: 'monospace', fontSize: 11, color: '#6b7280', wordBreak: 'break-all' }}>
              {p.fen}
            </div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ color: '#9ca3af', fontSize: 12, marginBottom: 4 }}>
              Solution
            </div>
            <div style={{ color: '#10b981', fontWeight: 700 }}>{p.solution_san}</div>
            <div style={{ color: '#6b7280', fontSize: 12 }}>{p.solution_uci}</div>
          </div>
          <div style={{ color: p.verified ? '#10b981' : '#f59e0b', fontSize: 12 }}>
            {p.verified ? 'Verified' : 'Unverified'}
          </div>
        </div>
      ))}
    </div>
  );
}

function GraduationsTab({ graduations, onApprove }) {
  return (
    <div data-testid="graduations-tab">
      {graduations.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#6b7280', padding: 48 }}>
          No pending graduations.
        </div>
      ) : (
        <div>
          {graduations.map((g) => (
            <div
              key={g.batch_id}
              data-testid={`graduation-row-${g.batch_id}`}
              data-status={g.status}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px 20px',
                background: '#1f2937',
                borderRadius: 8,
                marginBottom: 12,
                border: g.status === 'graduated' ? '1px solid #10b981' : '1px solid #374151',
              }}
            >
              <div>
                <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4 }}>
                  {g.profile_name}
                </div>
                <div style={{ color: '#9ca3af', fontSize: 13 }}>
                  {g.chapter_title} &middot; Circle {g.current_circle}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                {g.status === 'graduated' ? (
                  <span style={{ color: '#10b981', fontWeight: 600 }}>Graduated</span>
                ) : (
                  <button
                    data-testid={`approve-btn-${g.batch_id}`}
                    onClick={() => onApprove(g.batch_id)}
                    style={{
                      background: '#10b981',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 6,
                      padding: '8px 20px',
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: 14,
                    }}
                  >
                    Approve Graduation
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const TABS = [
  { key: 'live', label: 'Live', testId: 'tab-live' },
  { key: 'chapters', label: 'Chapters', testId: 'tab-chapters' },
  { key: 'puzzle-review', label: 'Puzzle Review', testId: 'tab-puzzle-review' },
  { key: 'graduations', label: 'Graduations', testId: 'tab-graduations' },
];

function ParentPanel() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('live');
  const [chapters, setChapters] = useState([]);
  const [graduations, setGraduations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activity, setActivity] = useState(null);
  const [liveError, setLiveError] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    Promise.all([api.getChapters(), api.getPendingGraduations()])
      .then(([chs, grads]) => {
        setChapters(chs);
        setGraduations(grads);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (activeTab !== 'live') {
      clearInterval(pollRef.current);
      return;
    }
    const fetchActivity = () =>
      api.getParentActivity()
        .then(setActivity)
        .catch(() => setLiveError('Could not reach server'));
    fetchActivity();
    pollRef.current = setInterval(fetchActivity, 3000);
    return () => clearInterval(pollRef.current);
  }, [activeTab]);

  function handleApprove(batchId) {
    api.approveGraduation(batchId).then((result) => {
      setGraduations((prev) =>
        prev.map((g) =>
          g.batch_id === batchId ? { ...g, status: result.status } : g
        )
      );
    });
  }

  const tabBtnStyle = (key) => ({
    padding: '10px 24px',
    background: activeTab === key ? '#3b82f6' : 'transparent',
    color: activeTab === key ? '#fff' : '#9ca3af',
    border: 'none',
    borderBottom: activeTab === key ? '2px solid #3b82f6' : '2px solid transparent',
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: 14,
    transition: 'all 0.15s',
  });

  if (loading) {
    return <div style={{ textAlign: 'center', marginTop: 80 }}>Loading...</div>;
  }

  return (
    <div data-testid="parent-panel" style={{ maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0, fontSize: 24 }}>Parent Panel</h1>
        <button
          onClick={() => navigate('/')}
          style={{ background: 'transparent', color: '#9ca3af', border: '1px solid #374151', borderRadius: 6, padding: '6px 16px', cursor: 'pointer' }}
        >
          Back
        </button>
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid #374151', marginBottom: 24 }}>
        {TABS.map((t) => (
          <button
            key={t.key}
            data-testid={t.testId}
            style={tabBtnStyle(t.key)}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
            {t.key === 'graduations' && graduations.filter((g) => g.status === 'ready_to_graduate').length > 0 && (
              <span style={{
                marginLeft: 8,
                background: '#ef4444',
                color: '#fff',
                borderRadius: 999,
                padding: '1px 7px',
                fontSize: 11,
              }}>
                {graduations.filter((g) => g.status === 'ready_to_graduate').length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'live' && (
        <div>
          <div style={{ color: '#666', fontSize: '0.75rem', marginBottom: 12 }}>
            Auto-refreshes every 3 seconds
          </div>
          {liveError && <div style={{ color: '#ef4444', marginBottom: 12 }}>{liveError}</div>}
          {!activity && !liveError && <div>Loading...</div>}
          {activity?.children.map(child => (
            <div key={child.profile_id} style={{
              background: '#1e1e2e', borderRadius: 10, padding: 16, marginBottom: 16,
              border: '1px solid #333',
            }}>
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div>
                  <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>{child.name}</span>
                  <span style={{ color: '#a78bfa', marginLeft: 10 }}>⚡ {child.total_xp} XP</span>
                  {child.current_streak > 0 && (
                    <span style={{ color: '#f59e0b', marginLeft: 8 }}>🔥 {child.current_streak}d</span>
                  )}
                </div>
                {child.session ? (
                  <span style={{ color: '#4ade80', fontSize: '0.8rem' }}>● Training now</span>
                ) : (
                  <span style={{ color: '#555', fontSize: '0.8rem' }}>○ Not active</span>
                )}
              </div>

              {/* Session stats */}
              {child.session && (
                <div style={{ display: 'flex', gap: 20, marginBottom: 12, fontSize: '0.85rem', color: '#aaa' }}>
                  <span>Attempted: <b style={{ color: '#fff' }}>{child.session.puzzles_attempted}</b></span>
                  <span>Correct: <b style={{ color: '#4ade80' }}>{child.session.puzzles_correct}</b></span>
                  {child.training.current_circle && (
                    <span>Circle: <b style={{ color: '#a78bfa' }}>{child.training.current_circle}</b></span>
                  )}
                </div>
              )}

              {/* Current puzzle board */}
              {child.current_puzzle && (
                <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start', marginBottom: 12 }}>
                  <div>
                    <div style={{ color: '#666', fontSize: '0.7rem', marginBottom: 4 }}>
                      Current puzzle — Ch. {child.training.chapter_id} #{child.current_puzzle.puzzle_number}
                    </div>
                    <Chessboard
                      position={child.current_puzzle.fen}
                      boardOrientation={child.current_puzzle.turn === 'w' ? 'white' : 'black'}
                      arePiecesDraggable={false}
                      boardWidth={160}
                    />
                  </div>

                  {/* Recent attempts feed */}
                  <div style={{ flex: 1 }}>
                    <div style={{ color: '#666', fontSize: '0.7rem', marginBottom: 6 }}>Recent attempts</div>
                    <div style={{ maxHeight: 168, overflowY: 'auto' }}>
                      {child.recent_attempts.length === 0 && (
                        <div style={{ color: '#555', fontSize: '0.8rem' }}>No attempts yet</div>
                      )}
                      {child.recent_attempts.map((a, i) => (
                        <div key={i} style={{
                          display: 'flex', gap: 8, alignItems: 'center',
                          padding: '3px 0', borderBottom: '1px solid #2a2a3a',
                          fontSize: '0.8rem',
                        }}>
                          <span style={{ color: a.success ? '#4ade80' : '#ef4444' }}>{a.success ? '✓' : '✗'}</span>
                          <span style={{ color: '#888' }}>#{a.puzzle_number}</span>
                          <span style={{ color: '#666', fontSize: '0.72rem' }}>
                            {(a.time_taken_ms / 1000).toFixed(1)}s
                          </span>
                          <span style={{ color: '#555', fontSize: '0.7rem' }}>C{a.circle}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {!child.current_puzzle && !child.session && (
                <div style={{ color: '#555', fontSize: '0.85rem' }}>Not currently training</div>
              )}
            </div>
          ))}
        </div>
      )}
      {activeTab === 'chapters' && <ChaptersTab chapters={chapters} />}
      {activeTab === 'puzzle-review' && <PuzzleReviewTab />}
      {activeTab === 'graduations' && (
        <GraduationsTab graduations={graduations} onApprove={handleApprove} />
      )}
    </div>
  );
}

export default ParentPanel;
