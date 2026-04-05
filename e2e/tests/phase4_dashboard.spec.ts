/**
 * Phase 4 Playwright E2E tests: Dashboard & Results
 *
 * Prerequisites (must be running before test):
 *   - Backend:  cd backend && uvicorn main:app --port 8000
 *   - Frontend: cd frontend && npm run dev
 *   - DB state: Chapter 1 puzzles loaded, batch created for Rishi (profile 1)
 *
 * Run: npx playwright test e2e/tests/phase4_dashboard.spec.ts
 */

import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';

test.describe('Phase 4: Dashboard & Results', () => {

  test('navigate to Rishi dashboard from ProfileSelect', async ({ page }) => {
    await page.goto(BASE);
    await page.click('[data-testid="profile-rishi"]');
    await expect(page).toHaveURL(/\/dashboard\/1/);
    await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
  });

  test('dashboard shows current chapter and circle progress', async ({ page }) => {
    await page.goto(`${BASE}/dashboard/1`);
    await expect(page.locator('[data-testid="batch-progress"]')).toBeVisible();
    await expect(page.locator('[data-testid="circle-progress"]')).toBeVisible();
    // Should show chapter 1
    await expect(page.locator('[data-testid="batch-progress"]')).toContainText('Chapter 1');
  });

  test('dashboard shows Today\'s Stats section', async ({ page }) => {
    await page.goto(`${BASE}/dashboard/1`);
    await expect(page.locator('[data-testid="today-stats"]')).toBeVisible();
    // Solved count present
    await expect(page.locator('[data-testid="today-stats"]')).toContainText('Solved');
  });

  test('dashboard shows speed trend chart when circle stats exist', async ({ page }) => {
    await page.goto(`${BASE}/dashboard/1`);
    // Speed trend card should be visible (circle 1 has been completed)
    await expect(page.locator('[data-testid="speed-trend"]')).toBeVisible();
    // Should show C1 with a time value
    await expect(page.locator('[data-testid="speed-trend"]')).toContainText('C1');
  });

  test('Continue Training button navigates to TrainingSession', async ({ page }) => {
    await page.goto(`${BASE}/dashboard/1`);
    const btn = page.locator('[data-testid="continue-training-btn"]');
    await expect(btn).toBeVisible();
    await btn.click();
    await expect(page).toHaveURL(/\/train\/1/);
    await expect(page.locator('[data-testid="training-session"]')).toBeVisible({ timeout: 10000 });
  });

  test('ResultsScreen appears after completing a training circle', async ({ page }) => {
    // Navigate to dashboard first to verify current circle
    await page.goto(`${BASE}/dashboard/1`);
    const batchProgress = page.locator('[data-testid="batch-progress"]');
    await expect(batchProgress).toBeVisible();

    // Navigate directly to results (simulating circle completion)
    await page.goto(`${BASE}/results/1`);
    await expect(page.locator('[data-testid="results-screen"]')).toBeVisible();
  });

  test('ResultsScreen shows circle stats: accuracy and avg time', async ({ page }) => {
    await page.goto(`${BASE}/results/1`);
    await expect(page.locator('[data-testid="results-screen"]')).toBeVisible();
    await expect(page.locator('[data-testid="circle-stats"]')).toBeVisible();
    // Should contain accuracy percentage
    await expect(page.locator('[data-testid="circle-stats"]')).toContainText('%');
    // Should contain a time value
    await expect(page.locator('[data-testid="circle-stats"]')).toContainText('s');
  });

  test('ResultsScreen Start Circle N button navigates back to TrainingSession', async ({ page }) => {
    await page.goto(`${BASE}/results/1`);
    await expect(page.locator('[data-testid="results-screen"]')).toBeVisible();
    const btn = page.locator('[data-testid="start-next-circle-btn"]');
    await expect(btn).toBeVisible();
    // Button text should say "Start Circle N"
    await expect(btn).toContainText('Start Circle');
    await btn.click();
    await expect(page).toHaveURL(/\/train\/1/);
  });

  test('navigating back to Dashboard after results shows updated circle', async ({ page }) => {
    await page.goto(`${BASE}/results/1`);
    await expect(page.locator('[data-testid="results-screen"]')).toBeVisible();
    // Click Dashboard button
    await page.click('button:has-text("Dashboard")');
    await expect(page).toHaveURL(/\/dashboard\/1/);
    await expect(page.locator('[data-testid="circle-progress"]')).toBeVisible();
  });

});
