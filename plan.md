# Chess Intuition Trainer - Implementation Plan

## Context

Raj wants to train his two kids' chess tactical intuition using Christopher Yoo's modified spaced repetition method with Susan Polgar's "Chess Tactics for Champions" as primary material.

**Users:** Rishi (9yo, USCF 1228), Raghav (7yo, USCF 1008), Raj (parent/admin)

**Yoo's Method:** Micro-cycles of 50-100 puzzles, 4-5 repetition circles per batch, 30-60 min daily cap, graduate when avg solve time < 15s. Pure speed/pattern recognition -- no hints or explanations.

**Polgar Book:** 22 chapters, ~600+ puzzles organized by tactical motif (forks, pins, deflection, discoveries, etc.), difficulty progresses within and across chapters.

---

## Decisions

| Decision | Choice |
|----------|--------|
| Puzzle source | LLM vision extraction from Polgar PDF |
| Extraction timing | Per-chapter on-demand (as kids reach each chapter) |
| User profiles | Separate profiles, independent progress |
| Difficulty model | Same start (Ch 1), own pace |
| Progression | Parent approval to graduate |
| Architecture | Standalone app, copy components from chess_blunder_trainer |
| Deployment | Local first, deploy later |
| Gamification | Full (XP, badges, streaks, sibling leaderboard) |

---

## Project Structure

```
~/projects/chess_intuition_trainer/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── models.py            # SQLAlchemy ORM (9 tables)
│   ├── database.py          # SQLite engine (copy from blunder trainer)
│   ├── extraction.py        # PDF -> FEN pipeline via vision LLM
│   ├── training.py          # Yoo method state machine
│   ├── gamification.py      # XP, badges, leaderboard
│   ├── llm.py               # Vision LLM client (adapt from blunder trainer)
│   ├── chess_engine.py      # Stockfish wrapper (copy from blunder trainer)
│   ├── requirements.txt
│   ├── tests/               # pytest test suite
│   └── bin/stockfish-linux   # Copy from blunder trainer
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx           # Router shell
│       ├── services/api.js   # API client
│       ├── hooks/useStockfish.js  # Copy from blunder trainer
│       ├── __tests__/        # Vitest test suite
│       └── components/
│           ├── ProfileSelect.jsx    # Kid picker (no passwords)
│           ├── Dashboard.jsx        # Progress hub
│           ├── TrainingSession.jsx  # Core puzzle-solving screen
│           ├── ChessBoard.jsx       # react-chessboard wrapper
│           ├── Stopwatch.jsx        # Copy from blunder trainer
│           ├── SessionTimer.jsx     # 60-min countdown
│           ├── CircleProgress.jsx   # Visual batch/circle tracker
│           ├── ResultsScreen.jsx    # Post-circle/session stats
│           ├── BadgeDisplay.jsx     # Badge gallery
│           ├── Leaderboard.jsx      # Sibling comparison
│           └── ParentPanel.jsx      # Extraction review + graduation approval
├── verification/                    # Showboat executable verification docs (all phases)
├── e2e/
│   ├── playwright.config.ts         # Playwright config
│   └── tests/                       # Agentic E2E tests (Phases 3-7)
└── chess_tactics_for_champions_by_Polgar.pdf  # Already present
```

---

## Data Model (SQLite)

### profiles
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT UNIQUE | "Rishi", "Raghav", "Raj" |
| role | TEXT | "student" or "parent" |
| uscf_rating | INTEGER | |
| total_xp | INTEGER | Denormalized for fast reads |
| current_streak | INTEGER | Days |
| longest_streak | INTEGER | |
| last_session_date | TEXT | "YYYY-MM-DD" |

### chapters
Seeded once from Polgar TOC. 22 rows.
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | 1-22 |
| title | TEXT | "Forks and Double Attacks" |
| section | TEXT | "TACTICAL ELEMENTS" / "SAVE THE GAME" / "OTHER" |
| start_page | INTEGER | PDF page number |
| end_page | INTEGER | |
| puzzle_count | INTEGER | Filled after extraction |
| extraction_status | TEXT | pending / extracting / review / verified |

### puzzles
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| chapter_id | FK chapters | |
| puzzle_number | INTEGER | 1-50 within chapter |
| fen | TEXT | Board position |
| turn | TEXT | "w" or "b" |
| solution_san | TEXT | First move SAN ("Nf6+") |
| solution_uci | TEXT | First move UCI ("g8f6") |
| solution_line | TEXT | Full solution text from book |
| pdf_page | INTEGER | Source page |
| verified | INTEGER | 0=unverified, 1=parent-approved |
| extraction_confidence | REAL | 0-1 |
| UNIQUE(chapter_id, puzzle_number) | | |

### batches
A micro-cycle group of puzzles assigned to a profile.
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| profile_id | FK profiles | |
| chapter_id | FK chapters | |
| puzzle_ids | JSON | Ordered list of puzzle IDs |
| total_puzzles | INTEGER | |
| current_circle | INTEGER | 1-5 |
| status | TEXT | active / ready_to_graduate / graduated |

