"""
Test profile setup/teardown script.
Called from e2e/setup/global-setup.ts and global-teardown.ts.
Uses the same SQLAlchemy session as the backend so data is immediately visible to the API.

Usage:
  python test_setup.py create         — inserts Test profile (ID 99) + Chapter 1 batch (circle 2, stats seeded)
  python test_setup.py create_circle1 — minimal 1-puzzle batch at circle 1 (for circle-completion E2E test)
  python test_setup.py destroy        — removes all Test profile data
"""

import sys
import os
import re
from datetime import datetime
from pathlib import Path
from database import SessionLocal
from models import Attempt, Profile, Batch, Puzzle, Session as TrainingSession, PuzzleMastery, EarnedBadge

PROFILE_ID = 99
CHAPTER_ID = 1


# Synthetic mate-in-1 puzzle used by the single-move Playwright test.
# FEN: White Ka6, Rb4 vs Black Ka8 — Rb8# is the only move.
SYNTHETIC_PUZZLE_NUMBER = 9999
SYNTHETIC_FEN = "k7/8/K7/8/1R6/8/8/8 w - - 0 1"
SYNTHETIC_UCI = "b4b8"


def destroy(db):
    db.query(EarnedBadge).filter(EarnedBadge.profile_id == PROFILE_ID).delete()
    db.query(PuzzleMastery).filter(PuzzleMastery.profile_id == PROFILE_ID).delete()
    db.query(Attempt).filter(Attempt.profile_id == PROFILE_ID).delete()
    db.query(TrainingSession).filter(TrainingSession.profile_id == PROFILE_ID).delete()
    db.query(Batch).filter(Batch.profile_id == PROFILE_ID).delete()
    db.query(Profile).filter(Profile.id == PROFILE_ID).delete()
    # Remove synthetic test puzzle
    db.query(Puzzle).filter(
        Puzzle.chapter_id == CHAPTER_ID,
        Puzzle.puzzle_number == SYNTHETIC_PUZZLE_NUMBER,
    ).delete()
    db.commit()
    print(f"✔  Test profile ({PROFILE_ID}) destroyed")


def create(db):
    # Always start clean
    destroy(db)

    # Insert a synthetic mate-in-1 puzzle so the single-move Playwright test always has data.
    # puzzle_number 9999 is reserved for this test fixture.
    synthetic = db.query(Puzzle).filter(
        Puzzle.chapter_id == CHAPTER_ID,
        Puzzle.puzzle_number == SYNTHETIC_PUZZLE_NUMBER,
    ).first()
    if not synthetic:
        synthetic = Puzzle(
            chapter_id=CHAPTER_ID,
            puzzle_number=SYNTHETIC_PUZZLE_NUMBER,
            fen=SYNTHETIC_FEN,
            turn="w",
            solution_san="Rb8#",
            solution_uci=SYNTHETIC_UCI,
            solution_line="1. Rb8#",
            solution_uci_line=[SYNTHETIC_UCI],
            verified=1,
            extraction_confidence=1.0,
        )
        db.add(synthetic)
        db.flush()
        print(f"  ✔  Synthetic mate-in-1 puzzle inserted (puzzle_number={SYNTHETIC_PUZZLE_NUMBER})")

    # Query actual verified puzzle IDs from the DB — don't hardcode
    puzzle_ids = [
        p.id for p in db.query(Puzzle)
        .filter(Puzzle.chapter_id == CHAPTER_ID, Puzzle.verified == 1)
        .order_by(Puzzle.puzzle_number)
        .all()
        if p.puzzle_number != SYNTHETIC_PUZZLE_NUMBER  # keep it out of the main list
    ]
    if not puzzle_ids:
        print(f"  ⚠  No verified puzzles found for chapter {CHAPTER_ID} — batch will be empty")
        puzzle_ids = []

    # Prepend the synthetic puzzle so getNextPuzzle() returns it first.
    puzzle_ids = [synthetic.id] + puzzle_ids

    print(f"  Found {len(puzzle_ids) - 1} verified puzzles for chapter {CHAPTER_ID} (+ 1 synthetic)")

    profile = Profile(
        id=PROFILE_ID,
        name="Test",
        role="student",
        uscf_rating=1000,
        total_xp=0,
        current_streak=0,
        longest_streak=0,
    )
    db.add(profile)
    db.flush()

    batch = Batch(
        profile_id=PROFILE_ID,
        chapter_id=CHAPTER_ID,
        puzzle_ids=puzzle_ids,
        total_puzzles=len(puzzle_ids),
        current_circle=2,  # Circle 1 is "done" — gives the results screen real stats to show
        status="active",
    )
    db.add(batch)
    db.flush()

    # Seed circle 1 attempts so circle_stats['1'] is populated for the results screen
    for puzzle_id in puzzle_ids[:10]:
        db.add(Attempt(
            profile_id=PROFILE_ID,
            puzzle_id=puzzle_id,
            batch_id=batch.id,
            circle=1,
            success=1,
            time_taken_ms=8000,
            user_move="f3f6",
            attempted_at=datetime.utcnow(),
        ))
    db.flush()

    session = TrainingSession(
        profile_id=PROFILE_ID,
        started_at=datetime.utcnow(),
        puzzles_attempted=0,
        puzzles_correct=0,
        xp_earned=0,
    )
    db.add(session)
    db.commit()

    print(f"✔  Test profile ({PROFILE_ID}) created — batch {batch.id}, session {session.id}")

    # Populate solution_uci_line for chapter 1 puzzles using chapter1_answers.txt
    _import_chapter1_answers(db)


