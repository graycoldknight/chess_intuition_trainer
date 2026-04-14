# Phase 3.1: Training State Additions Test Coverage

## Context

Two commits added fields to the training state without tests:
- **4f54ba9**: Added `total_xp` and `puzzle_ids` to `get_training_state()` return dict
- **f92202a**: Added `median_time_ms` calculation in circle stats, median display in ResultsScreen

The median calculation at `training.py:273-278` has real edge-case risk (even/odd count, zero correct attempts, single value). These fields are consumed by the frontend Dashboard, ResultsScreen, and TrainingSession components.

**Key decisions:**
- Backend unit tests go in `test_training.py` (alongside existing `get_training_state` tests)
- API-level test for new fields goes in `test_training_api.py`
- Frontend test for median display goes in `ResultsScreen.test.jsx`
- No Playwright E2E needed -- median is a display-only stat visible in existing E2E flows

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/tests/test_training.py` | Add tests for median calc edge cases, total_xp, puzzle_ids |
| `backend/tests/test_training_api.py` | Add test asserting new fields in API response |
| `frontend/src/__tests__/ResultsScreen.test.jsx` | Add test for median_time_ms display |

---

## Implementation

### `backend/tests/test_training.py`

Add after the existing `test_get_training_state_with_active_batch` test (~line 430):

```python
# ---------------------------------------------------------------------------
# get_training_state: total_xp, puzzle_ids, median_time_ms
# ---------------------------------------------------------------------------

def test_training_state_includes_total_xp(seeded_db):
    db = seeded_db
    profile = db.query(Profile).get(1)
    profile.total_xp = 250
    db.commit()

    make_puzzles(db, count=2)
    training.create_batch(profile_id=1, chapter_id=1, db=db)

    state = training.get_training_state(profile_id=1, db=db)
    assert state["total_xp"] == 250


def test_training_state_no_batch_includes_total_xp(seeded_db):
    db = seeded_db
    state = training.get_training_state(profile_id=1, db=db)
    assert "total_xp" in state
    assert state["total_xp"] == 0


def test_training_state_includes_puzzle_ids(seeded_db):
    db = seeded_db
    make_puzzles(db, count=3)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    state = training.get_training_state(profile_id=1, db=db)
    assert "puzzle_ids" in state
    assert state["puzzle_ids"] == batch.puzzle_ids
    assert len(state["puzzle_ids"]) == 3


def test_median_time_single_correct(seeded_db):
    """Median of a single value is that value."""
    db = seeded_db
    make_puzzles(db, count=1)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    record_all_puzzles_in_circle(db, batch, profile_id=1, circle=1, time_ms=5000)
    db.refresh(batch)

    state = training.get_training_state(profile_id=1, db=db)
    assert state["circle_stats"][1]["median_time_ms"] == 5000


def test_median_time_odd_count(seeded_db):
    """Median of [3000, 5000, 7000] = 5000 (middle value)."""
    db = seeded_db
    make_puzzles(db, count=3)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    times = [3000, 7000, 5000]
    for i, pid in enumerate(batch.puzzle_ids):
        training.record_attempt(
            profile_id=1, puzzle_id=pid, batch_id=batch.id,
            circle=1, success=True, time_taken_ms=times[i],
            user_move="e7e5", db=db,
        )

    state = training.get_training_state(profile_id=1, db=db)
    assert state["circle_stats"][1]["median_time_ms"] == 5000


def test_median_time_even_count(seeded_db):
    """Median of [3000, 5000, 7000, 9000] = avg(5000, 7000) = 6000."""
    db = seeded_db
    make_puzzles(db, count=4)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    times = [9000, 3000, 7000, 5000]
    for i, pid in enumerate(batch.puzzle_ids):
        training.record_attempt(
            profile_id=1, puzzle_id=pid, batch_id=batch.id,
            circle=1, success=True, time_taken_ms=times[i],
            user_move="e7e5", db=db,
        )

    state = training.get_training_state(profile_id=1, db=db)
    assert state["circle_stats"][1]["median_time_ms"] == 6000


def test_median_time_no_correct_attempts(seeded_db):
    """When all attempts are wrong, median should be None."""
    db = seeded_db
    make_puzzles(db, count=2)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    record_all_puzzles_in_circle(db, batch, profile_id=1, circle=1, time_ms=5000, success=False)
    db.refresh(batch)

    state = training.get_training_state(profile_id=1, db=db)
    assert state["circle_stats"][1]["median_time_ms"] is None
    assert state["circle_stats"][1]["avg_time_ms"] is None
```

### `backend/tests/test_training_api.py`

Add after existing `test_training_state_with_batch` test:

```python
def test_training_state_api_includes_total_xp_and_puzzle_ids(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    seed_verified_puzzles(db)
    db.close()

    create_batch_via_api(test_client)
    resp = test_client.get("/api/training/state/1")
    data = resp.json()

    assert "total_xp" in data
    assert isinstance(data["total_xp"], int)
    assert "puzzle_ids" in data
    assert isinstance(data["puzzle_ids"], list)
    assert len(data["puzzle_ids"]) == 3
```

### `frontend/src/__tests__/ResultsScreen.test.jsx`

Add inside the existing `describe('ResultsScreen')` block:

```jsx
  it('renders median time when present in circle stats', async () => {
    api.getDashboard.mockResolvedValue(
      makeDashboard({
        currentCircle: 2,
        circleStats: {
          '1': { total: 50, correct: 45, avg_time_ms: 12000, median_time_ms: 10500 },
        },
      })
    );
    await act(async () => renderResults());
    await waitFor(() => {
      expect(screen.getByText(/median/i)).toBeDefined();
    });
  });
```

---

## Execution Workflow

### RED -- write tests first

```bash
cd backend && pytest tests/test_training.py -v -k "total_xp or puzzle_ids or median"
cd backend && pytest tests/test_training_api.py -v -k "total_xp_and_puzzle_ids"
cd frontend && npx vitest run src/__tests__/ResultsScreen.test.jsx
```

Since the implementation already exists, tests should be **GREEN** immediately. Any failure reveals a bug.

### GREEN -- verify all pass

```bash
cd backend && pytest -v
cd frontend && npm test
```

All tests should be **GREEN**.

### SHOWBOAT -- `verification/phase3_training_additions.md`

```
showboat init verification/phase3_training_additions.md "Phase 3.1: Training State Additions Verification"
showboat note verification/phase3_training_additions.md "Verify median_time_ms, total_xp, puzzle_ids in training state"
showboat exec verification/phase3_training_additions.md bash "cd backend && pytest tests/test_training.py -v -k 'total_xp or puzzle_ids or median'"
showboat exec verification/phase3_training_additions.md bash "cd backend && pytest tests/test_training_api.py -v -k 'total_xp_and_puzzle_ids'"
showboat exec verification/phase3_training_additions.md bash "cd frontend && npx vitest run src/__tests__/ResultsScreen.test.jsx 2>&1 | tail -5"
showboat exec verification/phase3_training_additions.md bash "cd backend && pytest -v"
showboat note verification/phase3_training_additions.md "Verify training state API returns all new fields"
showboat exec verification/phase3_training_additions.md bash "curl -s http://localhost:8000/api/training/state/1 | python3 -c \"import sys,json; d=json.load(sys.stdin); print({k: d.get(k) for k in ['total_xp','puzzle_ids']})\""
showboat verify verification/phase3_training_additions.md
```

### PLAYWRIGHT

No new Playwright E2E needed -- median is a display-only stat within the existing ResultsScreen, already exercised by `phase4_dashboard.spec.ts` and `manual_validation.spec.ts` flows.
