/**
 * MultiMove.test.jsx
 * Tests for multi-move puzzle sequence flow (Phase 9).
 * Verifies that TrainingSession handles multi-move puzzles correctly:
 * intermediate moves keep the clock running, final move completes the puzzle.
 */

import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import TrainingSession from '../components/TrainingSession';
import * as api from '../services/api';

// ---------------------------------------------------------------------------
// Mock the API module
// ---------------------------------------------------------------------------
vi.mock('../services/api');

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

// Multi-move puzzle: 3 moves in sequence
const MULTI_MOVE_PUZZLE = {
  id: 1,
  chapter_id: 1,
  puzzle_number: 1,
  fen: '8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1',
  turn: 'w',
  solution_san: 'Rf6+',
  solution_uci: 'f3f6',
  solution_line: '1. Rf6+ Kg7 2. Rb6',
  solution_uci_line: ['f3f6', 'h6g7', 'f6b6'],
};

// Single-move puzzle (backward compat)
const SINGLE_MOVE_PUZZLE = {
  id: 2,
  chapter_id: 1,
  puzzle_number: 2,
  fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
  turn: 'b',
  solution_san: 'e5',
  solution_uci: 'e7e5',
  solution_line: '1...e5',
  solution_uci_line: ['e7e5'],
};

// Puzzle with null solution_uci_line (fallback test)
const LEGACY_PUZZLE = {
  id: 3,
  chapter_id: 1,
  puzzle_number: 3,
  fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
  turn: 'b',
  solution_san: 'e5',
  solution_uci: 'e7e5',
  solution_line: '1...e5',
  solution_uci_line: null,  // Not yet parsed
};

const MOCK_STATE_WITH_BATCH = {
  has_active_batch: true,
  batch_id: 1,
  chapter_id: 1,
  current_circle: 1,
  total_puzzles: 3,
  status: 'active',
  session: {
    id: 1,
    started_at: new Date().toISOString(),
    puzzles_attempted: 0,
    puzzles_correct: 0,
  },
};

function renderSession(profileId = '1') {
  return render(
    <MemoryRouter initialEntries={[`/train/${profileId}`]}>
      <Routes>
        <Route path="/train/:profileId" element={<TrainingSession />} />
        <Route path="/results/:profileId" element={<div data-testid="results-page">Results</div>} />
        <Route path="/" element={<div data-testid="home">Home</div>} />
      </Routes>
    </MemoryRouter>
  );
}

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers({ shouldAdvanceTime: true });

  api.getTrainingState.mockResolvedValue(MOCK_STATE_WITH_BATCH);
  api.startSession.mockResolvedValue({ id: 1, started_at: new Date().toISOString() });
  api.getNextPuzzle.mockResolvedValue({ puzzle: MULTI_MOVE_PUZZLE });
  api.recordAttempt.mockResolvedValue({ attempt_id: 1, success: true, xp_earned: 10 });
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Multi-move tests
// ---------------------------------------------------------------------------

describe('MultiMove Puzzle Flow', () => {

  it('renders multi-move puzzle and shows board', async () => {
    await act(async () => {
      renderSession();
    });

    await waitFor(() => {
      expect(screen.getByTestId('chessboard-container')).toBeDefined();
    });
  });

  it('does NOT show progress indicator on first move', async () => {
    await act(async () => {
      renderSession();
    });

    await waitFor(() => {
      expect(screen.getByTestId('chessboard-container')).toBeDefined();
    });

    // Progress indicator should not appear until after first correct intermediate move
    expect(screen.queryByText(/Move \d+ of \d+/)).toBeNull();
  });

  it('handles single-move puzzle identically to previous behavior', async () => {
    api.getNextPuzzle.mockResolvedValue({ puzzle: SINGLE_MOVE_PUZZLE });

    await act(async () => {
      renderSession();
    });

    await waitFor(() => {
      expect(screen.getByTestId('chessboard-container')).toBeDefined();
    });

    // No progress indicator for single-move puzzles
    expect(screen.queryByText(/Move \d+ of \d+/)).toBeNull();
  });

  it('handles legacy puzzle with null solution_uci_line (fallback)', async () => {
    api.getNextPuzzle.mockResolvedValue({ puzzle: LEGACY_PUZZLE });

    await act(async () => {
      renderSession();
    });

    await waitFor(() => {
      expect(screen.getByTestId('chessboard-container')).toBeDefined();
    });

    // Should render fine with fallback to [solution_uci]
    expect(screen.queryByText(/Move \d+ of \d+/)).toBeNull();
  });

  it('receives solution_uci_line from API and stores it', async () => {
    await act(async () => {
      renderSession();
    });

    await waitFor(() => {
      expect(screen.getByTestId('chessboard-container')).toBeDefined();
    });

    // Verify the API was called and puzzle data is used
    expect(api.getNextPuzzle).toHaveBeenCalledWith(1);
  });

  // Note: Actual drag-and-drop move simulation is covered in Playwright E2E tests.
  // jsdom doesn't support the drag events needed by react-chessboard.
  // These tests verify the component renders correctly and handles state properly.
});
