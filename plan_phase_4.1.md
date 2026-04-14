# Phase 4.1: Dashboard UX Fixes Test Coverage

## Context

Two post-phase commits added Dashboard UX improvements without tests:
- **15f61f1**: "Start Chapter 1" button shown when `has_active_batch` is false (`Dashboard.jsx:152-159`)
- **90e87cb**: `current_circle` field added to API response (has Playwright E2E in `phase4_circle_completion.spec.ts` but no backend unit test for the field)

**Key decisions:**
- Frontend test for Start Chapter 1 button goes in `Dashboard.test.jsx`
- Backend test for `current_circle` field goes in `test_training.py` (existing `get_training_state` section)
- No new Playwright E2E needed -- circle completion already covered by `phase4_circle_completion.spec.ts`

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/__tests__/Dashboard.test.jsx` | Add tests for Start Chapter 1 button |
| `backend/tests/test_training.py` | Add test for current_circle in training state |

---

## Implementation

### `frontend/src/__tests__/Dashboard.test.jsx`

Add inside the existing `describe('Dashboard')` block:

```jsx
  it('renders Start Chapter 1 button when no active batch', async () => {
    api.getDashboard.mockResolvedValue(MOCK_DASHBOARD_NO_BATCH);
    await act(async () => renderDashboard());
    await waitFor(() => expect(screen.getByTestId('no-batch')).toBeDefined());

    const startBtn = screen.getByText('Start Chapter 1');
    expect(startBtn).toBeDefined();
    expect(startBtn.tagName).toBe('BUTTON');
  });

  it('does not render Start Chapter 1 button when batch exists', async () => {
    await act(async () => renderDashboard());
    await waitFor(() => expect(screen.getByTestId('dashboard')).toBeDefined());
    expect(screen.queryByText('Start Chapter 1')).toBeNull();
  });
```

### `backend/tests/test_training.py`

Add after the existing `test_get_training_state_with_active_batch` test:

```python
def test_training_state_includes_current_circle(seeded_db):
    db = seeded_db
    make_puzzles(db, count=2)
    training.create_batch(profile_id=1, chapter_id=1, db=db)

    state = training.get_training_state(profile_id=1, db=db)
    assert "current_circle" in state
    assert state["current_circle"] == 1


def test_training_state_no_batch_has_no_current_circle(seeded_db):
    db = seeded_db
    state = training.get_training_state(profile_id=1, db=db)
    assert "current_circle" not in state
```

---

## Execution Workflow

### RED -- write tests first

```bash
cd frontend && npx vitest run src/__tests__/Dashboard.test.jsx
cd backend && pytest tests/test_training.py -v -k "current_circle"
```

Since the implementation already exists, tests should be **GREEN** immediately.

### GREEN -- verify all pass

```bash
cd backend && pytest -v
cd frontend && npm test
```

All tests should be **GREEN**.

### SHOWBOAT -- `verification/phase4_dashboard_fixes.md`

```
showboat init verification/phase4_dashboard_fixes.md "Phase 4.1: Dashboard UX Fixes Verification"
showboat note verification/phase4_dashboard_fixes.md "Verify Start Chapter 1 button and current_circle in API response"
showboat exec verification/phase4_dashboard_fixes.md bash "cd backend && pytest tests/test_training.py -v -k 'current_circle'"
showboat exec verification/phase4_dashboard_fixes.md bash "cd frontend && npx vitest run src/__tests__/Dashboard.test.jsx 2>&1 | tail -10"
showboat exec verification/phase4_dashboard_fixes.md bash "cd backend && pytest -v"
showboat note verification/phase4_dashboard_fixes.md "Manual: navigate to dashboard with no active batch, verify Start Chapter 1 button visible"
showboat verify verification/phase4_dashboard_fixes.md
```

### PLAYWRIGHT

No new Playwright E2E needed -- circle completion navigation already covered by `phase4_circle_completion.spec.ts`. The Start Chapter 1 button is a simple UI element adequately covered by the unit test.
