/**
 * SessionResume.test.jsx
 * Tests for localStorage-based session resume.
 * - State is saved when a puzzle is solved
 * - State is restored on page reload (same day)
 * - Stale state from a different day is discarded
 */

import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import TrainingSession from '../components/TrainingSession';
import * as api from '../services/api';
import {
  saveSessionToStorage,
  loadSessionFromStorage,
  clearSessionFromStorage,
  SESSION_STORAGE_KEY,
} from '../services/sessionStorage';

vi.mock('../services/api');

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const TODAY = new Date().toISOString().slice(0, 10); // "YYYY-MM-DD"
const YESTERDAY = new Date(Date.now() - 86400000).toISOString().slice(0, 10);

const MOCK_PUZZLE = {
  id: 5,
  chapter_id: 1,
  puzzle_number: 5,
  fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
  turn: 'b',
  solution_san: 'e5',
  solution_uci: 'e7e5',
  solution_line: '1...e5',
};

const MOCK_STATE = {
  has_active_batch: true,
  batch_id: 2,
  chapter_id: 1,
  current_circle: 2,
  total_puzzles: 50,
  status: 'active',
  session: { id: 3, started_at: new Date().toISOString(), puzzles_attempted: 4, puzzles_correct: 4 },
};

function renderSession(profileId = '1') {
  api.getTrainingState.mockResolvedValue(MOCK_STATE);
  api.startSession.mockResolvedValue({ id: 3, started_at: new Date().toISOString() });
  api.getNextPuzzle.mockResolvedValue({ puzzle: MOCK_PUZZLE });
  api.recordAttempt.mockResolvedValue({ attempt_id: 10, success: true, xp_earned: 10, new_badges: [] });

  return render(
    <MemoryRouter initialEntries={[`/train/${profileId}`]}>
      <Routes>
        <Route path="/train/:profileId" element={<TrainingSession />} />
        <Route path="/results/:profileId" element={<div>Results</div>} />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

afterEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

// ---------------------------------------------------------------------------
// sessionStorage service unit tests
// ---------------------------------------------------------------------------

describe('sessionStorage service', () => {
  it('saves session state to localStorage', () => {
    const state = { profileId: 1, batchId: 2, circle: 1, puzzleIndex: 4, date: TODAY };
    saveSessionToStorage(state);
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    expect(raw).not.toBeNull();
    // Storage is keyed by profileId string: { '1': { profileId, ... } }
    const parsed = JSON.parse(raw);
    expect(parsed['1'].profileId).toBe(1);
    expect(parsed['1'].puzzleIndex).toBe(4);
    expect(parsed['1'].date).toBe(TODAY);
  });

  it('loads session state from localStorage', () => {
    const state = { profileId: 1, batchId: 2, circle: 1, puzzleIndex: 4, date: TODAY };
    saveSessionToStorage(state);
    const loaded = loadSessionFromStorage(1);
    expect(loaded).not.toBeNull();
    expect(loaded.batchId).toBe(2);
    expect(loaded.circle).toBe(1);
  });

  it('returns null when no session exists for profile', () => {
    const result = loadSessionFromStorage(99);
    expect(result).toBeNull();
  });

  it('returns null for a different profileId', () => {
    const state = { profileId: 1, batchId: 2, circle: 1, puzzleIndex: 4, date: TODAY };
    saveSessionToStorage(state);
    const result = loadSessionFromStorage(2);
    expect(result).toBeNull();
  });

  it('clears session state from localStorage', () => {
    const state = { profileId: 1, batchId: 2, circle: 1, puzzleIndex: 4, date: TODAY };
    saveSessionToStorage(state);
    clearSessionFromStorage(1);
    expect(loadSessionFromStorage(1)).toBeNull();
  });

  it('discards stale session from a different day', () => {
    const staleState = { profileId: 1, batchId: 2, circle: 1, puzzleIndex: 10, date: YESTERDAY };
    saveSessionToStorage(staleState);
    const result = loadSessionFromStorage(1);
    // loadSessionFromStorage returns null if date !== today
    expect(result).toBeNull();
  });

  it('returns fresh session when date matches today', () => {
    const state = { profileId: 1, batchId: 2, circle: 1, puzzleIndex: 10, date: TODAY };
    saveSessionToStorage(state);
    const result = loadSessionFromStorage(1);
    expect(result).not.toBeNull();
    expect(result.puzzleIndex).toBe(10);
  });
});

// ---------------------------------------------------------------------------
// TrainingSession + localStorage integration tests
// ---------------------------------------------------------------------------

describe('TrainingSession session resume', () => {
  it('renders training session without crashing when no localStorage state exists', async () => {
    await act(async () => {
      renderSession('1');
    });

    await waitFor(() => {
      expect(screen.getByTestId('training-session')).toBeDefined();
    });
  });

  it('renders training session with stale localStorage state without crashing', async () => {
    // Pre-seed stale state
    const staleState = { profileId: 1, batchId: 99, circle: 3, puzzleIndex: 15, date: YESTERDAY };
    saveSessionToStorage(staleState);

    await act(async () => {
      renderSession('1');
    });

    // Should still load fresh state from API (stale state discarded)
    await waitFor(() => {
      expect(screen.getByTestId('training-session')).toBeDefined();
    });
    // API still called because stale state was ignored
    expect(api.getTrainingState).toHaveBeenCalledWith(1);
  });
});
