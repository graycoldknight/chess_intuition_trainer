# Phase 9.7: Show Answer + Solution Editing Test Coverage

## Context

Phase 9.6 (commit `8463f28`) added the "Answer" toggle button for profile 99, a solution display panel (SAN + UCI line), edit mode with solution field inputs, and a `PUT /api/puzzles/{puzzle_id}/solution` endpoint (`main.py:459-482`). This was 423 lines of frontend changes and a new backend endpoint -- all with zero tests.

**Key decisions:**
- Backend API tests for the PUT solution endpoint go in `test_training_api.py`
- Frontend tests for Answer toggle go in `TrainingSession.test.jsx` (profile 99 behavior)
- Playwright E2E tests exercise the full toggle flow in the browser
- Verification doc covers both API and UI behavior

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/tests/test_training_api.py` | Add tests for `PUT /api/puzzles/{id}/solution` |
| `frontend/src/__tests__/TrainingSession.test.jsx` | Add tests for Answer toggle (profile 99 only) |
| `verification/phase9_show_answer.md` | New verification doc |
| `e2e/tests/phase9.6_show_answer.spec.ts` | New Playwright E2E test |

---

## Implementation

### `backend/tests/test_training_api.py`

Add at end of file:

```python
# ---------------------------------------------------------------------------
# PUT /api/puzzles/{puzzle_id}/solution
# ---------------------------------------------------------------------------

