/**
 * ResultsScreen.test.jsx
 * Tests for the post-circle results screen.
 */

import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import ResultsScreen from '../components/ResultsScreen';
import * as api from '../services/api';

vi.mock('../services/api');

function makeDashboard({ currentCircle = 2, status = 'active', circleStats = {} } = {}) {
  return {
    profile: { id: 1, name: 'Rishi', total_xp: 0, current_streak: 0, longest_streak: 0 },
    training: {
      has_active_batch: true,
      batch_id: 1,
      chapter_id: 1,
      current_circle: currentCircle,
      total_puzzles: 50,
      status,
      circle_stats: circleStats,
      session_time_remaining_seconds: 3000,
    },
    today: { puzzles_attempted: 50, puzzles_correct: 45, duration_seconds: 600 },
  };
}

function renderResults(profileId = '1') {
  return render(
    <MemoryRouter initialEntries={[`/results/${profileId}`]}>
      <Routes>
        <Route path="/results/:profileId" element={<ResultsScreen />} />
        <Route path="/train/:profileId" element={<div data-testid="training">Training</div>} />
        <Route path="/dashboard/:profileId" element={<div data-testid="dashboard-page">Dashboard</div>} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  api.getDashboard.mockResolvedValue(
    makeDashboard({
      currentCircle: 2,
      circleStats: { '1': { total: 50, correct: 45, avg_time_ms: 12000 } },
    })
  );
});

describe('ResultsScreen', () => {
  it('renders loading state initially', () => {
    api.getDashboard.mockImplementation(() => new Promise(() => {}));
    renderResults();
    expect(screen.getByText('Loading results...')).toBeDefined();
  });

  it('renders circle complete heading', async () => {
    await act(async () => renderResults());
    await waitFor(() => expect(screen.getByTestId('results-screen')).toBeDefined());
    expect(screen.getByText(/Circle 1 Complete/)).toBeDefined();
  });

  it('renders circle stats with accuracy and avg time', async () => {
    await act(async () => renderResults());
    await waitFor(() => expect(screen.getByTestId('circle-stats')).toBeDefined());
    expect(screen.getByText('90%')).toBeDefined();   // 45/50 accuracy
    expect(screen.getByText('12.0s')).toBeDefined(); // avg time
    expect(screen.getByText('45/50')).toBeDefined(); // correct/total
  });

  it('shows improvement percentage vs previous circle when available', async () => {
    api.getDashboard.mockResolvedValue(
      makeDashboard({
        currentCircle: 3,
        circleStats: {
          '1': { total: 50, correct: 45, avg_time_ms: 15000 },
          '2': { total: 50, correct: 48, avg_time_ms: 12000 },
        },
      })
    );
    await act(async () => renderResults());
    await waitFor(() => expect(screen.getByTestId('improvement')).toBeDefined());
    expect(screen.getByTestId('improvement').textContent).toMatch(/20%.*faster/);
  });

  it('shows Ready to Graduate when threshold met', async () => {
    api.getDashboard.mockResolvedValue(
      makeDashboard({
        currentCircle: 6,
        status: 'ready_to_graduate',
        circleStats: {
          '5': { total: 50, correct: 50, avg_time_ms: 10000 },
        },
      })
    );
    await act(async () => renderResults());
    await waitFor(() => expect(screen.getByTestId('graduation-ready')).toBeDefined());
  });

  it('renders Start Circle N button linking to training', async () => {
    await act(async () => renderResults());
    await waitFor(() => expect(screen.getByTestId('start-next-circle-btn')).toBeDefined());
    expect(screen.getByTestId('start-next-circle-btn').textContent).toBe('Start Circle 2');
  });
});