### attempts
Every single puzzle solve. Core analytics table.
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| profile_id | FK profiles | |
| puzzle_id | FK puzzles | |
| batch_id | FK batches | |
| circle | INTEGER | Which circle (1-5) |
| success | INTEGER | 1=correct, 0=wrong |
| time_taken_ms | INTEGER | Millisecond precision for speed drills |
| user_move | TEXT | What the user played (UCI) |
| attempted_at | DATETIME | |

### sessions
Daily training sessions. Enforces 60-min cap.
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| profile_id | FK profiles | |
| started_at | DATETIME | |
| ended_at | DATETIME | |
| duration_seconds | INTEGER | |
| puzzles_attempted | INTEGER | |
| puzzles_correct | INTEGER | |
| xp_earned | INTEGER | |

### puzzle_mastery
Per-profile, per-puzzle mastery record. Aggregates attempt history for future spaced repetition.
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| profile_id | FK profiles | |
| puzzle_id | FK puzzles | |
| total_attempts | INTEGER | Total times this puzzle was seen |
| total_correct | INTEGER | Times solved correctly |
| total_wrong | INTEGER | Times solved incorrectly |
| best_time_ms | INTEGER | Fastest correct solve |
| last_time_ms | INTEGER | Most recent solve time |
| first_seen_at | DATETIME | When first attempted |
| last_seen_at | DATETIME | Most recent attempt |
| wrong_moves | JSON | List of wrong moves played: `[{"move":"e2e4","at":"...","circle":1}, ...]` |
| ease_factor | REAL DEFAULT 2.5 | SM-2 ease factor (for future spaced repetition) |
| interval_days | INTEGER DEFAULT 1 | SM-2 interval (for future spaced repetition) |
| next_review_date | TEXT | "YYYY-MM-DD" (for future spaced repetition scheduling) |
| UNIQUE(profile_id, puzzle_id) | | |

Updated on every attempt via `record_attempt()`. The `wrong_moves` JSON captures exactly what the kid played each time they got it wrong, enabling future analysis of recurring mistake patterns. The SM-2 fields (`ease_factor`, `interval_days`, `next_review_date`) are populated but not actively used until spaced repetition is implemented.

### badge_definitions + earned_badges
Badge catalog (seeded) and per-profile earned badges.

---

## PDF Extraction Pipeline (`backend/extraction.py`)

### Flow (per chapter, on demand)
1. **Page range** -- `chapters` table has start/end PDF page numbers
2. **Separate intro vs puzzle pages** -- Intro pages have inline text + diagrams (skip). Puzzle pages have "N. White/Black to move" headers
3. **Vision LLM extracts diagrams** -- Send each puzzle page image to Gemini 2.0 Flash or GPT-4o. Prompt returns JSON array: `[{puzzle_number, side_to_move, fen}]`
4. **Text LLM extracts solutions** -- Solutions section at chapter end. Parse numbered solutions for first move in SAN
5. **Merge + validate** -- Cross-reference diagrams with solutions. Use `python-chess` to verify solution move is legal in extracted FEN. Convert SAN to UCI
6. **Stockfish spot-check** -- Optionally confirm the book's solution is the engine's top choice
7. **Flag mismatches** -- Illegal moves or low confidence flagged for parent review

### Parent Review UI (in ParentPanel.jsx)
- Board rendered from extracted FEN alongside PDF page reference
- Approve / Edit FEN / Edit Solution / Reject per puzzle
- Bulk "Verify All" when extraction looks good

### Key: PyMuPDF (`fitz`) renders PDF pages to images for the vision LLM

---

## Core Training Loop (Yoo Method)

### State Machine (`backend/training.py`)
```
[No Active Batch]
  -> Parent creates batch from verified chapter puzzles
  -> [Circle 1 Active]
     -> Solve all puzzles in order, record time per puzzle
     -> [Circle 1 Complete]
  -> [Circle 2 Active] ... [Circle 5 Active]
  -> [All Circles Complete]
     -> Avg time on last circle < 15s? -> "ready_to_graduate"
     -> Avg time >= 15s? -> suggest more circles
  -> [Parent Approves] -> "graduated" -> next batch
```

### Key Rules
- Puzzles always served in same order within a batch (builds positional memory)
- Single-move validation only (find the first key move)
- No hints, no explanations -- pure pattern recognition speed drill
- Session timer enforced: no more puzzles after 60 min daily
- Board auto-orients based on side to move

### Training API
```
GET  /api/training/state/{profile_id}         # Full state
GET  /api/training/next-puzzle/{profile_id}   # Next puzzle
POST /api/training/attempt                     # Record attempt
POST /api/training/start-session/{profile_id} # Begin session
POST /api/training/end-session/{session_id}   # End session
POST /api/training/create-batch               # Parent creates batch
POST /api/training/approve-graduation/{batch_id}  # Parent approves
```

---

## Gamification (`backend/gamification.py`)