def test_update_puzzle_solution_success(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    seed_verified_puzzles(db)
    puzzle = db.query(Puzzle).first()
    puzzle_id = puzzle.id
    db.close()

    resp = test_client.put(f"/api/puzzles/{puzzle_id}/solution", json={
        "solution_san": "Nxf6+",
        "solution_uci": "g8f6",
        "solution_line": "1. Nxf6+ Kh7 2. Ng8+",
        "solution_uci_line": ["g8f6", "h8h7", "f6g8"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == puzzle_id
    assert data["solution_san"] == "Nxf6+"
    assert data["solution_uci"] == "g8f6"
    assert data["solution_line"] == "1. Nxf6+ Kh7 2. Ng8+"
    assert data["solution_uci_line"] == ["g8f6", "h8h7", "f6g8"]


def test_update_puzzle_solution_partial_fields(test_client, test_engine):
    """solution_line and solution_uci_line are optional (nullable)."""
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    seed_verified_puzzles(db)
    puzzle = db.query(Puzzle).first()
    puzzle_id = puzzle.id
    db.close()

    resp = test_client.put(f"/api/puzzles/{puzzle_id}/solution", json={
        "solution_san": "Bxh7+",
        "solution_uci": "c4h7",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["solution_san"] == "Bxh7+"
    assert data["solution_line"] is None
    assert data["solution_uci_line"] is None


def test_update_puzzle_solution_not_found(test_client):
    resp = test_client.put("/api/puzzles/99999/solution", json={
        "solution_san": "e5",
        "solution_uci": "e7e5",
    })
    assert resp.status_code == 404


def test_update_puzzle_solution_persists(test_client, test_engine):
    """Verify the update is persisted by re-fetching the puzzle."""
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    seed_verified_puzzles(db)
    puzzle = db.query(Puzzle).first()
    puzzle_id = puzzle.id
    db.close()

    test_client.put(f"/api/puzzles/{puzzle_id}/solution", json={
        "solution_san": "Qxg7#",
        "solution_uci": "d1g7",
        "solution_line": "1. Qxg7#",
        "solution_uci_line": ["d1g7"],
    })

    resp = test_client.get(f"/api/puzzles/{puzzle_id}")
    assert resp.status_code == 200
    puzzle_data = resp.json()["puzzle"]
    assert puzzle_data["solution_san"] == "Qxg7#"
    assert puzzle_data["solution_uci_line"] == ["d1g7"]
```

### `frontend/src/__tests__/TrainingSession.test.jsx`

Add a new `describe` block after the existing tests:

```jsx
describe('TrainingSession - Answer Toggle (profile 99)', () => {
  const MOCK_STATE_99 = {
    ...MOCK_STATE_WITH_BATCH,
    puzzle_ids: [1, 2, 3],
    is_randomized_circle: false,
  };

  const MOCK_PUZZLE_WITH_SOLUTION = {
    ...MOCK_PUZZLE,
    solution_line: '1. Nxf6+ Kh7 2. Ng8+',
    solution_uci_line: ['g8f6', 'h8h7', 'f6g8'],
  };

  beforeEach(() => {
    api.getTrainingState.mockResolvedValue(MOCK_STATE_99);
    api.getNextPuzzle.mockResolvedValue({ puzzle: MOCK_PUZZLE_WITH_SOLUTION });
    api.startSession.mockResolvedValue({ id: 1 });
  });

  it('renders Answer button for profile 99', async () => {
    await act(async () => renderSession('99'));
    await waitFor(() => {
      expect(screen.getByText('Answer')).toBeDefined();
    });
  });

  it('does not render Answer button for non-99 profiles', async () => {
    api.getTrainingState.mockResolvedValue(MOCK_STATE_WITH_BATCH);
    api.getNextPuzzle.mockResolvedValue({ puzzle: MOCK_PUZZLE });
    await act(async () => renderSession('1'));
    await waitFor(() => {
      expect(screen.getByTestId('chessboard-container')).toBeDefined();
    });
    expect(screen.queryByText('Answer')).toBeNull();
  });

  it('renders Prev/Next navigation for profile 99', async () => {
    await act(async () => renderSession('99'));
    await waitFor(() => {
      expect(screen.getByText(/Prev/)).toBeDefined();
      expect(screen.getByText(/Next/)).toBeDefined();
    });
  });
});
```

### `e2e/tests/phase9.6_show_answer.spec.ts`

```typescript
/**
 * Phase 9.6 Playwright E2E tests: Show Answer Toggle
 *
 * Prerequisites:
 *   - Backend:  cd backend && uvicorn main:app --port 8000
 *   - Frontend: cd frontend && npm run dev
 *   - DB state: test_setup.py create (profile 99 with active batch)
 *
 * Run: cd e2e && npx playwright test tests/phase9.6_show_answer.spec.ts
 */

import { test, expect, request as playwrightRequest } from '@playwright/test';

const BASE = 'http://localhost:5173';
const API  = 'http://localhost:8000';
const TEST_PROFILE_ID = 99;

async function resetTestSession() {
  const ctx = await playwrightRequest.newContext();
  const stateRes = await ctx.get(`${API}/api/training/state/${TEST_PROFILE_ID}`);
  const state = await stateRes.json();
  if (state.session?.id) {
    await ctx.post(`${API}/api/training/end-session/${state.session.id}`);
  }
  await ctx.post(`${API}/api/training/start-session/${TEST_PROFILE_ID}`);
  await ctx.dispose();
}

test.describe('Phase 9.6: Show Answer Toggle', () => {
  test.beforeEach(async () => {
    await resetTestSession();
  });

  test('Answer button is visible for profile 99', async ({ page }) => {
    await page.goto(`${BASE}/train/${TEST_PROFILE_ID}`);
    const answerBtn = page.getByRole('button', { name: 'Answer' });
    await expect(answerBtn).toBeVisible({ timeout: 10000 });
  });

  test('clicking Answer shows solution panel', async ({ page }) => {
    await page.goto(`${BASE}/train/${TEST_PROFILE_ID}`);
    const answerBtn = page.getByRole('button', { name: 'Answer' });
    await expect(answerBtn).toBeVisible({ timeout: 10000 });

    await answerBtn.click();

    // Solution panel should appear with "Solution" heading
    await expect(page.getByText('Solution')).toBeVisible();

    // Button should now say "Hide"
    await expect(page.getByRole('button', { name: 'Hide' })).toBeVisible();

    await page.screenshot({ path: 'test-results/phase9.6-answer-visible.png' });
  });

  test('clicking Hide hides solution panel', async ({ page }) => {
    await page.goto(`${BASE}/train/${TEST_PROFILE_ID}`);
    const answerBtn = page.getByRole('button', { name: 'Answer' });
    await expect(answerBtn).toBeVisible({ timeout: 10000 });

    await answerBtn.click();
    await expect(page.getByText('Solution')).toBeVisible();

    const hideBtn = page.getByRole('button', { name: 'Hide' });
    await hideBtn.click();

    // Solution panel should be hidden
    await expect(page.getByRole('button', { name: 'Answer' })).toBeVisible();
  });

  test('navigating Next resets answer panel', async ({ page }) => {
    await page.goto(`${BASE}/train/${TEST_PROFILE_ID}`);
    const answerBtn = page.getByRole('button', { name: 'Answer' });
    await expect(answerBtn).toBeVisible({ timeout: 10000 });

    // Show answer on first puzzle
    await answerBtn.click();
    await expect(page.getByText('Solution')).toBeVisible();

    // Navigate to next puzzle
    const nextBtn = page.getByRole('button', { name: /Next/ });
    await nextBtn.click();

    // Answer panel should be hidden on new puzzle
    await expect(page.getByRole('button', { name: 'Answer' })).toBeVisible();
  });

  test('Answer button not visible for regular profiles', async ({ page }) => {
    await page.goto(`${BASE}/train/1`);
    // Wait for board to load
    await page.waitForTimeout(3000);
    // Answer button should not exist
    await expect(page.getByRole('button', { name: 'Answer' })).not.toBeVisible();
  });
});
```

---

## Execution Workflow

### RED -- write tests first

```bash
cd backend && pytest tests/test_training_api.py -v -k "update_puzzle_solution"
cd frontend && npx vitest run src/__tests__/TrainingSession.test.jsx
```

Since implementation exists, tests should be **GREEN** immediately.

### GREEN -- verify all pass

```bash
cd backend && pytest -v
cd frontend && npm test
```

### SHOWBOAT -- `verification/phase9_show_answer.md`

```
showboat init verification/phase9_show_answer.md "Phase 9.6: Show Answer & Solution Editing Verification"
showboat note verification/phase9_show_answer.md "Verify PUT /api/puzzles/{id}/solution endpoint and Answer toggle in UI"
showboat exec verification/phase9_show_answer.md bash "cd backend && pytest tests/test_training_api.py -v -k 'update_puzzle_solution'"
showboat exec verification/phase9_show_answer.md bash "cd frontend && npx vitest run src/__tests__/TrainingSession.test.jsx 2>&1 | tail -10"
showboat exec verification/phase9_show_answer.md bash "cd backend && pytest -v"
showboat note verification/phase9_show_answer.md "Manual: profile 99 -> Answer button toggles solution panel; Next resets it"
showboat exec verification/phase9_show_answer.md bash "curl -s http://localhost:8000/api/puzzles/1 | python3 -m json.tool | head -15"
showboat verify verification/phase9_show_answer.md
```

### PLAYWRIGHT -- `e2e/tests/phase9.6_show_answer.spec.ts`

Both servers must be running (`./test.sh`).

- Navigate to profile 99 training session with active batch
- Assert "Answer" button visible
- Click Answer -> assert solution panel appears with "Solution" text
- Assert button label changes to "Hide"
- Click Hide -> assert panel disappears
- Click Next -> assert answer panel is hidden on new puzzle
- Navigate to profile 1 -> assert no Answer button

All existing Playwright tests must remain green.
