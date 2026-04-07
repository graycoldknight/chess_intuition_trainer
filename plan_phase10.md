# Phase 10: Randomized Challenge Circles (6 & 7)

## Context

Circles 1–5 always serve puzzles in the same `puzzle_number` order. This builds positional memory, but risks the pattern being "index-memorized" rather than truly internalized. Circles 6 and 7 are a **randomized internalization test**: if a student can solve puzzles quickly in a scrambled order, the pattern is genuinely internalized. Graduation is deferred until after circle 7 so that both test circles are mandatory.

**Key decisions:**
- Circles 1–5: sequential, unchanged
- Circle 6: randomly shuffled puzzle order (independent shuffle per batch)
- Circle 7: independently re-shuffled (different order from circle 6)
- Circles 8+ (if graduation still not met): also randomized
- Graduation check moved from `>= 5` to `>= 7`
- Frontend shows **"⚡ Challenge Mode"** badge during circles 6+

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/models.py` | Add `circle_puzzle_orders` JSON column to `Batch` |
| `backend/training.py` | Randomize puzzle order for circles 6+; defer graduation to circle 7 |
| `backend/main.py` | Add `is_randomized_circle` to training state response |
| `frontend/src/components/TrainingSession.jsx` | Render Challenge Mode badge for circles 6+ |

---

## Data Model Change

### `batches` table — add column

```python
circle_puzzle_orders = Column(JSON, nullable=True)
# Maps str(circle_number) → [puzzle_id, ...] (shuffled order)
# Only populated for circles >= 6; null for older rows (handled gracefully)
```

**Migration for existing DB:**
```sql
ALTER TABLE batches ADD COLUMN circle_puzzle_orders JSON;
```
Or delete `backend/chess_intuition.db` and let SQLAlchemy recreate it on startup.

---

## Implementation

### `backend/training.py`

**Add constant at top of file:**
```python
RANDOMIZED_FROM_CIRCLE = 6  # circles 6+ use independently shuffled puzzle order
```

**`get_next_puzzle` — change puzzle ordering:**
```python
# was: iterate batch.puzzle_ids in order
# new: for circles >= RANDOMIZED_FROM_CIRCLE, use the pre-generated shuffled order
orders = batch.circle_puzzle_orders or {}
puzzle_order = orders.get(str(batch.current_circle), batch.puzzle_ids)
# rest of attempted-set logic unchanged — iterate puzzle_order instead of batch.puzzle_ids
```

**`_maybe_advance_circle` — two changes:**

1. Defer graduation threshold from `>= 5` → `>= 7`:
```python
# was: if batch.current_circle >= 5:
# new: if batch.current_circle >= 7:
```

2. Generate and store a fresh shuffle when advancing into circle 6+:
```python
import random  # already in stdlib

batch.current_circle += 1
if batch.current_circle >= RANDOMIZED_FROM_CIRCLE:
    shuffled = list(batch.puzzle_ids)  # copy — never mutate puzzle_ids
    random.shuffle(shuffled)
    orders = dict(batch.circle_puzzle_orders or {})  # copy to trigger SQLAlchemy JSON mutation detection
    orders[str(batch.current_circle)] = shuffled
    batch.circle_puzzle_orders = orders
```

### `backend/main.py`

In the `get_training_state` response dict (around line 226), add:
```python
"is_randomized_circle": batch.current_circle >= RANDOMIZED_FROM_CIRCLE,
```

Import `RANDOMIZED_FROM_CIRCLE` from `training.py`.

### `frontend/src/components/TrainingSession.jsx`

Read `trainingState.is_randomized_circle` and render a badge in the existing puzzle header:
```jsx
{trainingState?.is_randomized_circle && (
  <span className="challenge-badge">⚡ Challenge Mode</span>
)}
```

Style inline or via existing CSS: amber/gold, small, positioned next to the circle indicator.

---

## Execution Workflow

### RED — write failing tests first

Add to `backend/tests/test_training.py`:

```python
def test_graduation_not_triggered_at_circle_5():
    # Simulate completing circle 5 with avg time < 15s
    # Assert batch.status != "ready_to_graduate"
    # Assert batch.current_circle == 6

def test_graduation_not_triggered_at_circle_6():
    # Simulate completing circle 6 with avg time < 15s
    # Assert batch.status != "ready_to_graduate"
    # Assert batch.current_circle == 7

