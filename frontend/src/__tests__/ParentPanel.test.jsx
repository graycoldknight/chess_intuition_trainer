/**
 * ParentPanel.test.jsx
 * Tests for the ParentPanel component (3 tabs: Chapters, Puzzle Review, Graduations).
 * RED phase: written before implementation.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ParentPanel from '../components/ParentPanel';

const renderPanel = () =>
  render(<MemoryRouter><ParentPanel /></MemoryRouter>);

// Mock the api module
vi.mock('../services/api', () => ({
  getChapters: vi.fn(),
  getPendingGraduations: vi.fn(),
  approveGraduation: vi.fn(),
  getUnverifiedPuzzles: vi.fn(),
  getParentActivity: vi.fn(),
}));

import * as api from '../services/api';

const MOCK_CHAPTERS = [
  { id: 1, title: 'Forks and Double Attacks', extraction_status: 'verified', puzzle_count: 50 },
  { id: 2, title: 'Pins and Skewers', extraction_status: 'pending', puzzle_count: 0 },
  { id: 3, title: 'Deflection and Decoy', extraction_status: 'review', puzzle_count: 30 },
];

const MOCK_GRADUATIONS = [
  {
    batch_id: 1,
    profile_id: 1,
    profile_name: 'Rishi',
    chapter_id: 1,
    chapter_title: 'Forks and Double Attacks',
    current_circle: 5,
    status: 'ready_to_graduate',
  },
];

const MOCK_PUZZLES = [
  {
    id: 1,
    puzzle_number: 1,
    fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
    turn: 'b',
    solution_san: 'e5',
    solution_uci: 'e7e5',
    verified: 0,
  },
];

describe('ParentPanel', () => {
  beforeEach(() => {
    api.getChapters.mockResolvedValue(MOCK_CHAPTERS);
    api.getPendingGraduations.mockResolvedValue(MOCK_GRADUATIONS);
    api.approveGraduation.mockResolvedValue({ batch_id: 1, status: 'graduated', next_chapter_id: 2 });
    api.getUnverifiedPuzzles.mockResolvedValue(MOCK_PUZZLES);
    api.getParentActivity.mockResolvedValue({ children: [] });
  });

  // ---------------------------------------------------------------------------
  // Structure
  // ---------------------------------------------------------------------------

  it('renders the parent panel container', async () => {
    renderPanel();
    await waitFor(() => expect(screen.getByTestId('parent-panel')).toBeDefined());
  });

  it('renders 3 tab buttons: Chapters, Puzzle Review, Graduations', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId('tab-chapters')).toBeDefined();
      expect(screen.getByTestId('tab-puzzle-review')).toBeDefined();
      expect(screen.getByTestId('tab-graduations')).toBeDefined();
    });
  });

  // ---------------------------------------------------------------------------
  // Chapters tab
  // ---------------------------------------------------------------------------

  it('shows Chapters tab content when Chapters tab is clicked', async () => {
    renderPanel();
    await waitFor(() => screen.getByTestId('tab-chapters'));
    fireEvent.click(screen.getByTestId('tab-chapters'));
    await waitFor(() => expect(screen.getByTestId('chapters-tab')).toBeDefined());
  });

  it('Chapters tab lists all chapters', async () => {
    renderPanel();
    await waitFor(() => screen.getByTestId('tab-chapters'));
    fireEvent.click(screen.getByTestId('tab-chapters'));
    await waitFor(() => {
      expect(screen.getByText('Forks and Double Attacks')).toBeDefined();
      expect(screen.getByText('Pins and Skewers')).toBeDefined();
      expect(screen.getByText('Deflection and Decoy')).toBeDefined();
    });
  });

  it('Chapters tab shows extraction status badge per chapter', async () => {
    renderPanel();
    await waitFor(() => screen.getByTestId('tab-chapters'));
    fireEvent.click(screen.getByTestId('tab-chapters'));
    await waitFor(() => {
      const verified = screen.getByTestId('status-badge-1');
      expect(verified).toBeDefined();
      expect(verified.dataset.status).toBe('verified');

      const pending = screen.getByTestId('status-badge-2');
      expect(pending.dataset.status).toBe('pending');
    });
  });

  // ---------------------------------------------------------------------------
  // Graduations tab
  // ---------------------------------------------------------------------------

  it('clicking Graduations tab shows graduations content', async () => {
    renderPanel();
    await waitFor(() => screen.getByTestId('tab-graduations'));
    fireEvent.click(screen.getByTestId('tab-graduations'));
    await waitFor(() => expect(screen.getByTestId('graduations-tab')).toBeDefined());
  });

  it('Graduations tab shows pending graduation rows', async () => {
    renderPanel();
    await waitFor(() => screen.getByTestId('tab-graduations'));
    fireEvent.click(screen.getByTestId('tab-graduations'));
    await waitFor(() => {
      expect(screen.getByTestId('graduation-row-1')).toBeDefined();
      expect(screen.getByText('Rishi')).toBeDefined();
    });
  });

  it('Graduations tab shows Approve button per graduation', async () => {
    renderPanel();
    await waitFor(() => screen.getByTestId('tab-graduations'));
    fireEvent.click(screen.getByTestId('tab-graduations'));
    await waitFor(() => {
      expect(screen.getByTestId('approve-btn-1')).toBeDefined();
    });
  });

  it('clicking Approve calls approveGraduation API', async () => {
    renderPanel();
    await waitFor(() => screen.getByTestId('tab-graduations'));
    fireEvent.click(screen.getByTestId('tab-graduations'));
    await waitFor(() => screen.getByTestId('approve-btn-1'));
    fireEvent.click(screen.getByTestId('approve-btn-1'));
    await waitFor(() => {
      expect(api.approveGraduation).toHaveBeenCalledWith(1);
    });
  });

  it('after Approve the row updates to graduated status', async () => {
    renderPanel();
    await waitFor(() => screen.getByTestId('tab-graduations'));
    fireEvent.click(screen.getByTestId('tab-graduations'));
    await waitFor(() => screen.getByTestId('approve-btn-1'));
    fireEvent.click(screen.getByTestId('approve-btn-1'));
    await waitFor(() => {
      const row = screen.getByTestId('graduation-row-1');
      expect(row.dataset.status).toBe('graduated');
    });
  });

  // ---------------------------------------------------------------------------
  // Puzzle Review tab
  // ---------------------------------------------------------------------------

  it('clicking Puzzle Review tab shows puzzle review content', async () => {
    renderPanel();
    await waitFor(() => screen.getByTestId('tab-puzzle-review'));
    fireEvent.click(screen.getByTestId('tab-puzzle-review'));
    await waitFor(() => expect(screen.getByTestId('puzzle-review-tab')).toBeDefined());
  });
});
