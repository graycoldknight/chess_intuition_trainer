# Phase 9.6: Show Answer in Test Mode

## Context

Profile 99 is used to validate extracted puzzles against the source PDF. Currently there is no way to see the full solution line without solving (or deliberately getting it wrong). Adding an "Answer" toggle button lets you instantly reveal `solution_line` (the full SAN main line, e.g. `1. Nxf6 Kh7 2. Ng8+`) alongside the first-move UCI, so you can cross-check each puzzle against the book.

**Key decisions:**
- Pure frontend change — the API already returns `solution_line`, `solution_san`, and `solution_uci_line` in every puzzle response; no backend work needed
- Toggle button ("Answer" / "Hide"), not a permanent reveal — keeps the board uncluttered while navigating
- Reset `showAnswer` to `false` on every puzzle change (Prev, Next, or `loadNextPuzzle`) so each puzzle starts hidden
- Show both the human-readable `solution_line` (SAN prose) and the raw UCI line — the SAN is what you compare to the PDF; the UCI is useful for spotting extraction errors

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/TrainingSession.jsx` | Add `showAnswer` state; reset on navigation; "Answer" toggle button; answer panel below board |

---

## Implementation

### `frontend/src/components/TrainingSession.jsx`

**New state** (near the browse-navigation state block, ~line 108):
```jsx
const [showAnswer, setShowAnswer] = useState(false);
```

**Reset on navigation** — add `setShowAnswer(false)` in two places:

In `loadNextPuzzle`, after `setMoveIndex(0)`:
```jsx
setShowAnswer(false);
```

In `loadPuzzleById`, after `setMoveIndex(0)`:
```jsx
setShowAnswer(false);
```

**"Answer" toggle button** — in the puzzle info bar (pid === 99, !editMode block, ~line 416), add after the Edit button:
```jsx
<button
  onClick={() => setShowAnswer(v => !v)}
  style={{ ...editBtnStyle, background: showAnswer ? '#3b1a00' : undefined }}
>
  {showAnswer ? 'Hide' : 'Answer'}
</button>
```

**Answer panel** — in normal play mode (below the feedback correct/wrong divs, ~line 530), add:
```jsx
{pid === 99 && showAnswer && (
  <div style={{
    marginTop: 14,
    background: '#111827',
    border: '1px solid #374151',
    borderRadius: 8,
    padding: '10px 14px',
  }}>
    <div style={{ color: '#9ca3af', fontSize: '0.72rem', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
      Solution
    </div>
    <div style={{ color: '#f9fafb', fontSize: '0.95rem', fontWeight: 600, marginBottom: 6 }}>
      {puzzle.solution_line || puzzle.solution_san}
    </div>
    {puzzle.solution_uci_line && puzzle.solution_uci_line.length > 1 && (
      <div style={{ color: '#6b7280', fontSize: '0.75rem', fontFamily: 'monospace' }}>
        UCI: {puzzle.solution_uci_line.join(' ')}
      </div>
    )}
  </div>
)}
```

---

## Execution Workflow

### RED — write failing tests first

No new backend logic — skip RED/GREEN for backend tests.

For frontend, visually confirm on load (manual check) that the Answer panel is hidden by default and appears on click.

### GREEN — implement

Apply changes as described above. Restart frontend dev server and verify manually:

1. Profile 99, active batch
2. Puzzle info bar shows `← Prev | 1/N | Next → | Edit | Answer`
3. Click **Answer** → panel appears below board with `solution_line` text and UCI line
4. Button label changes to **Hide**
5. Click **Hide** → panel disappears
6. Click **Next →** → navigates to next puzzle, answer panel is hidden again
7. Normal profiles (1, 2, 3) see no Answer button

### SHOWBOAT — `verification/phase9.6_show_answer.md`

```
showboat init verification/phase9.6_show_answer.md "Phase 9.6: Show Answer in Test Mode"
showboat note verification/phase9.6_show_answer.md "Verify answer panel hidden on load, visible on toggle, resets on nav"
showboat note verification/phase9.6_show_answer.md "Manual: profile 99 → Answer button toggles panel; Next nav resets it"
showboat verify verification/phase9.6_show_answer.md
```

### PLAYWRIGHT — `e2e/tests/phase9.6_show_answer.spec.ts`

Both servers must be running (`./test.sh`).

- Navigate to profile 99 training session with active batch
- Assert no answer panel visible on load
- Assert "Answer" button is visible in puzzle info bar
- Click Answer → assert answer panel appears and contains non-empty text
- Assert button label changes to "Hide"
- Click Hide → assert answer panel disappears
- Click Next → assert answer panel is hidden on the new puzzle
- Assert profile 1 training session has no Answer button

All existing Playwright tests must remain green.