### XP Formula
- Base: 10 XP per correct, 2 XP per incorrect (participation)
- Speed bonus (correct only): <5s +20, <10s +15, <15s +10, <30s +5
- Circle multiplier: C1 1.0x, C2 1.1x, C3 1.2x, C4 1.3x, C5 1.5x
- Streak multiplier: 3+ days 1.2x, 7+ days 1.5x, 14+ days 2.0x, 30+ days 3.0x

### Badges
- **Theme mastery** (22): "Fork Master", "Pin Expert", etc. -- graduate each chapter
- **Speed**: "Lightning Reflexes" (<3s), "Speed Demon" (circle avg <10s)
- **Streak**: 3/7/14/30-day streaks
- **Milestone**: "First Solve", "Century" (100), "500 Club", "Full Book"
- **Improvement**: "Half the Time" (circle N avg < 50% of circle 1)

### Sibling Leaderboard (fair despite rating gap)
Compare on: Total XP, current streak, speed improvement %, chapters graduated, daily XP, best single-puzzle time. Each metric has its own "leader" -- both kids can win at something.

---

## UI Screens

### ProfileSelect
Two kid cards + parent login. Each card shows name, streak, XP. No passwords (local app).

### Dashboard
- Current batch/chapter/circle progress bar
- Today's stats (puzzles solved, time trained / 60:00 cap)
- Speed trend chart (avg time per circle)
- Recent badges, leaderboard link

### TrainingSession (core screen -- adapted from blunder trainer App.jsx)
- Header: chapter name, circle #, puzzle N/total, session timer
- Interactive chessboard (react-chessboard) with auto-orientation
- Per-puzzle stopwatch (millisecond display)
- Correct: green flash + confetti + XP popup, auto-advance 1s
- Wrong: red flash + show correct move arrow, auto-advance 2s
- Circle progress dots along bottom

### ResultsScreen
- Circle stats: accuracy, avg time, best time
- Improvement comparison vs previous circles
- XP earned, new badges unlocked

### ParentPanel (3 tabs)
1. **Chapters** -- extraction status, extract/review buttons
2. **Puzzle Review** -- verify extracted puzzles (board + solution)
3. **Graduations** -- approve/deny per child, circle-by-circle speed chart

---

## Reuse from chess_blunder_trainer

| Copy as-is | Adapt |
|------------|-------|
| `Stopwatch.jsx` | `App.jsx` puzzle solving flow -> `TrainingSession.jsx` |
| `useStockfish.js` | `api.js` endpoints |
| `database.py` (change DB name) | `llm.py` (add vision API) |
| `chess_engine.py` | `main.py` (new endpoints) |
| `bin/stockfish-linux` | |
| `package.json` deps | |

---

## Implementation Phases (Red/Green TDD)

Each phase follows a four-step cycle:
1. **RED** -- write failing tests first
2. **GREEN** -- implement just enough code to make them pass
3. **SHOWBOAT** -- create executable verification doc proving the phase works (all phases)
4. **PLAYWRIGHT** -- agentic browser E2E tests (Phases 3-7 only, requires UI)

No production code without a failing test driving it. No phase is "done" until `showboat verify` passes.

### Phase 1: Foundation

**RED -- write tests first:**
- `backend/tests/test_models.py`: Test all 9 tables can be created, foreign key constraints work, unique constraints enforced (e.g., duplicate chapter_id+puzzle_number rejected)
- `backend/tests/test_database.py`: Test DB engine creation, session lifecycle, table auto-creation
- `backend/tests/test_seed.py`: Test seeding 22 chapters with correct titles/page ranges, 3 profiles (Rishi/Raghav/Raj), badge definitions inserted with correct categories
- `backend/tests/test_main.py`: Test `GET /` health check returns 200

**GREEN -- implement:**
- Project scaffolding, copy reusable files
- `models.py` with all tables, `database.py`
- Seed script for chapters, profiles, badges
- Basic FastAPI with health check
- Run tests -- all green

**SHOWBOAT -- `verification/phase1_foundation.md`:**
```
showboat init verification/phase1_foundation.md "Phase 1: Foundation Verification"
showboat note verification/phase1_foundation.md "Verify database tables, seed data, and API health."
showboat exec verification/phase1_foundation.md bash "cd backend && pytest tests/test_models.py tests/test_database.py tests/test_seed.py tests/test_main.py -v"
showboat exec verification/phase1_foundation.md bash "cd backend && python -c \"from database import engine; from models import *; from sqlalchemy import inspect; print(inspect(engine).get_table_names())\""
showboat exec verification/phase1_foundation.md bash "cd backend && python -c \"from database import SessionLocal; from models import Chapter, Profile; db=SessionLocal(); print(f'Chapters: {db.query(Chapter).count()}, Profiles: {db.query(Profile).count()}')\""
showboat exec verification/phase1_foundation.md bash "curl -s http://localhost:8000/ | python -m json.tool"
showboat verify verification/phase1_foundation.md
```

### Phase 2: Extraction Pipeline

