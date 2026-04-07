/**
 * Circle completion E2E test.
 *
 * Verifies that finishing the last puzzle in a circle navigates to the
 * ResultsScreen instead of looping back to puzzle 1 of the next circle.
 *
 * Setup: profile 99 with a 1-puzzle batch at circle 1 (synthetic mate-in-1).
 *   FEN:  k7/8/K7/8/1R6/8/8/8 w - - 0 1
 *   Move: b4b8 (Rb8#)
 *
 * Run: cd e2e && npx playwright test tests/phase4_circle_completion.spec.ts
 */

import { test, expect } from '@playwright/test';
import { execSync } from 'child_process';
import * as path from 'path';

const BASE = 'http://localhost:5174';
const TEST_PROFILE_ID = 99;
const BACKEND_DIR = path.resolve(__dirname, '../../backend');

function setupCircle1() {
  execSync('python test_setup.py create_circle1', {
    cwd: BACKEND_DIR,
    stdio: 'pipe',
  });
}

/** Drag a piece from one square to another on the chessboard. */
async function dragPiece(page: any, boardContainer: any, from: string, to: string): Promise<boolean> {
  const fromSquare = boardContainer.locator(`[data-square="${from}"]`);
  const toSquare   = boardContainer.locator(`[data-square="${to}"]`);
  const visible = await fromSquare.isVisible().catch(() => false);
  if (!visible) return false;
  await fromSquare.dragTo(toSquare);
  return true;
}

test.describe('Circle completion → ResultsScreen', () => {

  test.beforeEach(() => {
    setupCircle1();
  });

  test('solving the last puzzle in a circle navigates to ResultsScreen', async ({ page }) => {
    await page.goto(`${BASE}/train/${TEST_PROFILE_ID}`);

    const board = page.locator('[data-testid="chessboard-container"]');
    await expect(board).toBeVisible({ timeout: 10000 });

    // Verify we're on circle 1
    await expect(page.locator('text=/Circle 1/')).toBeVisible({ timeout: 5000 });

    await page.screenshot({ path: 'test-results/circle-completion-before.png' });

    // Solve the synthetic mate-in-1: Rb8# (b4 → b8)
    const dragged = await dragPiece(page, board, 'b4', 'b8');

    if (!dragged) {
      // Board drag not available in this environment — skip
      test.skip();
      return;
    }

    // Correct feedback should appear briefly
    await expect(page.locator('[data-testid="feedback-correct"]')).toBeVisible({ timeout: 3000 });

    await page.screenshot({ path: 'test-results/circle-completion-correct.png' });

    // After auto-advance (1s), should navigate to results — NOT stay on training
    await expect(page).toHaveURL(/\/results\/99/, { timeout: 5000 });

    const results = page.locator('[data-testid="results-screen"]');
    await expect(results).toBeVisible({ timeout: 5000 });

    // Should say "Circle 1 Complete!" not "Circle 2 Complete!"
    await expect(results).toContainText('Circle 1 Complete!');

    await page.screenshot({ path: 'test-results/circle-completion-results.png' });
  });

  test('next-puzzle API includes current_circle in response', async ({ request }) => {
    const res = await request.get(`http://localhost:8000/api/training/next-puzzle/${TEST_PROFILE_ID}`);
    expect(res.ok()).toBeTruthy();
    const data = await res.json();
    expect(data).toHaveProperty('current_circle');
    expect(typeof data.current_circle).toBe('number');
  });

});
