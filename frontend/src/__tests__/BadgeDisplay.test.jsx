/**
 * BadgeDisplay.test.jsx
 * Tests for the BadgeDisplay component.
 * RED phase: written before implementation.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import BadgeDisplay from '../components/BadgeDisplay';

const ALL_BADGES = [
  { id: 1, key: 'fork_master', name: 'Fork Master', category: 'theme', icon: 'fork', description: 'Graduate Ch 1' },
  { id: 2, key: 'lightning_reflexes', name: 'Lightning Reflexes', category: 'speed', icon: 'zap', description: 'Solve in <3s' },
  { id: 3, key: 'first_solve', name: 'First Solve', category: 'milestone', icon: 'star', description: 'First puzzle' },
  { id: 4, key: 'streak_3', name: 'On a Roll', category: 'streak', icon: 'flame', description: '3-day streak' },
];

const EARNED_IDS = [1, 3];  // fork_master and first_solve earned

describe('BadgeDisplay', () => {
  it('renders earned badges', () => {
    render(<BadgeDisplay badges={ALL_BADGES} earnedIds={EARNED_IDS} />);
    const container = screen.getByTestId('badge-display');
    expect(container).toBeDefined();
  });

  it('shows earned badge as unlocked (not grayed)', () => {
    render(<BadgeDisplay badges={ALL_BADGES} earnedIds={EARNED_IDS} />);
    const earnedBadge = screen.getByTestId('badge-fork_master');
    // Earned badges should NOT have the locked class/attribute
    expect(earnedBadge.dataset.locked).toBe('false');
  });

  it('shows unearned badge as locked', () => {
    render(<BadgeDisplay badges={ALL_BADGES} earnedIds={EARNED_IDS} />);
    const lockedBadge = screen.getByTestId('badge-lightning_reflexes');
    expect(lockedBadge.dataset.locked).toBe('true');
  });

  it('renders badge name for earned badges', () => {
    render(<BadgeDisplay badges={ALL_BADGES} earnedIds={EARNED_IDS} />);
    expect(screen.getByText('Fork Master')).toBeDefined();
    expect(screen.getByText('First Solve')).toBeDefined();
  });

  it('renders all badges (earned and unearned)', () => {
    render(<BadgeDisplay badges={ALL_BADGES} earnedIds={EARNED_IDS} />);
    // All 4 badges should be rendered
    for (const badge of ALL_BADGES) {
      expect(screen.getByTestId(`badge-${badge.key}`)).toBeDefined();
    }
  });
});