**RED -- write tests first:**
- `backend/tests/test_extraction.py`:
  - Test `extract_page_images(chapter_id)` returns correct number of PIL images for known page range
  - Test `parse_diagram_response(llm_json)` correctly parses vision LLM output into puzzle dicts
  - Test `parse_solution_response(llm_json)` extracts first move SAN from solution text
  - Test `merge_and_validate(diagrams, solutions)` matches puzzle numbers, flags illegal moves, converts SAN->UCI
  - Test merge rejects puzzle where solution move is illegal in FEN (using a known-bad FEN)
  - Test merge sets `extraction_confidence=0.0` on mismatches
- `backend/tests/test_extraction_api.py`:
  - Test `POST /api/extract-chapter/1` returns 202 and sets chapter status to "extracting"
  - Test `GET /api/chapters` returns all 22 with statuses
  - Test `GET /api/puzzles/unverified/1` returns extracted puzzles with verified=0
  - Test `PUT /api/puzzles/{id}/verify` sets verified=1
  - Test `POST /api/chapters/1/verify-all` bulk-approves all puzzles

**GREEN -- implement:**
- `extraction.py` with PyMuPDF page-to-image + vision LLM prompts
- Solution text extraction
- Merge + python-chess validation logic
- Extraction API endpoints in `main.py`
- Extract Chapter 1 as proof of concept, manually verify
- Run tests -- all green

**SHOWBOAT -- `verification/phase2_extraction.md`:**
```
showboat init verification/phase2_extraction.md "Phase 2: Extraction Pipeline Verification"
showboat note verification/phase2_extraction.md "Verify PDF extraction, FEN validation, and chapter API."
showboat exec verification/phase2_extraction.md bash "cd backend && pytest tests/test_extraction.py tests/test_extraction_api.py -v"
showboat exec verification/phase2_extraction.md bash "curl -s http://localhost:8000/api/chapters | python -m json.tool | head -30"
showboat exec verification/phase2_extraction.md bash "curl -s -X POST http://localhost:8000/api/extract-chapter/1 | python -m json.tool"
showboat note verification/phase2_extraction.md "Verify extracted puzzles have valid FENs using python-chess."
showboat exec verification/phase2_extraction.md bash "curl -s http://localhost:8000/api/puzzles/unverified/1 | python -c \"import sys,json; puzzles=json.load(sys.stdin); print(f'Extracted {len(puzzles)} puzzles'); [print(f'  #{p[\\\"puzzle_number\\\"]}: {p[\\\"fen\\\"]} -> {p[\\\"solution_san\\\"]}') for p in puzzles[:5]]\""
showboat exec verification/phase2_extraction.md bash "cd backend && python -c \"
import chess
from database import SessionLocal
from models import Puzzle
db=SessionLocal()
puzzles=db.query(Puzzle).filter(Puzzle.chapter_id==1, Puzzle.verified==0).all()
valid=0
for p in puzzles:
    board=chess.Board(p.fen)
    try:
        board.push_san(p.solution_san)
        valid+=1
    except: pass
print(f'Valid FENs: {valid}/{len(puzzles)}')
\""
showboat verify verification/phase2_extraction.md
```

### Phase 3: Core Training Loop

**RED -- write tests first:**
- `backend/tests/test_training.py`:
  - Test `create_batch(profile_id, chapter_id)` creates batch with correct puzzle_ids from verified puzzles only
  - Test `get_next_puzzle(profile_id)` returns first unsolved puzzle in current circle
  - Test `get_next_puzzle` returns None when circle is complete (all puzzles attempted)
  - Test `record_attempt(correct=True)` stores attempt with time_taken_ms and increments session counters
  - Test `record_attempt(correct=False)` records wrong attempt with user_move and appends to `puzzle_mastery.wrong_moves` JSON
  - Test `record_attempt` creates/updates `puzzle_mastery` row: increments total_attempts, total_correct/wrong, updates best_time_ms, last_time_ms, timestamps
  - Test `puzzle_mastery.wrong_moves` accumulates across circles: wrong on C1 and C3 -> 2 entries with circle numbers and timestamps
  - Test circle auto-advances: after all puzzles attempted in circle 1, `current_circle` becomes 2
  - Test same puzzles served in same order across circles
  - Test graduation readiness: avg time < 15000ms on last circle -> status = "ready_to_graduate"
  - Test graduation NOT ready: avg time >= 15000ms -> status stays "active", suggests more circles
  - Test `approve_graduation(batch_id)` sets status to "graduated"
  - Test session cap: `start_session` works, `get_next_puzzle` returns None after 60 min elapsed
- `backend/tests/test_training_api.py`:
  - Test all training API endpoints return correct status codes and payloads
  - Test `GET /api/training/state/{profile_id}` returns complete state object
- `frontend/src/__tests__/TrainingSession.test.jsx` (Vitest + jsdom):
  - Test board renders with correct FEN and orientation
  - Test correct move triggers success state (green flash)
  - Test wrong move triggers failure state (red flash + correct move arrow)
  - Test auto-advance after correct/wrong
  - Test stopwatch starts on puzzle display and stops on solve

