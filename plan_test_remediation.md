# Test Coverage Gap Remediation Plan

## Context

The chess_intuition_trainer project follows a phased plan (Phases 1-10) where each phase should have RED/GREEN TDD, SHOWBOAT verification docs, and Playwright E2E tests. Analysis of git history reveals that Phases 1-7 and Phase 9 have complete test coverage, but several gaps exist in Phase 9.6, Phase 10, and various post-phase fix/feature commits.

## Summary of Gaps

| Gap | Phase File | What's Missing | Severity |
|-----|-----------|----------------|----------|
| Phase 9.6: Show Answer + Solution Editing | `plan_phase_9.7.md` | Backend API tests, frontend tests, verification doc, Playwright E2E | HIGH |
| Phase 10: Challenge Mode (frontend/E2E) | `plan_phase_10.1.md` | Frontend tests for badge UI, verification doc, Playwright E2E | MEDIUM |
| JSON Import Workflow | `plan_phase_2.1.md` | All tests for `import_puzzles.py` (90 lines, zero tests) | HIGH |
| Training State Additions (median, total_xp, puzzle_ids) | `plan_phase_3.1.md` | Backend tests for median calc edge cases, API field tests | MEDIUM |
| Dashboard UX Fixes (Start Chapter 1 button, current_circle) | `plan_phase_4.1.md` | Frontend test for button, backend test for current_circle field | LOW |

### Not requiring plans (trivial/config changes):
- `728ca90` CORS wildcard -- 1-line config
- `29d7c19` remove text -- 1-line deletion
- `037ddbf` + `0b6fbe2` Guest profile -- 1-line data additions, no logic
- `7ff025a` export script -- read-only utility

## Execution Priority

1. **plan_phase_2.1.md** -- `import_puzzles.py` is foundational infrastructure with zero tests
2. **plan_phase_3.1.md** -- median calculation has real edge-case risk (division, even/odd, n=0)
3. **plan_phase_9.7.md** -- PUT /api/puzzles/{id}/solution endpoint has zero API tests
4. **plan_phase_10.1.md** -- mostly docs/E2E gaps; backend tests already exist
5. **plan_phase_4.1.md** -- smallest gap, minimal risk

## Deliverables

5 plan files following `plan_template.md` format:
- `plan_phase_2.1.md` -- JSON Import Workflow tests
- `plan_phase_3.1.md` -- Training State Additions tests
- `plan_phase_4.1.md` -- Dashboard UX Fixes tests
- `plan_phase_9.7.md` -- Show Answer + Solution Editing tests
- `plan_phase_10.1.md` -- Challenge Mode frontend/E2E tests

Each plan includes specific test function names, assertions, verification docs, and (where applicable) Playwright E2E specs. Since the implementation already exists, RED/GREEN is inverted: tests are written to validate existing code, and any test failure reveals an existing bug to fix.

## Key Files Referenced

### Test infrastructure:
- `backend/tests/conftest.py` -- `test_engine`, `test_db`, `seeded_db`, `test_client` fixtures
- `backend/tests/test_training.py` -- 553 lines, main training tests (add median/state tests here)
- `backend/tests/test_training_api.py` -- 209 lines, API tests (add solution endpoint tests here)
- `frontend/src/__tests__/TrainingSession.test.jsx` -- 270 lines (add answer toggle tests here)
- `frontend/src/__tests__/Dashboard.test.jsx` -- 178 lines (add Start Chapter 1 test here)
- `frontend/src/__tests__/ResultsScreen.test.jsx` -- 109 lines (add median display test here)

### Implementation files being tested:
- `backend/import_puzzles.py` -- JSON import (90 lines, ROOT constant needs monkeypatching)
- `backend/training.py:260-299` -- median calc + training state fields
- `backend/main.py:459-482` -- PUT /api/puzzles/{id}/solution endpoint
- `frontend/src/components/Dashboard.jsx:152-159` -- Start Chapter 1 button
- `frontend/src/components/TrainingSession.jsx` -- Answer toggle, Challenge Mode badge

## Verification

After all 5 plans are implemented:
```bash
cd backend && pytest -v                    # all backend tests green
cd frontend && npm test                     # all frontend tests green
./test.sh                                   # all Playwright E2E tests green
ls verification/                            # should have new verification docs
```
