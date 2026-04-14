"""
Import Chapter 1 puzzles from chapter1_questions.json + chapter1_answers.json.

Usage:
    cd backend && python import_chapter1.py

Idempotent: skips puzzles that already exist (by chapter_id + puzzle_number).
All imported puzzles are marked verified=1 so they're immediately usable.
"""

import json
import os

# Resolve paths relative to repo root (one level up from backend/)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUESTIONS_PATH = os.path.join(ROOT, "chapter1_questions.json")
ANSWERS_PATH   = os.path.join(ROOT, "chapter1_answers.json")

from models import Puzzle

CHAPTER_ID = 1
MAX_PUZZLE_NUMBER = 1000  # exclude sentinel entries like 9999


def import_chapter1(db):
    """Import Chapter 1 puzzles from JSON files. Idempotent — skips existing puzzles."""
    with open(QUESTIONS_PATH) as f:
        questions = {q["puzzle_number"]: q for q in json.load(f) if q["puzzle_number"] < MAX_PUZZLE_NUMBER}
    with open(ANSWERS_PATH) as f:
        answers = {a["puzzle_number"]: a for a in json.load(f) if a["puzzle_number"] < MAX_PUZZLE_NUMBER}

    puzzle_numbers = sorted(set(questions) & set(answers))
    imported = 0
    for num in puzzle_numbers:
        existing = db.query(Puzzle).filter_by(chapter_id=CHAPTER_ID, puzzle_number=num).first()
        if existing:
            continue
        q = questions[num]
        a = answers[num]
        db.add(Puzzle(
            chapter_id=CHAPTER_ID,
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
        print(f"import_chapter1: imported {imported} puzzles")


if __name__ == "__main__":
    from database import SessionLocal, init_db
    from seed import seed_all
    init_db()
    db = SessionLocal()
    try:
        seed_all(db)
        import_chapter1(db)
    finally:
        db.close()