**GREEN -- implement:**
- `training.py` state machine
- Training API endpoints
- `ProfileSelect.jsx` + React Router
- `TrainingSession.jsx` (board, move validation, attempt recording)
- `Stopwatch.jsx` + `SessionTimer.jsx`
- Run tests -- all green

**SHOWBOAT -- `verification/phase3_training.md`:**
```
showboat init verification/phase3_training.md "Phase 3: Training Loop Verification"
showboat note verification/phase3_training.md "Verify batch creation, puzzle serving, attempt recording, and circle progression."
showboat exec verification/phase3_training.md bash "cd backend && pytest tests/test_training.py tests/test_training_api.py -v"
showboat note verification/phase3_training.md "Create a batch for Rishi (profile_id=1) from Chapter 1."
showboat exec verification/phase3_training.md bash "curl -s -X POST http://localhost:8000/api/training/create-batch -H 'Content-Type: application/json' -d '{\"profile_id\":1,\"chapter_id\":1}' | python -m json.tool"
showboat note verification/phase3_training.md "Get training state -- should show active batch, circle 1."
showboat exec verification/phase3_training.md bash "curl -s http://localhost:8000/api/training/state/1 | python -m json.tool"
showboat note verification/phase3_training.md "Get next puzzle and record a correct attempt."
showboat exec verification/phase3_training.md bash "curl -s http://localhost:8000/api/training/next-puzzle/1 | python -m json.tool"
showboat exec verification/phase3_training.md bash "curl -s -X POST http://localhost:8000/api/training/attempt -H 'Content-Type: application/json' -d '{\"profile_id\":1,\"puzzle_id\":1,\"batch_id\":1,\"circle\":1,\"success\":true,\"time_taken_ms\":8500,\"user_move\":\"g8f6\"}' | python -m json.tool"
showboat note verification/phase3_training.md "Verify puzzle_mastery row was created."
showboat exec verification/phase3_training.md bash "cd backend && python -c \"from database import SessionLocal; from models import PuzzleMastery; db=SessionLocal(); m=db.query(PuzzleMastery).first(); print(f'attempts={m.total_attempts}, correct={m.total_correct}, best_ms={m.best_time_ms}')\""
showboat verify verification/phase3_training.md
```

**PLAYWRIGHT -- agentic manual testing (both servers running):**
- `e2e/tests/phase3_training.spec.ts`:
  - Navigate to `/` -- verify ProfileSelect shows Rishi and Raghav cards
  - Click Rishi's profile -- verify Dashboard loads with his name
  - Click "Continue Training" -- verify TrainingSession screen renders chessboard
  - Verify chessboard displays a position (board has pieces, not empty)
  - Verify puzzle header shows "Ch 1: Forks | Circle 1 | Puzzle 1/50"
  - Verify stopwatch is running (time display changes between two screenshots)
  - Verify session timer shows countdown (e.g., "59:58 / 60:00")
  - Make a wrong move via drag-and-drop -- verify red flash appears and correct move arrow shown
  - Verify board resets after ~2s and advances to next puzzle
  - Screenshot comparison: capture puzzle 1 board, advance to puzzle 2, verify boards differ

### Phase 4: Dashboard + Results

**RED -- write tests first:**
- `backend/tests/test_dashboard_api.py`:
  - Test `GET /api/dashboard/{profile_id}` returns current batch, circle stats, streak, XP
  - Test circle stats include avg_time_ms and accuracy per circle
  - Test streak calculation: consecutive days with sessions = correct streak count
  - Test streak resets: gap day -> streak = 0
  - Test session daily cap: `GET /api/training/state` includes `session_time_remaining_seconds`
- `frontend/src/__tests__/Dashboard.test.jsx`:
  - Test renders current chapter/circle/progress
  - Test renders speed trend (avg time per circle)
  - Test "Continue Training" button links to session
  - Test shows "Session Complete" when daily cap hit
- `frontend/src/__tests__/ResultsScreen.test.jsx`:
  - Test renders circle stats (accuracy, avg time, best time)
  - Test shows improvement percentage vs previous circle
  - Test shows "Ready to Graduate" when threshold met

**GREEN -- implement:**
- `Dashboard.jsx` with progress display
- `ResultsScreen.jsx` with circle comparison
- `CircleProgress.jsx`
- Dashboard + session cap API endpoints
- Run tests -- all green

**SHOWBOAT -- `verification/phase4_dashboard.md`:**
```
showboat init verification/phase4_dashboard.md "Phase 4: Dashboard & Results Verification"
showboat note verification/phase4_dashboard.md "Verify dashboard API returns correct stats, streaks, and circle comparisons."
showboat exec verification/phase4_dashboard.md bash "cd backend && pytest tests/test_dashboard_api.py -v"
showboat exec verification/phase4_dashboard.md bash "curl -s http://localhost:8000/api/dashboard/1 | python -m json.tool"
showboat note verification/phase4_dashboard.md "Verify circle stats show avg_time_ms and accuracy."
showboat exec verification/phase4_dashboard.md bash "curl -s http://localhost:8000/api/training/circle-stats/1 | python -m json.tool"
showboat note verification/phase4_dashboard.md "Verify streak calculation after consecutive sessions."
showboat exec verification/phase4_dashboard.md bash "cd backend && python -c \"from database import SessionLocal; from models import Profile; db=SessionLocal(); p=db.query(Profile).get(1); print(f'streak={p.current_streak}, last_session={p.last_session_date}')\""
showboat verify verification/phase4_dashboard.md
```

