# Phase 2.1: JSON Import Workflow Test Coverage

## Context

Commit `983045b` replaced the PDF extraction pipeline with a JSON-based import workflow (`import_puzzles.py`, 90 lines). This module is called at server startup to auto-import chapter puzzles from `chapterN_questions.json` + `chapterN_answers.json` files. The old `/api/extract-chapter` endpoint now returns 501. Despite being foundational infrastructure, this module has zero automated tests.

**Key decisions:**
- Test `import_chapter()` directly using `seeded_db` fixture + temp JSON files via `monkeypatch` on `ROOT`
- Test the 501 API response via `test_client`
- No Playwright E2E needed -- this is a backend-only import pipeline with no user-facing UI

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/tests/test_import_puzzles.py` | New file: unit tests for `import_puzzles.import_chapter()` |
| `backend/tests/test_training_api.py` | Add test for 501 response on `/api/extract-chapter` |

---

## Implementation

### `backend/tests/test_import_puzzles.py`

New test file exercising `import_puzzles.import_chapter()`:

```python
"""
Tests for backend/import_puzzles.py -- JSON puzzle import workflow.
"""

import json
import os
import pytest
from models import Puzzle, Chapter


def write_json_files(tmp_path, chapter_id, questions, answers):
    q_path = os.path.join(str(tmp_path), f"chapter{chapter_id}_questions.json")
    a_path = os.path.join(str(tmp_path), f"chapter{chapter_id}_answers.json")
    with open(q_path, 'w') as f:
        json.dump(questions, f)
    with open(a_path, 'w') as f:
        json.dump(answers, f)


SAMPLE_QUESTIONS = [
    {"puzzle_number": 1, "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1", "turn": "b"},
    {"puzzle_number": 2, "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", "turn": "w"},
]

SAMPLE_ANSWERS = [
    {"puzzle_number": 1, "solution_san": "e5", "solution_uci": "e7e5", "solution_line": "1...e5", "solution_uci_line": ["e7e5"]},
    {"puzzle_number": 2, "solution_san": "Nf3", "solution_uci": "g1f3", "solution_line": "2. Nf3", "solution_uci_line": ["g1f3"]},
]


def test_import_chapter_creates_puzzles(seeded_db, tmp_path, monkeypatch):
    write_json_files(tmp_path, 1, SAMPLE_QUESTIONS, SAMPLE_ANSWERS)
    import import_puzzles
    monkeypatch.setattr(import_puzzles, 'ROOT', str(tmp_path))

    count = import_puzzles.import_chapter(chapter_id=1, db=seeded_db)

    assert count == 2
    puzzles = seeded_db.query(Puzzle).filter_by(chapter_id=1).order_by(Puzzle.puzzle_number).all()
    assert len(puzzles) == 2
    assert puzzles[0].fen == SAMPLE_QUESTIONS[0]["fen"]
    assert puzzles[0].solution_san == "e5"
    assert puzzles[0].solution_uci == "e7e5"
    assert puzzles[0].verified == 1


def test_import_chapter_idempotent(seeded_db, tmp_path, monkeypatch):
    write_json_files(tmp_path, 1, SAMPLE_QUESTIONS, SAMPLE_ANSWERS)
    import import_puzzles
    monkeypatch.setattr(import_puzzles, 'ROOT', str(tmp_path))

    count1 = import_puzzles.import_chapter(chapter_id=1, db=seeded_db)
    count2 = import_puzzles.import_chapter(chapter_id=1, db=seeded_db)

    assert count1 == 2
    assert count2 == 0
    assert seeded_db.query(Puzzle).filter_by(chapter_id=1).count() == 2


def test_import_chapter_missing_files_returns_zero(seeded_db, tmp_path, monkeypatch):
    import import_puzzles
    monkeypatch.setattr(import_puzzles, 'ROOT', str(tmp_path))

    count = import_puzzles.import_chapter(chapter_id=99, db=seeded_db)
    assert count == 0


