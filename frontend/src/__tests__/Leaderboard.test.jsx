/**
 * Leaderboard.test.jsx
 * Tests for the Leaderboard component.
 * RED phase: written before implementation.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import Leaderboard from '../components/Leaderboard';

const MOCK_LEADERBOARD = [
  {
    id: 1,
    name: 'Rishi',
    total_xp: 320,
    current_streak: 5,
    chapters_graduated: 2,
    best_puzzle_time_ms: 1800,
  },
  {
    id: 2,
    name: 'Raghav',
    total_xp: 180,
    current_streak: 7,
    chapters_graduated: 1,
    best_puzzle_time_ms: 2100,
  },
];

describe('Leaderboard', () => {
  it('renders both kids side by side', () => {
    render(<Leaderboard data={MOCK_LEADERBOARD} />);
    const board = screen.getByTestId('leaderboard');
    expect(board).toBeDefined();
    expect(screen.getByTestId('leaderboard-rishi')).toBeDefined();
    expect(screen.getByTestId('leaderboard-raghav')).toBeDefined();
  });

  it('shows player names', () => {
    render(<Leaderboard data={MOCK_LEADERBOARD} />);
    expect(screen.getByText('Rishi')).toBeDefined();
    expect(screen.getByText('Raghav')).toBeDefined();
  });

  it('shows XP for each player', () => {
    render(<Leaderboard data={MOCK_LEADERBOARD} />);
    expect(screen.getByText('320')).toBeDefined();
    expect(screen.getByText('180')).toBeDefined();
  });

  it('shows streak for each player', () => {
    render(<Leaderboard data={MOCK_LEADERBOARD} />);
    expect(screen.getByText('5')).toBeDefined();  // Rishi streak
    expect(screen.getByText('7')).toBeDefined();  // Raghav streak
  });

  it('highlights the XP leader', () => {
    render(<Leaderboard data={MOCK_LEADERBOARD} />);
    // Rishi has more XP -- his XP cell should be marked as leader
    const rishiXp = screen.getByTestId('leaderboard-rishi-xp');
    expect(rishiXp.dataset.leader).toBe('true');
  });

  it('highlights the streak leader', () => {
    render(<Leaderboard data={MOCK_LEADERBOARD} />);
    // Raghav has longer streak
    const raghavStreak = screen.getByTestId('leaderboard-raghav-streak');
    expect(raghavStreak.dataset.leader).toBe('true');
  });

  it('shows chapters graduated metric', () => {
    render(<Leaderboard data={MOCK_LEADERBOARD} />);
    // Rishi: 2 chapters, Raghav: 1 chapter
    const rishiChapters = screen.getByTestId('leaderboard-rishi-chapters');
    expect(rishiChapters).toBeDefined();
    expect(screen.getByText('2')).toBeDefined();
  });

  it('renders leaderboard with empty data', () => {
    render(<Leaderboard data={[]} />);
    expect(screen.getByTestId('leaderboard')).toBeDefined();
  });

  it('renders higher-XP player before lower-XP player', () => {
    const data = [
      { id: 1, name: 'Rishi',  total_xp: 643,  current_streak: 3, chapters_graduated: 0 },
      { id: 2, name: 'Raghav', total_xp: 1494, current_streak: 1, chapters_graduated: 0 },
    ];
    render(<Leaderboard data={data} />);
    const rows = screen.getAllByRole('row');
    // rows[0] is the header, rows[1] should be Raghav (higher XP)
    expect(rows[1]).toHaveTextContent('Raghav');
    expect(rows[2]).toHaveTextContent('Rishi');
  });
});