**PLAYWRIGHT -- agentic manual testing:**
- `e2e/tests/phase4_dashboard.spec.ts`:
  - Navigate to Rishi's dashboard -- verify progress bar shows current chapter/circle
  - Verify "Today's Stats" section shows puzzles solved count and time trained
  - Verify speed trend chart renders (canvas/SVG element exists with data)
  - Complete a training circle (solve all puzzles) -- verify ResultsScreen appears
  - On ResultsScreen: verify circle stats (accuracy %, avg time) are displayed
  - Verify improvement comparison shows "X% faster" if circle > 1
  - Verify "Start Circle N" button appears and navigates back to TrainingSession
  - Navigate back to Dashboard -- verify progress updated (circle incremented)

### Phase 5: Gamification

**RED -- write tests first:**
- `backend/tests/test_gamification.py`:
  - Test XP base: correct=10, wrong=2
  - Test speed bonus: <5s->+20, <10s->+15, <15s->+10, <30s->+5, >=30s->+0
  - Test circle multiplier: C1=1.0x, C2=1.1x, ..., C5=1.5x
  - Test streak multiplier: 3d=1.2x, 7d=1.5x, 14d=2.0x, 30d=3.0x
  - Test full formula: e.g., correct in 4s on circle 3 with 7-day streak = floor((10+20)*1.2*1.5) = 54 XP
  - Test badge awarding: "Fork Master" earned when Ch 1 batch graduated
  - Test badge awarding: "Lightning Reflexes" earned when any puzzle solved in <3s
  - Test badge NOT double-awarded: earning same badge twice is idempotent
  - Test leaderboard returns both profiles with XP, streak, chapters graduated, improvement %
- `frontend/src/__tests__/BadgeDisplay.test.jsx`:
  - Test renders earned badges with icons
  - Test unearned badges shown as locked/grayed
- `frontend/src/__tests__/Leaderboard.test.jsx`:
  - Test renders both kids' stats side by side
  - Test highlights leader per metric

**GREEN -- implement:**
- `gamification.py` (XP calculator, badge checker, leaderboard)
- `BadgeDisplay.jsx`, `Leaderboard.jsx`
- Wire XP/badge earning into `record_attempt` flow
- Streak tracking in profile updates
- Run tests -- all green

**SHOWBOAT -- `verification/phase5_gamification.md`:**
```
showboat init verification/phase5_gamification.md "Phase 5: Gamification Verification"
showboat note verification/phase5_gamification.md "Verify XP formula, badge awarding, and leaderboard."
showboat exec verification/phase5_gamification.md bash "cd backend && pytest tests/test_gamification.py -v"
showboat note verification/phase5_gamification.md "Verify XP calculation: correct in 4s, circle 3, 7-day streak = floor((10+20)*1.2*1.5) = 54"
showboat exec verification/phase5_gamification.md bash "cd backend && python -c \"from gamification import calculate_xp; xp=calculate_xp(time_ms=4000, success=True, circle=3, streak=7); print(f'XP={xp}, expected=54, match={xp==54}')\""
showboat note verification/phase5_gamification.md "Verify badge earned after chapter graduation."
showboat exec verification/phase5_gamification.md bash "cd backend && python -c \"from database import SessionLocal; from models import EarnedBadge; db=SessionLocal(); badges=db.query(EarnedBadge).filter_by(profile_id=1).all(); print(f'Badges earned: {len(badges)}'); [print(f'  {b.badge_id}') for b in badges]\""
showboat note verification/phase5_gamification.md "Verify leaderboard returns both kids."
showboat exec verification/phase5_gamification.md bash "curl -s http://localhost:8000/api/leaderboard | python -m json.tool"
showboat verify verification/phase5_gamification.md
```

**PLAYWRIGHT -- agentic manual testing:**
- `e2e/tests/phase5_gamification.spec.ts`:
  - Solve a puzzle correctly -- verify XP popup appears with a number
  - Navigate to Dashboard -- verify total XP increased
  - Navigate to Badge gallery -- verify badges render (earned vs locked visual difference)
  - Navigate to Leaderboard -- verify both Rishi and Raghav rows appear
  - Verify leaderboard shows multiple metrics (XP, streak, chapters)
  - Verify leader indicator highlights the higher value per metric
  - Solve a puzzle in <3s -- verify "Lightning Reflexes" badge appears as newly earned

### Phase 6: Parent Panel

