# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Backend (FastAPI, port 8000):**
```bash
cd backend && uvicorn main:app --port 8000 --reload
```

**Frontend (Vite/React, port 5173):**
```bash
cd frontend && npm run dev
```

**Backend tests (pytest):**
```bash
cd backend && pytest
cd backend && pytest tests/test_training.py  # single file
```

**Frontend tests (Vitest):**
```bash
cd frontend && npm test
```

**E2E tests (Playwright):**
```bash
./test.sh  # starts both servers, seeds test profile, opens Playwright UI
```

## Architecture

**Purpose:** Chess tactics trainer using Christopher Yoo's spaced repetition method with Susan Polgar's puzzle book. Kids solve 50-100 puzzles per "batch" across 4-5 "circles" (repetition rounds) with XP/badges/leaderboard gamification.

**Backend** (`backend/`): FastAPI + SQLAlchemy + SQLite
- `main.py` — all API endpoints (chapters, extraction, training loop, gamification, parent panel)
- `training.py` — Yoo method state machine: active batch selection, circle progression, graduation logic
- `gamification.py` — XP calculation, badge awarding, leaderboard
- `extraction.py` — PDF vision extraction via Gemini API, FEN/UCI puzzle parsing, multi-move solutions
- `models.py` — 9 SQLAlchemy tables: profiles, chapters, puzzles, batches, attempts, sessions, badge_definitions, earned_badges, puzzle_mastery
- `seed.py` — seeds 22 chapters (Polgar TOC) and 8 badge definitions on startup
- `database.py` — SQLite engine with foreign key enforcement; `init_db()` called on startup

**Frontend** (`frontend/src/`): React 18 + Vite + react-chessboard
- `App.jsx` — route structure: `/` → ProfileSelect, `/dashboard/:id` → Dashboard, `/train/:id` → TrainingSession, `/results/:id` → ResultsScreen, `/badges/:id`, `/leaderboard`, `/parent`
- `TrainingSession.jsx` — core puzzle loop: fetch next puzzle → render board → handle move → post attempt → repeat
- `services/api.js` — all fetch calls to `http://localhost:8000`

**Training flow:**
1. Profile selected → Dashboard loads chapter list and stats
2. User picks chapter → `POST /api/training/create-batch` creates a Batch (4-5 circles)
3. TrainingSession calls `GET /api/training/next-puzzle/{profileId}` → renders puzzle
4. User plays move → `POST /api/training/attempt` → backend returns XP delta, badge updates
5. Circle completes → ResultsScreen → next circle or graduation pending
6. Parent approves graduation → batch advances to next chapter

**E2E test setup:**
- Profile ID 99 is reserved for E2E tests
- `backend/test_setup.py create/destroy` manages test data
- `test.sh` orchestrates full server lifecycle for Playwright

## Planning

When in plan mode:
1. Always structure the plan using `@plan_template.md` as the template (project root).
2. Save the plan file to the **project root** as `plan_phase<N>.md` (e.g. `plan_phase15.md`). Infer the phase number from context or ask if unclear.
3. After the user approves the plan, always present these next steps before doing anything else:

   **Plan saved to `plan_phase<N>.md`. Recommended next steps:**
   1. `/model sonnet` — switch model if currently in Opus (persists across `/clear`)
   2. `/clear` — clear the context cache
   3. `execute @plan_phase<N>.md` — implement the plan

   **To do it in two steps:** run `/model sonnet` first (if needed), then `/clear` and in the next message `execute @plan_phase<N>.md`.

## Key constraints

- Stockfish binary at `backend/bin/stockfish-linux` (pre-compiled, don't replace)
- Backend `.env` requires `GOOGLE_API_KEY` and `GEMINI_MODEL` for extraction
- SQLite DB auto-created at `backend/chess_intuition.db`; destroyed and recreated by E2E tests
- Playwright E2E tests are a hard gate — run `./test.sh` before declaring any phase done
- CORS origins whitelisted in `main.py`: ports 5173, 5174, 3000
