# Phase 5: Gamification Verification

*2026-04-05T14:26:25Z by Showboat 0.6.1*
<!-- showboat-id: 4bdc264b-04db-438e-95fb-413316d5cd49 -->

Verify XP formula, badge awarding, and leaderboard.

```bash
cd /home/raj/projects/chess_intuition_trainer/backend && python3 -m pytest tests/test_gamification.py 2>&1 | grep -oE "[0-9]+ passed"
```

```output
24 passed
```

Verify XP calculation: correct in 4s, circle 3, 7-day streak = floor((10+20)*1.2*1.5) = 54

```bash
cd /home/raj/projects/chess_intuition_trainer/backend && python3 -c "from gamification import calculate_xp; xp=calculate_xp(time_ms=4000, success=True, circle=3, streak=7); print(f'XP={xp}, expected=54, match={xp==54}')"
```

```output
XP=54, expected=54, match=True
```

Verify frontend tests: BadgeDisplay and Leaderboard components.

```bash
cd /home/raj/projects/chess_intuition_trainer/frontend && npx vitest run src/__tests__/BadgeDisplay.test.jsx src/__tests__/Leaderboard.test.jsx 2>&1 | grep -oE "[0-9]+ passed"
```

```output
2 passed
13 passed
```

Verify leaderboard returns both kids (Rishi and Raghav, not Raj).

```bash
curl -s http://localhost:8000/api/leaderboard | python3 -c "import sys,json; b=json.load(sys.stdin); print([r['name'] for r in b])"
```

```output
['Rishi', 'Raghav']
```

Verify badge API returns all 33 badge definitions for a profile.

```bash
curl -s http://localhost:8000/api/badges/1 | python3 -c "import sys,json; b=json.load(sys.stdin); print(f'Total badges: {len(b)}, Earned: {sum(1 for x in b if x[\"earned\"])}')"
```

```output
Total badges: 33, Earned: 0
```