**RED -- write tests first:**
- `backend/tests/test_parent_api.py`:
  - Test `GET /api/chapters` shows extraction status per chapter
  - Test `POST /api/extract-chapter/{id}` only works for parent role
  - Test `GET /api/graduations/pending` returns batches with "ready_to_graduate" status
  - Test `POST /api/training/approve-graduation/{batch_id}` changes status and auto-suggests next batch
  - Test `POST /api/training/create-batch` validates chapter is verified before creating batch
- `frontend/src/__tests__/ParentPanel.test.jsx`:
  - Test renders 3 tabs (Chapters, Puzzle Review, Graduations)
  - Test Chapter tab shows extraction status badges
  - Test Graduation tab shows pending approvals per child
  - Test approve button calls API and updates UI

**GREEN -- implement:**
- `ParentPanel.jsx` with 3 tabs
- Puzzle review UI (board + solution side by side)
- Graduation approval flow
- Batch creation with chapter validation
- Run tests -- all green

**SHOWBOAT -- `verification/phase6_parent.md`:**
```
showboat init verification/phase6_parent.md "Phase 6: Parent Panel Verification"
showboat note verification/phase6_parent.md "Verify parent-only access, graduation approval, and batch creation."
showboat exec verification/phase6_parent.md bash "cd backend && pytest tests/test_parent_api.py -v"
showboat note verification/phase6_parent.md "Verify graduation pending list."
showboat exec verification/phase6_parent.md bash "curl -s http://localhost:8000/api/graduations/pending | python -m json.tool"
showboat note verification/phase6_parent.md "Approve graduation and verify next batch suggested."
showboat exec verification/phase6_parent.md bash "curl -s -X POST http://localhost:8000/api/training/approve-graduation/1 | python -m json.tool"
showboat note verification/phase6_parent.md "Verify batch creation rejects unverified chapters."
showboat exec verification/phase6_parent.md bash "curl -s -X POST http://localhost:8000/api/training/create-batch -H 'Content-Type: application/json' -d '{\"profile_id\":1,\"chapter_id\":2}' -w '\nHTTP %{http_code}'"
showboat verify verification/phase6_parent.md
```

**PLAYWRIGHT -- agentic manual testing:**
- `e2e/tests/phase6_parent.spec.ts`:
  - Login as Raj (parent) -- verify ParentPanel renders with 3 tabs
  - Click "Chapters" tab -- verify 22 chapters listed with extraction status badges
  - Click "Extract" on Chapter 1 -- verify status changes to "extracting" then "review"
  - Click "Puzzle Review" tab -- verify board diagrams render alongside solution moves
  - Click "Approve" on a puzzle -- verify it moves to verified state
  - Click "Verify All" -- verify all puzzles in chapter marked as verified
  - Click "Graduations" tab -- verify pending graduations listed per child
  - Click "Approve Graduation" for Rishi -- verify batch status changes to "graduated"
  - Verify "Create Next Batch" button appears after graduation

### Phase 7: Polish

**RED -- write tests first:**
- `frontend/src/__tests__/Animations.test.jsx`:
  - Test confetti component renders on correct solve
  - Test XP popup appears with correct value
  - Test board orientation flips based on `turn` field
- `frontend/src/__tests__/SessionResume.test.jsx`:
  - Test session state saved to localStorage on puzzle solve
  - Test session state restored from localStorage on page refresh
  - Test stale session (different day) is discarded, not restored

**GREEN -- implement:**
- Kid-friendly visuals (large pieces, bright colors)
- Celebration animations (confetti, XP popups)
- Mobile-responsive layout (tablet use)
- Session resume via localStorage
- Run tests -- all green

**SHOWBOAT -- `verification/phase7_polish.md`:**
```
showboat init verification/phase7_polish.md "Phase 7: Polish Verification"
showboat note verification/phase7_polish.md "Verify all test suites pass, frontend builds, and full stack is healthy."
showboat exec verification/phase7_polish.md bash "cd backend && pytest -v"
showboat exec verification/phase7_polish.md bash "cd frontend && npm test -- --run"
showboat exec verification/phase7_polish.md bash "cd frontend && npm run build"
showboat note verification/phase7_polish.md "Verify production build output exists."
showboat exec verification/phase7_polish.md bash "ls -lh frontend/dist/index.html frontend/dist/assets/*.js | head -5"
showboat note verification/phase7_polish.md "Full stack smoke test."
showboat exec verification/phase7_polish.md bash "curl -s http://localhost:8000/ | python -m json.tool"
showboat exec verification/phase7_polish.md bash "curl -s http://localhost:5173/ | head -5"
showboat verify verification/phase7_polish.md
```

**PLAYWRIGHT -- agentic manual testing:**
- `e2e/tests/phase7_polish.spec.ts`:
  - Solve puzzle correctly -- verify confetti animation appears (canvas element or particle count)
  - Verify XP popup animates in with correct value and fades out
  - Solve puzzle with Black to move -- verify board oriented with black pieces at bottom
  - Solve puzzle with White to move -- verify board oriented with white pieces at bottom
  - Set viewport to 768x1024 (tablet) -- verify layout is responsive (no horizontal scroll, board fits)
  - Solve a puzzle, close browser, reopen -- verify session resumes at correct puzzle (localStorage)
  - Full end-to-end flow: ProfileSelect -> Dashboard -> Train 3 puzzles -> Results -> back to Dashboard -- screenshot at each step for visual regression baseline

