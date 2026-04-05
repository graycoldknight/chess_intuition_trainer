/**
 * Dashboard.test.jsx
 * Tests for the Dashboard component.
 */

import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import Dashboard from '../components/Dashboard';
import * as api from '../services/api';

vi.mock('../services/api');

const MOCK_DASHBOARD_WITH_BATCH = {
  profile: {
    id: 1,
    name: 'Rishi',
    total_xp: 120,
    current_streak: 3,
    longest_streak: 5,
    last_session_date: '2026-04-05',
  },
  training: {
    has_active_batch: true,
    batch_id: 1,
    chapter_id: 1,
    current_circle: 2,
    total_puzzles: 50,
    status: 'active',
    circle_stats: {
      '1': { total: 50, correct: 45, avg_time_ms: 12000 },
    },
    session_time_remaining_seconds: 3420,
    session: { id: 1, started_at: new Date().toISOString(), puzzles_attempted: 5, puzzles_correct: 4 },
  },
  today: {
    puzzles_attempted: 5,
    puzzles_correct: 4,
    duration_seconds: 180,
  },
};

const MOCK_DASHBOARD_NO_BATCH = {
  profile: {
    id: 1,
    name: 'Rishi',
    total_xp: 0,
    current_streak: 0,
    longest_streak: 0,
    last_session_date: null,
  },
  training: {
    has_active_batch: false,
    session_time_remaining_seconds: null,
    session: null,
  },
  today: {
    puzzles_attempted: 0,
    puzzles_correct: 0,
    duration_seconds: 0,
  },
};

const MOCK_DASHBOARD_SESSION_CAP = {
  ...MOCK_DASHBOARD_WITH_BATCH,
  training: {
    ...MOCK_DASHBOARD_WITH_BATCH.training,
    session_time_remaining_seconds: 0,
  },
};

function renderDashboard(profileId = '1') {
  return render(
    <MemoryRouter initialEntries={[`/dashboard/${profileId}`]}>
      <Routes>
        <Route path="/dashboard/:profileId" element={<Dashboard />} />
        <Route path="/train/:profileId" element={<div data-testid="training-session">Training</div>} />
        <Route path="/" element={<div data-testid="home">Home</div>} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  api.getDashboard.mockResolvedValue(MOCK_DASHBOARD_WITH_BATCH);
});

describe('Dashboard', () => {
  it('renders loading state initially', () => {
    api.getDashboard.mockImplementation(() => new Promise(() => {}));
    renderDashboard();
    expect(screen.getByText('Loading...')).toBeDefined();
  });

  it('renders profile name and XP', async () => {
    await act(async () => renderDashboard());
    await waitFor(() => expect(screen.getByTestId('dashboard')).toBeDefined());
    expect(screen.getByText('Rishi')).toBeDefined();
    expect(screen.getByText(/120 XP/)).toBeDefined();
  });

  it('renders current chapter and circle progress', async () => {
    await act(async () => renderDashboard());
    await waitFor(() => expect(screen.getByTestId('batch-progress')).toBeDefined());
    expect(screen.getByTestId('circle-progress')).toBeDefined();
  });

  it('renders speed trend when circle stats exist', async () => {
    await act(async () => renderDashboard());
    await waitFor(() => expect(screen.getByTestId('speed-trend')).toBeDefined());
    expect(screen.getByText('12.0s')).toBeDefined();
  });

  it('renders Continue Training button that links to session', async () => {
    await act(async () => renderDashboard());
    await waitFor(() => expect(screen.getByTestId('continue-training-btn')).toBeDefined());
    expect(screen.getByTestId('continue-training-btn').textContent).toBe('Continue Training');
  });

  it('renders Start Training button when no puzzles done today', async () => {
    api.getDashboard.mockResolvedValue({
      ...MOCK_DASHBOARD_WITH_BATCH,
      today: { puzzles_attempted: 0, puzzles_correct: 0, duration_seconds: 0 },
    });
    await act(async () => renderDashboard());
    await waitFor(() => expect(screen.getByTestId('continue-training-btn')).toBeDefined());
    expect(screen.getByTestId('continue-training-btn').textContent).toBe('Start Training');
  });

  it('shows Session Complete when daily cap hit', async () => {
    api.getDashboard.mockResolvedValue(MOCK_DASHBOARD_SESSION_CAP);
    await act(async () => renderDashboard());
    await waitFor(() => expect(screen.getByTestId('session-complete-message')).toBeDefined());
  });

  it('shows no batch message when has_active_batch is false', async () => {
    api.getDashboard.mockResolvedValue(MOCK_DASHBOARD_NO_BATCH);
    await act(async () => renderDashboard());
    await waitFor(() => expect(screen.getByTestId('no-batch')).toBeDefined());
  });

  it('shows graduation ready when status is ready_to_graduate', async () => {
    api.getDashboard.mockResolvedValue({
      ...MOCK_DASHBOARD_WITH_BATCH,
      training: { ...MOCK_DASHBOARD_WITH_BATCH.training, status: 'ready_to_graduate' },
    });
    await act(async () => renderDashboard());
    await waitFor(() => expect(screen.getByTestId('graduation-ready')).toBeDefined());
  });

  it('renders today stats section', async () => {
    await act(async () => renderDashboard());
    await waitFor(() => expect(screen.getByTestId('today-stats')).toBeDefined());
    expect(screen.getByText('5')).toBeDefined(); // puzzles attempted
  });
});

// ---------------------------------------------------------------------------
// CircleProgress tests
// ---------------------------------------------------------------------------
import CircleProgress from '../components/CircleProgress';

describe('CircleProgress', () => {
  it('renders 5 circle dots', () => {
    render(<CircleProgress currentCircle={1} />);
    expect(screen.getByTestId('circle-progress')).toBeDefined();
    for (let i = 1; i <= 5; i++) {
      expect(screen.getByTestId(`circle-dot-${i}`)).toBeDefined();
    }
  });

  it('renders correct circle label', () => {
    render(<CircleProgress currentCircle={3} />);
    expect(screen.getByText('Circle 3')).toBeDefined();
  });
});
