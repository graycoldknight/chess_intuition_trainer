/**
 * Phase 3 Playwright E2E tests: Core Training Loop
 *
 * Prerequisites (must be running before test):
 *   - Backend:  cd backend && uvicorn main:app --port 8000
 *   - Frontend: cd frontend && npm run dev
 *   - DB state: Chapter 1 puzzles loaded, batch created for Rishi (profile 1)
 *
 * Run: npx playwright test e2e/tests/phase3_training.spec.ts
 */

import { test, expect, request as playwrightRequest } from '@playwright/test';

const BASE = 'http://localhost:5173';
const API  = 'http://localhost:8000';

/**
 * End any open sessions for a profile and start a fresh one.
 * This ensures `get_next_puzzle` works (session cap not hit) and
 * the Dashboard shows the "Continue Training" button.
 */
async function resetSession(profileId: number) {
  const ctx = await playwrightRequest.newContext();

  // Get current training state to find open session IDs
  const stateRes = await ctx.get(`${API}/api/training/state/${profileId}`);
  const state = await stateRes.json();

  if (state.session?.id) {
    await ctx.post(`${API}/api/training/end-session/${state.session.id}`);
  }

  // Start a fresh session
  await ctx.post(`${API}/api/training/start-session/${profileId}`);
  await ctx.dispose();
}

// ---------------------------------------------------------------------------
// ProfileSelect — no session needed
// ---------------------------------------------------------------------------
test.describe('Phase 3: ProfileSelect', () => {

  test('shows Rishi and Raghav cards', async ({ page }) => {
    await page.goto(BASE);
    await expect(page.locator('[data-testid="profile-rishi"]')).toBeVisible();
    await expect(page.locator('[data-testid="profile-raghav"]')).toBeVisible();
  });

  test('clicking Rishi navigates to his dashboard', async ({ page }) => {
    await page.goto(BASE);
    await page.click('[data-testid="profile-rishi"]');
    await expect(page).toHaveURL(/\/dashboard\/1/);
    await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    await expect(page.locator('[data-testid="dashboard"]')).toContainText('Rishi');
  });

  test('clicking Raghav navigates to his dashboard', async ({ page }) => {
    await page.goto(BASE);
    await page.click('[data-testid="profile-raghav"]');
    await expect(page).toHaveURL(/\/dashboard\/2/);
    await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    await expect(page.locator('[data-testid="dashboard"]')).toContainText('Raghav');
  });

});

// ---------------------------------------------------------------------------
// TrainingSession — requires fresh session so puzzle serving works
// ---------------------------------------------------------------------------
test.describe('Phase 3: TrainingSession', () => {

  test.beforeEach(async () => {
    await resetSession(1);
  });

  test('Continue Training button is visible on dashboard and navigates to TrainingSession', async ({ page }) => {
    await page.goto(`${BASE}/dashboard/1`);
    const btn = page.locator('[data-testid="continue-training-btn"]');
    await expect(btn).toBeVisible();
    await btn.click();
    await expect(page).toHaveURL(/\/train\/1/);
    await expect(page.locator('[data-testid="training-session"]')).toBeVisible({ timeout: 10000 });
  });

  test('TrainingSession renders a chessboard with pieces', async ({ page }) => {
    await page.goto(`${BASE}/train/1`);
    await expect(page.locator('[data-testid="training-session"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="chessboard-container"]')).toBeVisible();
    // react-chessboard renders pieces as divs with data-piece attribute (SVG inline)
    const pieces = page.locator('[data-testid="chessboard-container"] [data-piece]');
    await expect(pieces.first()).toBeVisible({ timeout: 10000 });
  });

  test('puzzle info shows circle number and whose move it is', async ({ page }) => {
    await page.goto(`${BASE}/train/1`);
    await expect(page.locator('[data-testid="training-session"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=/Circle \\d/')).toBeVisible();
    await expect(page.locator('text=/White to move|Black to move/')).toBeVisible();
  });

  test('session timer is visible while puzzle is active', async ({ page }) => {
    await page.goto(`${BASE}/train/1`);
    await expect(page.locator('[data-testid="training-session"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('[data-testid="session-timer"]')).toBeVisible();
  });

  test('back button returns to ProfileSelect', async ({ page }) => {
    await page.goto(`${BASE}/train/1`);
    await expect(page.locator('[data-testid="training-session"]')).toBeVisible({ timeout: 10000 });
    await page.click('button:has-text("Rishi")');
    await expect(page).toHaveURL('/');
    await expect(page.locator('[data-testid="profile-rishi"]')).toBeVisible();
  });

});

// ---------------------------------------------------------------------------
// Edge case — no batch
// ---------------------------------------------------------------------------
test.describe('Phase 3: Edge cases', () => {

  test('no active batch shows graceful error, not a crash', async ({ page }) => {
    // Profile 3 (Raj) has no training batch
    await page.goto(`${BASE}/train/3`);
    await expect(page.locator('text=/No active batch/')).toBeVisible({ timeout: 10000 });
  });

});
