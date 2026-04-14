# Phase 10.1: Challenge Mode Frontend/E2E Test Coverage

## Context

Phase 10 (commit `d503eea`) added randomized puzzle order for circles 6+, deferred graduation to circle 7, and a Challenge Mode badge in the UI. The backend has 7 tests in `test_training.py` covering shuffle logic and graduation deferral. What is missing: frontend tests for the Challenge Mode badge rendering, a verification doc, and a Playwright E2E test.

**Key decisions:**
- Frontend test for badge goes in `TrainingSession.test.jsx` (mocking `is_randomized_circle` in training state)
- Playwright E2E uses `test_setup.py create_circle1` helper to set up state, then API calls to fast-forward to circle 6
- Verification doc aggregates existing backend tests + new frontend/E2E tests

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/__tests__/TrainingSession.test.jsx` | Add tests for Challenge Mode badge |
| `verification/phase10_challenge_circles.md` | New verification doc |
| `e2e/tests/phase10_challenge_circles.spec.ts` | New Playwright E2E test |

---

## Implementation

### `frontend/src/__tests__/TrainingSession.test.jsx`

Add a new `describe` block:

```jsx
describe('TrainingSession - Challenge Mode badge', () => {
  it('renders Challenge Mode badge when is_randomized_circle is true', async () => {
    api.getTrainingState.mockResolvedValue({
      ...MOCK_STATE_WITH_BATCH,
      current_circle: 6,
      is_randomized_circle: true,
    });
    api.getNextPuzzle.mockResolvedValue({ puzzle: MOCK_PUZZLE });
    api.startSession.mockResolvedValue({ id: 1 });

    await act(async () => renderSession());
    await waitFor(() => {
      expect(screen.getByText(/Challenge Mode/)).toBeDefined();
    });
  });

  it('does not render Challenge Mode badge for circles 1-5', async () => {
    api.getTrainingState.mockResolvedValue({
      ...MOCK_STATE_WITH_BATCH,
      current_circle: 2,
      is_randomized_circle: false,
    });
    api.getNextPuzzle.mockResolvedValue({ puzzle: MOCK_PUZZLE });
    api.startSession.mockResolvedValue({ id: 1 });

    await act(async () => renderSession());
    await waitFor(() => {
      expect(screen.getByTestId('chessboard-container')).toBeDefined();
    });
    expect(screen.queryByText(/Challenge Mode/)).toBeNull();
  });

  it('does not render Challenge Mode badge when field is missing', async () => {
    const stateWithoutField = { ...MOCK_STATE_WITH_BATCH };
    delete stateWithoutField.is_randomized_circle;
    api.getTrainingState.mockResolvedValue(stateWithoutField);
    api.getNextPuzzle.mockResolvedValue({ puzzle: MOCK_PUZZLE });
    api.startSession.mockResolvedValue({ id: 1 });

    await act(async () => renderSession());
    await waitFor(() => {
      expect(screen.getByTestId('chessboard-container')).toBeDefined();
    });
    expect(screen.queryByText(/Challenge Mode/)).toBeNull();
  });
});
```

### `e2e/tests/phase10_challenge_circles.spec.ts`

```typescript
/**
 * Phase 10 Playwright E2E tests: Randomized Challenge Circles
 *
 * Prerequisites:
 *   - Backend:  cd backend && uvicorn main:app --port 8000
 *   - Frontend: cd frontend && npm run dev
 *   - DB state: test_setup.py create (profile 99 with active batch)
 *
 * Run: cd e2e && npx playwright test tests/phase10_challenge_circles.spec.ts
 */

import { test, expect, request as playwrightRequest } from '@playwright/test';

const BASE = 'http://localhost:5173';
const API  = 'http://localhost:8000';
const TEST_PROFILE_ID = 99;

async function getTrainingState() {
  const ctx = await playwrightRequest.newContext();
  const res = await ctx.get(`${API}/api/training/state/${TEST_PROFILE_ID}`);
  const data = await res.json();
  await ctx.dispose();
  return data;
}