def test_import_chapter_only_imports_matched_puzzles(seeded_db, tmp_path, monkeypatch):
    """Only puzzles present in BOTH questions and answers should be imported."""
    questions = SAMPLE_QUESTIONS + [
        {"puzzle_number": 3, "fen": "test_fen", "turn": "w"},  # no answer
    ]
    write_json_files(tmp_path, 1, questions, SAMPLE_ANSWERS)
    import import_puzzles
    monkeypatch.setattr(import_puzzles, 'ROOT', str(tmp_path))

    count = import_puzzles.import_chapter(chapter_id=1, db=seeded_db)
    assert count == 2  # puzzle 3 skipped
    nums = [p.puzzle_number for p in seeded_db.query(Puzzle).filter_by(chapter_id=1).all()]
    assert 3 not in nums


def test_import_chapter_excludes_sentinel_puzzles(seeded_db, tmp_path, monkeypatch):
    """Puzzle numbers >= MAX_PUZZLE_NUMBER (1000) should be excluded."""
    questions = SAMPLE_QUESTIONS[:1] + [
        {"puzzle_number": 9999, "fen": "sentinel", "turn": "w"},
    ]
    answers = SAMPLE_ANSWERS[:1] + [
        {"puzzle_number": 9999, "solution_san": "a1", "solution_uci": "a1a1"},
    ]
    write_json_files(tmp_path, 1, questions, answers)
    import import_puzzles
    monkeypatch.setattr(import_puzzles, 'ROOT', str(tmp_path))

    count = import_puzzles.import_chapter(chapter_id=1, db=seeded_db)
    assert count == 1


def test_import_chapter_updates_chapter_status(seeded_db, tmp_path, monkeypatch):
    write_json_files(tmp_path, 1, SAMPLE_QUESTIONS, SAMPLE_ANSWERS)
    import import_puzzles
    monkeypatch.setattr(import_puzzles, 'ROOT', str(tmp_path))

    import_puzzles.import_chapter(chapter_id=1, db=seeded_db)

    chapter = seeded_db.query(Chapter).filter_by(id=1).first()
    assert chapter.extraction_status == "verified"
    assert chapter.puzzle_count == 2


def test_import_chapter_stores_solution_uci_line(seeded_db, tmp_path, monkeypatch):
    write_json_files(tmp_path, 1, SAMPLE_QUESTIONS, SAMPLE_ANSWERS)
    import import_puzzles
    monkeypatch.setattr(import_puzzles, 'ROOT', str(tmp_path))

    import_puzzles.import_chapter(chapter_id=1, db=seeded_db)

    puzzle = seeded_db.query(Puzzle).filter_by(chapter_id=1, puzzle_number=1).first()
    assert puzzle.solution_uci_line == ["e7e5"]
    assert puzzle.solution_line == "1...e5"
```

### `backend/tests/test_training_api.py`

Add at end of file:

```python
# ---------------------------------------------------------------------------
# POST /api/extract-chapter/{chapter_id} -- 501 (disabled)
# ---------------------------------------------------------------------------

def test_extract_chapter_returns_501(test_client):
    resp = test_client.post("/api/extract-chapter/1")
    assert resp.status_code == 501
```

---

## Execution Workflow

### RED -- write tests first

```bash
cd backend && pytest tests/test_import_puzzles.py -v
cd backend && pytest tests/test_training_api.py -v -k "extract_chapter_returns_501"
```

Since the implementation already exists, tests should be **GREEN** immediately. Any failure reveals a bug in the existing code.

### GREEN -- verify all pass

```bash
cd backend && pytest -v
```

All tests should be **GREEN**.

### SHOWBOAT -- `verification/phase2_json_import.md`

```
showboat init verification/phase2_json_import.md "Phase 2.1: JSON Import Workflow Verification"
showboat note verification/phase2_json_import.md "Verify import_puzzles.py creates puzzles from JSON, is idempotent, handles edge cases"
showboat exec verification/phase2_json_import.md bash "cd backend && pytest tests/test_import_puzzles.py -v"
showboat exec verification/phase2_json_import.md bash "cd backend && pytest tests/test_training_api.py -v -k 'extract_chapter_returns_501'"
showboat exec verification/phase2_json_import.md bash "cd backend && pytest -v"
showboat note verification/phase2_json_import.md "Verify /api/extract-chapter returns 501"
showboat exec verification/phase2_json_import.md bash "curl -s -X POST http://localhost:8000/api/extract-chapter/1 -w '\n%{http_code}' | tail -1"
showboat verify verification/phase2_json_import.md
```

### PLAYWRIGHT

No Playwright E2E needed -- `import_puzzles.py` is a backend-only module with no user-facing UI. The import runs at server startup and is not triggered by the frontend.
