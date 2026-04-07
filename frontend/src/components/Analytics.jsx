import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ResponsiveContainer,
  LineChart, Line,
  BarChart, Bar,
  XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts';
import * as api from '../services/api';

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

const emptyStyle = {
  color: '#555',
  fontSize: '0.85rem',
  textAlign: 'center',
  padding: '24px 0',
};

function fmtSec(ms) {
  if (ms == null) return '--';
  return (ms / 1000).toFixed(1) + 's';
}

function shortDate(iso) {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

export default function Analytics() {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const pid = parseInt(profileId, 10);

  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getAnalytics(pid)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [pid]);

  if (error) {
    return (
      <div style={{ textAlign: 'center', marginTop: 80, color: '#f87171' }}>
        Error: {error}
        <br />
        <button onClick={() => navigate(`/dashboard/${pid}`)} style={backBtnStyle}>← Back</button>
      </div>
    );
  }

  if (!data) {
    return <div style={{ textAlign: 'center', marginTop: 80 }}>Loading...</div>;
  }

  const { profile_name, circle_perf, daily_activity, time_distribution, hard_puzzles } = data;

  // Derived: circle accuracy %
  const circleAccuracy = circle_perf.map((c) => ({
    name: `C${c.circle}`,
    accuracy: c.total > 0 ? Math.round((c.correct / c.total) * 100) : 0,
    correct: c.correct,
    total: c.total,
  }));

  // Derived: circle speed (convert ms → seconds)
  const circleSpeed = circle_perf.map((c) => ({
    name: `C${c.circle}`,
    avg: c.avg_ms != null ? parseFloat((c.avg_ms / 1000).toFixed(2)) : null,
    median: c.median_ms != null ? parseFloat((c.median_ms / 1000).toFixed(2)) : null,
  }));

  // Daily activity with short date labels
  const dailyData = daily_activity.map((d) => ({
    ...d,
    label: shortDate(d.date),
  }));

  // Hard puzzles label
  const hardData = hard_puzzles.map((p) => ({
    label: `Ch.${p.chapter_id} #${p.puzzle_number}`,
    wrong: p.wrong_count,
  }));

  return (
    <div style={{ maxWidth: 480, margin: '0 auto', padding: '24px 16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: '1.4rem' }}>{profile_name} — Analytics</h2>
        <button
          onClick={() => navigate(`/dashboard/${pid}`)}
          style={backBtnStyle}
        >
          ← Back
        </button>
      </div>

      {/* 1. Circle Speed Curve */}
      <div style={cardStyle}>
        <div style={cardLabelStyle}>Circle Speed Curve</div>
        {circleSpeed.length < 2 ? (
          <div style={emptyStyle}>Complete at least 2 circles to see speed trend</div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={circleSpeed}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="name" stroke="#888" tick={{ fontSize: 12 }} />
              <YAxis stroke="#888" tick={{ fontSize: 12 }} unit="s" />
              <Tooltip
                contentStyle={{ background: '#1e1e2e', border: '1px solid #333', borderRadius: 8 }}
                formatter={(v) => v != null ? v + 's' : '--'}
              />
              <Legend wrapperStyle={{ fontSize: '0.75rem' }} />
              <Line type="monotone" dataKey="avg" name="Avg" stroke="#a78bfa" strokeWidth={2} dot={{ r: 4 }} connectNulls />
              <Line type="monotone" dataKey="median" name="Median" stroke="#60a5fa" strokeWidth={2} dot={{ r: 4 }} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* 2. Circle Accuracy */}
      <div style={cardStyle}>
        <div style={cardLabelStyle}>Circle Accuracy</div>
        {circleAccuracy.length === 0 ? (
          <div style={emptyStyle}>No circle data yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={circleAccuracy}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="name" stroke="#888" tick={{ fontSize: 12 }} />
              <YAxis stroke="#888" tick={{ fontSize: 12 }} unit="%" domain={[0, 100]} />
              <Tooltip
                contentStyle={{ background: '#1e1e2e', border: '1px solid #333', borderRadius: 8 }}
                formatter={(v, _name, props) => [
                  `${v}% (${props.payload.correct}/${props.payload.total})`,
                  'Accuracy',
                ]}
              />
              <Bar dataKey="accuracy" name="Accuracy" fill="#4ade80" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* 3. Daily Training Habit */}
      <div style={cardStyle}>
        <div style={cardLabelStyle}>Daily Training (Last 30 Days)</div>
        {dailyData.length === 0 ? (
          <div style={emptyStyle}>No session data in the last 30 days</div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={dailyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="label" stroke="#888" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
              <YAxis stroke="#888" tick={{ fontSize: 12 }} />
              <Tooltip
                contentStyle={{ background: '#1e1e2e', border: '1px solid #333', borderRadius: 8 }}
                formatter={(v, name) => [v, name === 'attempted' ? 'Attempted' : 'Correct']}
                labelFormatter={(l) => `Date: ${l}`}
              />
              <Legend wrapperStyle={{ fontSize: '0.75rem' }} />
              <Bar dataKey="attempted" name="Attempted" fill="#60a5fa" radius={[3, 3, 0, 0]} />
              <Bar dataKey="correct" name="Correct" fill="#4ade80" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* 4. Solve Time Distribution */}
      <div style={cardStyle}>
        <div style={cardLabelStyle}>Solve Time Distribution</div>
        {time_distribution.every((b) => b.count === 0) ? (
          <div style={emptyStyle}>No attempt data yet</div>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={time_distribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="bucket" stroke="#888" tick={{ fontSize: 11 }} />
              <YAxis stroke="#888" tick={{ fontSize: 12 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ background: '#1e1e2e', border: '1px solid #333', borderRadius: 8 }}
                formatter={(v) => [v, 'Attempts']}
              />
              <Bar dataKey="count" name="Attempts" fill="#a78bfa" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* 5. Hardest Puzzles */}
      <div style={cardStyle}>
        <div style={cardLabelStyle}>Hardest Puzzles (by wrong attempts)</div>
        {hardData.length === 0 ? (
          <div style={emptyStyle}>No wrong attempts yet — keep it up!</div>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(160, hardData.length * 28)}>
            <BarChart data={hardData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis type="number" stroke="#888" tick={{ fontSize: 12 }} allowDecimals={false} />
              <YAxis type="category" dataKey="label" stroke="#888" tick={{ fontSize: 11 }} width={70} />
              <Tooltip
                contentStyle={{ background: '#1e1e2e', border: '1px solid #333', borderRadius: 8 }}
                formatter={(v) => [v, 'Wrong attempts']}
              />
              <Bar dataKey="wrong" name="Wrong" fill="#f87171" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

const backBtnStyle = {
  background: 'none',
  border: 'none',
  color: '#888',
  cursor: 'pointer',
  fontSize: '0.85rem',
};
