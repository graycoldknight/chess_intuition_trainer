/**
 * Animations.test.jsx
 * Tests for celebration animations: confetti on correct solve and XP popup.
 * Also tests board orientation based on puzzle.turn field.
 */

import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import TrainingSession from '../components/TrainingSession';
import ConfettiOverlay from '../components/ConfettiOverlay';
import XpPopup from '../components/XpPopup';
import * as api from '../services/api';

vi.mock('../services/api');
// react-confetti uses canvas which jsdom doesn't support — mock it to a simple div
vi.mock('react-confetti', () => ({
  default: () => <canvas data-testid="mock-confetti" />,
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const MOCK_PUZZLE_WHITE = {
  id: 1,
  chapter_id: 1,
  puzzle_number: 1,
  fen: 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
  turn: 'w',
  solution_san: 'Bxf7+',
  solution_uci: 'c4f7',
  solution_line: '1.Bxf7+',
};

const MOCK_PUZZLE_BLACK = {
  ...MOCK_PUZZLE_WHITE,
  turn: 'b',
  solution_san: 'Nxe4',
  solution_uci: 'f6e4',
};

const MOCK_STATE = {
  has_active_batch: true,
  batch_id: 1,
  chapter_id: 1,
  current_circle: 1,
  total_puzzles: 3,
  status: 'active',
  session: { id: 1, started_at: new Date().toISOString(), puzzles_attempted: 0, puzzles_correct: 0 },
};

function renderSession(puzzle = MOCK_PUZZLE_WHITE) {
  api.getTrainingState.mockResolvedValue(MOCK_STATE);
  api.startSession.mockResolvedValue({ id: 1, started_at: new Date().toISOString() });
  api.getNextPuzzle.mockResolvedValue({ puzzle });
  api.recordAttempt.mockResolvedValue({ attempt_id: 1, success: true, xp_earned: 10, new_badges: [] });

  return render(
    <MemoryRouter initialEntries={['/train/1']}>
      <Routes>
        <Route path="/train/:profileId" element={<TrainingSession />} />
        <Route path="/results/:profileId" element={<div>Results</div>} />
        <Route path="/" element={<div>Home</div>} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => vi.clearAllMocks());
afterEach(() => vi.clearAllMocks());

// ---------------------------------------------------------------------------
// ConfettiOverlay unit tests
// ---------------------------------------------------------------------------

describe('ConfettiOverlay', () => {
  it('does not render confetti canvas when active is false', () => {
    const { container } = render(<ConfettiOverlay active={false} />);
    const canvas = container.querySelector('canvas');
    expect(canvas).toBeNull();
  });

  it('renders confetti canvas when active is true', () => {
    const { container } = render(<ConfettiOverlay active={true} />);
    const canvas = container.querySelector('canvas');
    expect(canvas).not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// XpPopup unit tests
// ---------------------------------------------------------------------------

describe('XpPopup', () => {
  it('does not render when xp is null', () => {
    const { container } = render(<XpPopup xp={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders XP value when xp is provided', () => {
    render(<XpPopup xp={10} />);
    expect(screen.getByTestId('xp-popup')).toBeDefined();
    expect(screen.getByText('+10 XP')).toBeDefined();
  });

  it('renders correct value for different XP amounts', () => {
    render(<XpPopup xp={25} />);
    expect(screen.getByText('+25 XP')).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Board orientation tests (via TrainingSession)
// ---------------------------------------------------------------------------

describe('Board orientation based on turn', () => {
  it('renders chessboard when puzzle has white to move', async () => {
    await act(async () => {
      renderSession(MOCK_PUZZLE_WHITE);
    });

    await waitFor(() => {
      expect(screen.getByTestId('chessboard-container')).toBeDefined();
      expect(screen.getByText(/White to move/)).toBeDefined();
    });
  });

  it('renders chessboard when puzzle has black to move', async () => {
    await act(async () => {
      renderSession(MOCK_PUZZLE_BLACK);
    });

    await waitFor(() => {
      expect(screen.getByTestId('chessboard-container')).toBeDefined();
      expect(screen.getByText(/Black to move/)).toBeDefined();
    });
  });

  it('shows confetti overlay container in training session (wired up)', async () => {
    await act(async () => {
      renderSession(MOCK_PUZZLE_WHITE);
    });

    await waitFor(() => {
      expect(screen.getByTestId('confetti-overlay')).toBeDefined();
    });
  });
});
