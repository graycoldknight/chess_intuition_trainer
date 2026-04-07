# plan_phase_5.1.md — Fix Leaderboard Sort Order

## Context

The leaderboard renders rows in the order the backend returns them — profile insertion order (id ASC: Rishi=1, Raghav=2 always). `get_leaderboard()` in `gamification.py` does not sort. Raghav has 1494 XP vs Rishi's 643 but always appears second because his profile ID is lower. Players should be ranked by total XP descending.

**Key decision:** Sort in the frontend (`Leaderboard.jsx`) — it's a display concern and keeps the API response flexible.

---

## Files to Modify

| File | Change |
|------|--------|
| `frontend/src/components/Leaderboard.jsx` | Sort `data` by `total_xp` desc before rendering rows |
| `frontend/src/__tests__/Leaderboard.test.jsx` | Add test asserting higher-XP player renders first |

---

## Implementation

### `frontend/src/components/Leaderboard.jsx` — line 45

```jsx
// was:
{data.map((row) => {

// new:
{[...data].sort((a, b) => (b.total_xp ?? 0) - (a.total_xp ?? 0)).map((row) => {
```

### `frontend/src/__tests__/Leaderboard.test.jsx`

Add to `describe('Leaderboard')`:

```jsx
it('renders higher-XP player before lower-XP player', () => {
  const data = [
    { id: 1, name: 'Rishi',  total_xp: 643,  current_streak: 3, chapters_graduated: 0 },
    { id: 2, name: 'Raghav', total_xp: 1494, current_streak: 1, chapters_graduated: 0 },
  ];
  render(<Leaderboard data={data} />);
  const rows = screen.getAllByRole('row');
  // rows[0] is the header, rows[1] should be Raghav (higher XP)
  expect(rows[1]).toHaveTextContent('Raghav');
  expect(rows[2]).toHaveTextContent('Rishi');
});
```

---

## Execution Workflow

1. **RED** — add the test above, run `cd frontend && npx vitest run src/__tests__/Leaderboard.test.jsx` → should FAIL
2. **GREEN** — apply one-line sort change in `Leaderboard.jsx:45`, run test again → PASS
3. **Full suite** — `cd frontend && npm test` → all GREEN
4. **Manual** — open leaderboard in browser, confirm higher-XP player appears first
5. **No new Playwright test needed** — leaderboard is already exercised by `phase5_gamification.spec.ts`; this is a pure frontend rendering change