def _import_chapter1_answers(db):
    """Parse chapter1_answers.txt and populate solution_uci_line on puzzles."""
    answers_path = Path(__file__).resolve().parent.parent / "chapter1_answers.txt"
    if not answers_path.exists():
        print("  ⚠  chapter1_answers.txt not found — solution_uci_line will be empty")
        return

    try:
        from extraction import parse_solution_to_uci
    except ImportError:
        print("  ⚠  extraction module unavailable — skipping solution_uci_line import")
        return

    answer_map = {}
    for line in answers_path.read_text().strip().split("\n"):
        line = line.strip()
        m = re.match(r"^(\d+)\.\s*(.*)", line)
        if m:
            answer_map[int(m.group(1))] = m.group(2)

    puzzles = db.query(Puzzle).filter(Puzzle.chapter_id == CHAPTER_ID).order_by(Puzzle.puzzle_number).all()
    parsed = 0
    for p in puzzles:
        answer = answer_map.get(p.puzzle_number)
        if not answer:
            continue
        if p.solution_uci_line:
            # Already validated (e.g. manually corrected) — don't overwrite
            parsed += 1
            continue
        try:
            uci_line = parse_solution_to_uci(p.fen, answer)
            if uci_line:
                p.solution_uci_line = uci_line
                p.solution_line = answer
                parsed += 1
        except Exception as e:
            pass  # Skip puzzles where parsing fails

    db.commit()
    print(f"  ✔  Populated solution_uci_line for {parsed}/{len(puzzles)} chapter 1 puzzles")


def create_circle1(db):
    """Minimal setup for the circle-completion E2E test.

    Creates profile 99 with a batch at circle 1 containing ONLY the synthetic
    mate-in-1 puzzle (b4b8).  Solving that one puzzle completes circle 1 and
    should navigate the frontend to the results screen.
    """
    destroy(db)

    synthetic = db.query(Puzzle).filter(
        Puzzle.chapter_id == CHAPTER_ID,
        Puzzle.puzzle_number == SYNTHETIC_PUZZLE_NUMBER,
    ).first()
    if not synthetic:
        synthetic = Puzzle(
            chapter_id=CHAPTER_ID,
            puzzle_number=SYNTHETIC_PUZZLE_NUMBER,
            fen=SYNTHETIC_FEN,
            turn="w",
            solution_san="Rb8#",
            solution_uci=SYNTHETIC_UCI,
            solution_line="1. Rb8#",
            solution_uci_line=[SYNTHETIC_UCI],
            verified=1,
            extraction_confidence=1.0,
        )
        db.add(synthetic)
        db.flush()

    profile = Profile(
        id=PROFILE_ID,
        name="Test",
        role="student",
        uscf_rating=1000,
        total_xp=0,
        current_streak=0,
        longest_streak=0,
    )
    db.add(profile)
    db.flush()

    batch = Batch(
        profile_id=PROFILE_ID,
        chapter_id=CHAPTER_ID,
        puzzle_ids=[synthetic.id],
        total_puzzles=1,
        current_circle=1,
        status="active",
    )
    db.add(batch)
    db.flush()

    session = TrainingSession(
        profile_id=PROFILE_ID,
        started_at=datetime.utcnow(),
        puzzles_attempted=0,
        puzzles_correct=0,
        xp_earned=0,
    )
    db.add(session)
    db.commit()
    print(f"✔  Test profile ({PROFILE_ID}) created for circle-completion test — batch {batch.id}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "create"
    db = SessionLocal()
    try:
        if cmd == "destroy":
            destroy(db)
        elif cmd == "create_circle1":
            create_circle1(db)
        else:
            create(db)
    finally:
        db.close()