---

## Test Infrastructure

### Four Test Layers

**1. Backend unit tests:** pytest + httpx (TestClient for FastAPI)
- In-memory SQLite for test isolation (each test gets fresh DB)
- Fixtures: `test_db`, `test_client`, `seeded_db` (with chapters/profiles/badges)
- Mock LLM responses for extraction tests (no real API calls in tests)

**2. Frontend unit tests:** Vitest + jsdom + @testing-library/react
- Mock api.js calls with vi.mock
- Mock useStockfish hook
- Test user interactions with fireEvent / userEvent

**3. Showboat verification docs:** Executable markdown (all phases)
- Each phase produces a `verification/phaseN_*.md` with `showboat exec` commands
- Commands hit real API endpoints, query real DB, run real test suites
- `showboat verify` re-runs all commands and confirms outputs match -- reproducible proof
- Serves as living documentation: anyone can read the .md to understand what the phase does and re-verify it
- Install: `pip install showboat` or `uvx showboat`

**4. Playwright agentic E2E tests:** Playwright + real browser (Phases 3-7)
- Tests run against live frontend + backend (both servers must be running)
- Full browser automation: navigate, click, drag-and-drop chess pieces, screenshot
- Agentic approach: Claude drives the browser via Playwright MCP or test scripts, verifying visual behavior that unit tests can't catch (board renders correctly, animations fire, layout is responsive)
- Test data seeded via API calls in `beforeEach` (create profiles, extract chapter, create batch)
- Screenshots captured at key steps for visual regression baselines

### Project Structure for Tests
```
~/projects/chess_intuition_trainer/
├── backend/tests/
│   ├── conftest.py              # pytest fixtures (test_db, test_client, seeded_db)
│   ├── test_models.py           # Phase 1
│   ├── test_database.py         # Phase 1
│   ├── test_seed.py             # Phase 1
│   ├── test_main.py             # Phase 1
│   ├── test_extraction.py       # Phase 2
│   ├── test_extraction_api.py   # Phase 2
│   ├── test_training.py         # Phase 3
│   ├── test_training_api.py     # Phase 3
│   ├── test_dashboard_api.py    # Phase 4
│   ├── test_gamification.py     # Phase 5
│   └── test_parent_api.py       # Phase 6
├── frontend/src/__tests__/
│   ├── TrainingSession.test.jsx # Phase 3
│   ├── Dashboard.test.jsx       # Phase 4
│   ├── ResultsScreen.test.jsx   # Phase 4
│   ├── BadgeDisplay.test.jsx    # Phase 5
│   ├── Leaderboard.test.jsx     # Phase 5
│   ├── ParentPanel.test.jsx     # Phase 6
│   ├── Animations.test.jsx      # Phase 7
│   └── SessionResume.test.jsx   # Phase 7
├── verification/                    # Showboat executable docs
│   ├── phase1_foundation.md
│   ├── phase2_extraction.md
│   ├── phase3_training.md
│   ├── phase4_dashboard.md
│   ├── phase5_gamification.md
│   ├── phase6_parent.md
│   └── phase7_polish.md
└── e2e/
    ├── playwright.config.ts     # Base URL, browser config, screenshot dir
    └── tests/
        ├── phase3_training.spec.ts
        ├── phase4_dashboard.spec.ts
        ├── phase5_gamification.spec.ts
        ├── phase6_parent.spec.ts
        └── phase7_polish.spec.ts
```

### Running Tests
```bash
# Backend unit tests
cd backend && pytest -v

# Frontend unit tests
cd frontend && npm test

# Showboat verification (re-verify all phases)
for f in verification/phase*.md; do showboat verify "$f"; done

# Playwright E2E (requires both servers running)
cd e2e && npx playwright test

# All four layers
cd backend && pytest -v && cd ../frontend && npm test && cd .. && for f in verification/phase*.md; do showboat verify "$f"; done && cd e2e && npx playwright test
```

---

## Verification Plan (integration, post-TDD)
1. **Extraction**: Extract Ch 1 (50 fork puzzles), verify FEN accuracy against PDF visually, confirm solution moves are legal via python-chess
2. **Training loop**: Create batch for Rishi, solve 5 puzzles, verify attempts recorded with correct times, complete circle, check stats
3. **Micro-cycles**: Complete 2 circles of a small batch, verify speed comparison works and graduation flag triggers at threshold
4. **Gamification**: Solve puzzles, verify XP calculation matches formula, check badge awarding
5. **Session cap**: Start session, verify timer counts down, verify no puzzles served after cap
6. **Parent flow**: Extract chapter -> review puzzles -> approve -> create batch -> kid solves -> ready to graduate -> parent approves -> next batch created
