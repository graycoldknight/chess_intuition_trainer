"""
Import puzzles from chapterN_questions.json + chapterN_answers.json for any chapter.

Usage (standalone):
    cd backend && python import_puzzles.py          # imports all available chapters
    cd backend && python import_puzzles.py 2        # imports chapter 2 only

Called automatically at server startup via main.py.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_PUZZLE_NUMBER = 1000  # exclude sentinel entries like 9999


def import_chapter(chapter_id: int, db) -> int:
    """Import puzzles for one chapter from JSON files. Idempotent — skips existing puzzles.
    Returns number of newly imported puzzles."""
    from models import Puzzle, Chapter

    q_path = os.path.join(ROOT, f"chapter{chapter_id}_questions.json")
    a_path = os.path.join(ROOT, f"chapter{chapter_id}_answers.json")
    if not os.path.exists(q_path) or not os.path.exists(a_path):
        return 0

    with open(q_path) as f:
        questions = {q["puzzle_number"]: q for q in json.load(f) if q["puzzle_number"] < MAX_PUZZLE_NUMBER}
    with open(a_path) as f:
        answers = {a["puzzle_number"]: a for a in json.load(f) if a["puzzle_number"] < MAX_PUZZLE_NUMBER}

    puzzle_numbers = sorted(set(questions) & set(answers))
    imported = 0
    for num in puzzle_numbers:
        existing = db.query(Puzzle).filter_by(chapter_id=chapter_id, puzzle_number=num).first()
        if existing:
            continue
        q = questions[num]
        a = answers[num]
        db.add(Puzzle(
            chapter_id=chapter_id,
            puzzle_number=num,
            fen=q["fen"],
            turn=q["turn"],
            solution_san=a["solution_san"],
            solution_uci=a["solution_uci"],
            solution_uci_line=a.get("solution_uci_line"),
            solution_line=a.get("solution_line"),
            verified=1,
            extraction_confidence=1.0,
        ))
        imported += 1

    if imported:
        db.commit()
        chapter = db.query(Chapter).filter_by(id=chapter_id).first()
        if chapter:
            chapter.extraction_status = "verified"
            chapter.puzzle_count = db.query(Puzzle).filter_by(chapter_id=chapter_id).count()
            db.commit()

    return imported


def import_all_available_chapters(db):
    """Import all chapters that have JSON files in the repo root."""
    for chapter_id in range(1, 23):
        n = import_chapter(chapter_id, db)
        if n:
            print(f"import_puzzles: chapter {chapter_id} — imported {n} puzzles")


if __name__ == "__main__":
    import sys
    from database import SessionLocal, init_db
    from seed import seed_all

    init_db()
    db = SessionLocal()
    try:
        seed_all(db)
        if len(sys.argv) > 1:
            chapter_id = int(sys.argv[1])
            n = import_chapter(chapter_id, db)
            print(f"Chapter {chapter_id}: imported {n} puzzles")
        else:
            import_all_available_chapters(db)
    finally:
        db.close()
