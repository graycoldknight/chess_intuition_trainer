# Phase 9.5: Test Mode Prev/Next Navigation

## Context

Profile 99 is the reserved test/validation profile. Currently, navigating between puzzles requires solving each one (or waiting for auto-advance after a wrong answer). This makes it tedious to scan all puzzles in a batch to validate FEN positions. Adding Prev/Next buttons for profile 99 lets you jump directly to any puzzle by index without solving.

**Key decisions:**
- Frontend-only navigation state (`browseIndex`) — no new DB columns or session tracking needed
- Expose `puzzle_ids` list in the existing `get_training_state` response (profile-agnostic, minimal change) so the frontend knows the full ordered list
- New `GET /api/puzzles/{puzzle_id}` endpoint returns the same response shape as `next-puzzle`, allowing the frontend to fetch any puzzle directly
- Prev/Next navigation does NOT record attempts and does NOT start the stopwatch — purely for visual validation
- Normal training flow (`loadNextPuzzle`, attempt recording, auto-advance) is completely unchanged

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/training.py` | Add `puzzle_ids` field to `get_training_state()` return dict |
| `backend/main.py` | Add `GET /api/puzzles/{puzzle_id}` endpoint |
| `frontend/src/services/api.js` | Add `getPuzzleById(puzzleId)` |
| `frontend/src/components/TrainingSession.jsx` | Add `puzzleIds`/`browseIndex` state, `loadPuzzleById()`, Prev/Next buttons + position indicator |

---

## Implementation

### `backend/training.py`

In `get_training_state()`, the `has_active_batch: True` return dict (around line 273), add:
```python
"puzzle_ids": batch.puzzle_ids,
```

### `backend/main.py`

Add after the existing `PUT /api/puzzles/{puzzle_id}/fen` endpoint (around line 463):
```python
@app.get("/api/puzzles/{puzzle_id}")
def get_puzzle_by_id(puzzle_id: int, db: Session = Depends(get_db)):
    puzzle = db.query(Puzzle).get(puzzle_id)
    if not puzzle:
        raise HTTPException(status_code=404, detail="Puzzle not found")
    return {
        "puzzle": {
            "id": puzzle.id,
            "chapter_id": puzzle.chapter_id,
            "puzzle_number": puzzle.puzzle_number,
            "fen": puzzle.fen,
            "turn": puzzle.turn,
            "solution_san": puzzle.solution_san,
            "solution_uci": puzzle.solution_uci,
            "solution_line": puzzle.solution_line,
            "solution_uci_line": puzzle.solution_uci_line or [puzzle.solution_uci],
        }
    }
```

### `frontend/src/services/api.js`

Add:
```js
export const getPuzzleById = (puzzleId) =>
  request(`/api/puzzles/${puzzleId}`);
```

### `frontend/src/components/TrainingSession.jsx`

**New state (near existing edit-mode state, ~line 108):**
```jsx
// Browse navigation (test profile 99 only)
const [puzzleIds, setPuzzleIds] = useState([]);      // ordered list from batch
const [browseIndex, setBrowseIndex] = useState(0);   // current position in puzzleIds
```

**In `useEffect` initialization, after `setBatchId(trainingState.batch_id)` (~line 123):**
```jsx
if (pid === 99 && trainingState.puzzle_ids) {
  setPuzzleIds(trainingState.puzzle_ids);
}
```

Also set `browseIndex` after the first puzzle loads — in `loadNextPuzzle`, after `setPuzzle(p)`, add:
```jsx
if (pid === 99) {
  setBrowseIndex(prev => {
    // find this puzzle's index in puzzleIds (use ref to avoid stale closure)
    const idx = puzzleIdsRef.current.indexOf(p.id);
    return idx >= 0 ? idx : prev;
  });
}
```
(Use a `puzzleIdsRef` ref that mirrors the `puzzleIds` state to avoid stale closure in the callback.)

**New `loadPuzzleById` function:**
```jsx
const loadPuzzleById = useCallback(async (puzzleId, index) => {
  advancing.current = false;
  setSolveStatus(null);
  setArrows([]);
  setPuzzleLoading(true);
  const resp = await api.getPuzzleById(puzzleId);
  setPuzzleLoading(false);
  if (!resp.puzzle) return;
  const p = resp.puzzle;
  setPuzzle(p);
  setGame(new Chess(p.fen));
  setSolutionMoves(p.solution_uci_line ?? [p.solution_uci]);
  setMoveIndex(0);
  setBrowseIndex(index);
  // No stopwatch start — browse mode only
}, []);
```

**Prev/Next handlers:**
```jsx
const handlePrev = useCallback(() => {
  const idx = browseIndex - 1;
  if (idx >= 0) loadPuzzleById(puzzleIds[idx], idx);
}, [browseIndex, puzzleIds, loadPuzzleById]);

