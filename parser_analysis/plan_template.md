# Phase N: [Short Title]

## Context

[1–3 sentences describing the problem being solved and why it matters. Include the user-facing motivation.]

**Key decisions:**
- [Decision 1: what was chosen and why (or over what alternative)]
- [Decision 2]
- [Decision N]

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/models.py` | [what changes] |
| `backend/training.py` | [what changes] |
| `backend/main.py` | [what changes] |
| `frontend/src/components/Foo.jsx` | [what changes] |

---

## Data Model Change

*(Omit this section if no schema changes)*

### `[table_name]` table — [add column / new table / drop column]

```python
# SQLAlchemy column or model definition
```

**Migration for existing DB:**
```sql
ALTER TABLE [table] ADD COLUMN [col] [type];
```
Or delete `backend/chess_intuition.db` and let SQLAlchemy recreate it on startup.

---

## Implementation

### `backend/[file].py`

**[Function or area being changed]:**
```python
# was: old approach
# new: new approach
```

### `backend/main.py`

In the `[endpoint or function]` response dict (around line NNN), add:
```python
"[new_field]": [value],
```

### `frontend/src/components/[Component].jsx`

```jsx
{/* new JSX */}
```

---

## Execution Workflow

### RED — write failing tests first

Add to `backend/tests/test_training.py`:

```python
def test_[scenario_1]():
    # Arrange: set up state
    # Act: call function
    # Assert: expected outcome

def test_[scenario_2]():
    # ...
```

Run `cd backend && pytest tests/test_training.py -v` — new tests should be **RED**.

### GREEN — implement

Apply changes as described in Implementation above.

Run `cd backend && pytest` — all tests should be **GREEN**.

### SHOWBOAT — `verification/phase[N]_[slug].md`

```
showboat init verification/phase[N]_[slug].md "Phase N: [Title] Verification"
showboat note verification/phase[N]_[slug].md "[What this verification confirms]"
showboat exec verification/phase[N]_[slug].md bash "cd backend && pytest tests/test_training.py -v -k '[relevant keywords]'"
showboat exec verification/phase[N]_[slug].md bash "cd backend && pytest -v"
showboat note verification/phase[N]_[slug].md "[Manual check description]"
showboat exec verification/phase[N]_[slug].md bash "curl -s http://localhost:8000/api/[endpoint] | python -m json.tool"
showboat verify verification/phase[N]_[slug].md
```

### PLAYWRIGHT — `e2e/tests/phase[N]_[slug].spec.ts`

Both servers must be running (`./test.sh`).

- [Step 1: navigate to / set up state]
- [Step 2: trigger the feature]
- [Assert: expected visible behavior]
- [Assert: expected API state]
- Screenshot [key UI element] to confirm [what]

All existing Playwright tests must remain green.