async function resetTestSession() {
  const ctx = await playwrightRequest.newContext();
  const state = await (await ctx.get(`${API}/api/training/state/${TEST_PROFILE_ID}`)).json();
  if (state.session?.id) {
    await ctx.post(`${API}/api/training/end-session/${state.session.id}`);
  }
  await ctx.post(`${API}/api/training/start-session/${TEST_PROFILE_ID}`);
  await ctx.dispose();
}

test.describe('Phase 10: Randomized Challenge Circles', () => {
  test('training state API includes is_randomized_circle field', async () => {
    const state = await getTrainingState();
    expect(state).toHaveProperty('is_randomized_circle');
    expect(typeof state.is_randomized_circle).toBe('boolean');
  });

  test('Challenge Mode badge not visible at circle 1', async ({ page }) => {
    await resetTestSession();
    await page.goto(`${BASE}/train/${TEST_PROFILE_ID}`);

    // Wait for board to load
    await page.waitForSelector('[data-testid="chessboard-container"]', { timeout: 10000 });

    // Challenge Mode badge should NOT be visible at circle 1
    await expect(page.getByText(/Challenge Mode/)).not.toBeVisible();
  });

  test('training state returns correct is_randomized_circle for early circles', async () => {
    const state = await getTrainingState();
    if (state.current_circle && state.current_circle <= 5) {
      expect(state.is_randomized_circle).toBe(false);
    }
  });

  test('training state returns puzzle_ids for order comparison', async () => {
    const state = await getTrainingState();
    if (state.has_active_batch) {
      expect(Array.isArray(state.puzzle_ids)).toBe(true);
      expect(state.puzzle_ids.length).toBeGreaterThan(0);
    }
  });
});
```

Note: Testing circle 6+ behavior in E2E is impractical without fast-forwarding through 5 circles (250+ puzzle solves). The backend unit tests (`test_training.py`) already cover shuffle logic exhaustively. The E2E tests focus on what's visible -- the badge absence at early circles and the API field structure.

---

## Execution Workflow

### RED -- write tests first

```bash
cd frontend && npx vitest run src/__tests__/TrainingSession.test.jsx
```

Since the implementation already exists, tests should be **GREEN** immediately.

### GREEN -- verify all pass

```bash
cd backend && pytest -v
cd frontend && npm test
```

### SHOWBOAT -- `verification/phase10_challenge_circles.md`

```
showboat init verification/phase10_challenge_circles.md "Phase 10: Randomized Challenge Circles Verification"
showboat note verification/phase10_challenge_circles.md "Verify circles 6+ use randomized order, graduation deferred to circle 7, Challenge Mode badge"
showboat exec verification/phase10_challenge_circles.md bash "cd backend && pytest tests/test_training.py -v -k 'circle_6 or circle_7 or graduation or randomized or shuffle'"
showboat exec verification/phase10_challenge_circles.md bash "cd frontend && npx vitest run src/__tests__/TrainingSession.test.jsx 2>&1 | grep -E 'Challenge|passed|failed'"
showboat exec verification/phase10_challenge_circles.md bash "cd backend && pytest -v"
showboat note verification/phase10_challenge_circles.md "Training state API includes is_randomized_circle flag"
showboat exec verification/phase10_challenge_circles.md bash "curl -s http://localhost:8000/api/training/state/1 | python3 -c \"import sys,json; d=json.load(sys.stdin); print(f'is_randomized_circle={d.get(\\\"is_randomized_circle\\\")}')\""
showboat verify verification/phase10_challenge_circles.md
```

### PLAYWRIGHT -- `e2e/tests/phase10_challenge_circles.spec.ts`

Both servers must be running (`./test.sh`).

- Assert `is_randomized_circle` field exists in training state API
- Assert Challenge Mode badge NOT visible at circle 1
- Assert `is_randomized_circle` is `false` for circles 1-5
- Assert `puzzle_ids` array present for order comparison

All existing Playwright tests must remain green.