const handleNext = useCallback(() => {
  const idx = browseIndex + 1;
  if (idx < puzzleIds.length) loadPuzzleById(puzzleIds[idx], idx);
}, [browseIndex, puzzleIds, loadPuzzleById]);
```

**In the puzzle info bar render (~line 372), replace the existing Edit button block:**
```jsx
{pid === 99 && !editMode && (
  <>
    <button
      onClick={handlePrev}
      disabled={browseIndex <= 0}
      style={editBtnStyle}
    >← Prev</button>
    <span style={{ color: '#666', fontSize: '0.78rem' }}>
      {browseIndex + 1} / {puzzleIds.length}
    </span>
    <button
      onClick={handleNext}
      disabled={browseIndex >= puzzleIds.length - 1}
      style={editBtnStyle}
    >Next →</button>
    <button onClick={handleEnterEdit} style={editBtnStyle}>Edit</button>
  </>
)}
```

---

## Execution Workflow

### RED — write failing tests first

Add to `backend/tests/test_training.py`:

```python
def test_get_training_state_includes_puzzle_ids(db_session, test_profile, test_batch):
    # Arrange: active batch with known puzzle_ids
    # Act
    state = training.get_training_state(profile_id=test_profile.id, db=db_session)
    # Assert
    assert state["has_active_batch"] is True
    assert "puzzle_ids" in state
    assert isinstance(state["puzzle_ids"], list)
    assert state["puzzle_ids"] == test_batch.puzzle_ids
```

Run `cd backend && pytest tests/test_training.py -v` — new test should be **RED**.

### GREEN — implement

Apply changes as described above.

Run `cd backend && pytest` — all tests should be **GREEN**.

### SHOWBOAT — `verification/phase9.5_browse_nav.md`

```
showboat init verification/phase9.5_browse_nav.md "Phase 9.5: Test Mode Browse Navigation"
showboat note verification/phase9.5_browse_nav.md "Verify puzzle_ids exposed in training state"
showboat exec verification/phase9.5_browse_nav.md bash "cd backend && pytest tests/test_training.py -v -k 'puzzle_ids'"
showboat exec verification/phase9.5_browse_nav.md bash "cd backend && pytest -v"
showboat note verification/phase9.5_browse_nav.md "Verify new GET /api/puzzles/{id} endpoint"
showboat exec verification/phase9.5_browse_nav.md bash "curl -s http://localhost:8000/api/puzzles/1 | python -m json.tool"
showboat verify verification/phase9.5_browse_nav.md
```

### PLAYWRIGHT — `e2e/tests/phase9.5_browse_nav.spec.ts`

Both servers must be running (`./test.sh`).

- Navigate to profile 99's training session with an active batch
- Assert Prev/Next buttons are visible in the puzzle info bar
- Assert "1 / N" position indicator is visible
- Click Next → puzzle number increments, FEN on board changes, no attempt recorded
- Click Prev → returns to previous puzzle
- At index 0, Prev button is disabled; at last index, Next button is disabled
- Assert Edit button still visible alongside Prev/Next
- Assert normal profiles (e.g. profile 1) do NOT see Prev/Next buttons

All existing Playwright tests must remain green.