def test_graduation_triggered_at_circle_7():
    # Simulate completing circle 7 with avg time < 15s
    # Assert batch.status == "ready_to_graduate"

def test_circle_6_has_shuffled_order():
    # Complete circles 1-5
    # Assert batch.current_circle == 6
    # Assert batch.circle_puzzle_orders["6"] is not None
    # Assert set(batch.circle_puzzle_orders["6"]) == set(batch.puzzle_ids)  (same elements)
    # Assert len(batch.circle_puzzle_orders["6"]) == batch.total_puzzles

def test_circle_6_and_7_have_different_shuffles():
    # Complete circles 1-6
    # Assert batch.circle_puzzle_orders["6"] != batch.circle_puzzle_orders["7"]
    # (run many times or mock random.shuffle to guarantee different outputs)

def test_get_next_puzzle_uses_shuffled_order_in_circle_6():
    # Reach circle 6
    # Call get_next_puzzle repeatedly for all puzzles
    # Collect returned puzzle IDs in order
    # Assert that order != batch.puzzle_ids (sequential order)
    # Assert that order == batch.circle_puzzle_orders["6"]

def test_circle_puzzle_orders_null_on_circles_1_to_5():
    # Create batch, complete circle 1
    # Assert batch.circle_puzzle_orders is None or does not contain key "1"
```

Run `cd backend && pytest tests/test_training.py -v` — new tests should be **RED**.

### GREEN — implement

Apply changes to `models.py`, `training.py`, `main.py`, `TrainingSession.jsx` as described above.

Run `cd backend && pytest` — all tests should be **GREEN**.

### SHOWBOAT — `verification/phase10_challenge_circles.md`

```
showboat init verification/phase10_challenge_circles.md "Phase 10: Randomized Challenge Circles Verification"
showboat note verification/phase10_challenge_circles.md "Verify circles 6 and 7 use randomized puzzle order and graduation is deferred to circle 7."
showboat exec verification/phase10_challenge_circles.md bash "cd backend && pytest tests/test_training.py -v -k 'circle_6 or circle_7 or randomized or challenge'"
showboat exec verification/phase10_challenge_circles.md bash "cd backend && pytest -v"
showboat note verification/phase10_challenge_circles.md "Verify training state includes is_randomized_circle flag."
showboat exec verification/phase10_challenge_circles.md bash "curl -s http://localhost:8000/api/training/state/1 | python -m json.tool | grep -A1 'is_randomized'"
showboat note verification/phase10_challenge_circles.md "Fast-forward a batch to circle 6 and verify shuffle is stored."
showboat exec verification/phase10_challenge_circles.md bash "cd backend && python -c \"
from database import SessionLocal
from models import Batch
db = SessionLocal()
b = db.query(Batch).filter(Batch.current_circle >= 6).first()
if b:
    orders = b.circle_puzzle_orders or {}
    print(f'circle_6 order: {orders.get(\\\"6\\\", \\\"NOT SET\\\")}')
    print(f'original order: {b.puzzle_ids}')
    print(f'same elements: {sorted(orders.get(\\\"6\\\",[]))==sorted(b.puzzle_ids)}')
    print(f'different order: {orders.get(\\\"6\\\") != b.puzzle_ids}')
else:
    print('No batch at circle 6 yet')
\""
showboat verify verification/phase10_challenge_circles.md
```

### PLAYWRIGHT — `e2e/tests/phase10_challenge_circles.spec.ts`

Both servers must be running (`./test.sh`).

- Navigate to profile select → select test profile (profile ID 99)
- Create a batch for Chapter 1
- Fast-forward through circles 1–5 using existing test setup helpers (`backend/test_setup.py`)
- Assert no graduation prompt appears after circle 5
- Assert no graduation prompt appears after circle 6
- Verify **"⚡ Challenge Mode"** badge is visible in the header during circle 6
- Verify **"⚡ Challenge Mode"** badge is visible during circle 7
- Assert graduation prompt appears after completing circle 7 with fast solves
- Screenshot circle 6 header to confirm Challenge Mode badge is rendered
- Verify that the circle 6 puzzle order (captured via API state) differs from circle 1 order

All existing Playwright tests must remain green.
