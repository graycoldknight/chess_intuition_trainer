"""
Phase 1 RED: Test all 9 tables, foreign keys, and unique constraints.
"""

import pytest
from sqlalchemy import inspect
from models import (
    Profile, Chapter, Puzzle, Batch, Attempt, Session,
    PuzzleMastery, BadgeDefinition, EarnedBadge,
)


def test_all_nine_tables_created(test_engine):
    """All 9 tables exist in the database."""
    table_names = inspect(test_engine).get_table_names()
    expected = [
        "profiles", "chapters", "puzzles", "batches", "attempts",
        "sessions", "puzzle_mastery", "badge_definitions", "earned_badges",
    ]
    for table in expected:
        assert table in table_names, f"Missing table: {table}"


def test_create_profile(test_db):
    """Can create a profile and read it back."""
    p = Profile(name="TestKid", role="student", uscf_rating=1000)
    test_db.add(p)
    test_db.commit()
    result = test_db.query(Profile).filter_by(name="TestKid").first()
    assert result is not None
    assert result.role == "student"
    assert result.total_xp == 0
    assert result.current_streak == 0


def test_profile_unique_name(test_db):
    """Duplicate profile names are rejected."""
    test_db.add(Profile(name="Dup", role="student"))
    test_db.commit()
    test_db.add(Profile(name="Dup", role="parent"))
    with pytest.raises(Exception):
        test_db.commit()
    test_db.rollback()


def test_create_chapter(test_db):
    """Can create a chapter with all fields."""
    c = Chapter(id=1, title="Forks", section="TACTICAL ELEMENTS", start_page=13, end_page=30)
    test_db.add(c)
    test_db.commit()
    result = test_db.query(Chapter).get(1)
    assert result.title == "Forks"
    assert result.extraction_status == "pending"


def test_create_puzzle_with_chapter_fk(test_db):
    """Puzzle requires a valid chapter_id."""
    c = Chapter(id=1, title="Forks", section="TACTICAL ELEMENTS", start_page=13, end_page=30)
    test_db.add(c)
    test_db.commit()

    p = Puzzle(
        chapter_id=1, puzzle_number=1, fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        turn="w", solution_san="Nf3", solution_uci="g1f3",
    )
    test_db.add(p)
    test_db.commit()
    assert test_db.query(Puzzle).count() == 1


def test_puzzle_unique_chapter_number(test_db):
    """Duplicate chapter_id + puzzle_number is rejected."""
    c = Chapter(id=1, title="Forks", section="TACTICAL ELEMENTS", start_page=13, end_page=30)
    test_db.add(c)
    test_db.commit()

    test_db.add(Puzzle(chapter_id=1, puzzle_number=1, fen="fen1", turn="w", solution_san="Nf3", solution_uci="g1f3"))
    test_db.commit()
    test_db.add(Puzzle(chapter_id=1, puzzle_number=1, fen="fen2", turn="b", solution_san="Nf6", solution_uci="g8f6"))
    with pytest.raises(Exception):
        test_db.commit()
    test_db.rollback()


def test_puzzle_invalid_chapter_fk(test_db):
    """Puzzle with nonexistent chapter_id is rejected (FK constraint)."""
    p = Puzzle(chapter_id=999, puzzle_number=1, fen="fen", turn="w", solution_san="e4", solution_uci="e2e4")
    test_db.add(p)
    with pytest.raises(Exception):
        test_db.commit()
    test_db.rollback()


def test_create_batch(test_db):
    """Batch links to profile and chapter."""
    test_db.add(Profile(name="Kid", role="student"))
    test_db.add(Chapter(id=1, title="Forks", section="TACTICAL ELEMENTS", start_page=13, end_page=30))
    test_db.commit()

    kid = test_db.query(Profile).first()
    b = Batch(profile_id=kid.id, chapter_id=1, puzzle_ids=[1, 2, 3], total_puzzles=3)
    test_db.add(b)
    test_db.commit()
    assert test_db.query(Batch).first().status == "active"
    assert test_db.query(Batch).first().current_circle == 1


def test_create_attempt(test_db):
    """Attempt links to profile, puzzle, and batch."""
    test_db.add(Profile(name="Kid", role="student"))
    test_db.add(Chapter(id=1, title="Forks", section="TACTICAL ELEMENTS", start_page=13, end_page=30))
    test_db.commit()

    kid = test_db.query(Profile).first()
    test_db.add(Puzzle(chapter_id=1, puzzle_number=1, fen="fen", turn="w", solution_san="e4", solution_uci="e2e4"))
    test_db.add(Batch(profile_id=kid.id, chapter_id=1, puzzle_ids=[1], total_puzzles=1))
    test_db.commit()

    puzzle = test_db.query(Puzzle).first()
    batch = test_db.query(Batch).first()
    a = Attempt(profile_id=kid.id, puzzle_id=puzzle.id, batch_id=batch.id, circle=1, success=1, time_taken_ms=5000)
    test_db.add(a)
    test_db.commit()
    assert test_db.query(Attempt).count() == 1


def test_create_session(test_db):
    """Session links to profile with defaults."""
    test_db.add(Profile(name="Kid", role="student"))
    test_db.commit()
    kid = test_db.query(Profile).first()
    s = Session(profile_id=kid.id)
    test_db.add(s)
    test_db.commit()
    result = test_db.query(Session).first()
    assert result.puzzles_attempted == 0
    assert result.xp_earned == 0


def test_create_puzzle_mastery(test_db):
    """PuzzleMastery tracks per-profile per-puzzle stats."""
    test_db.add(Profile(name="Kid", role="student"))
    test_db.add(Chapter(id=1, title="Forks", section="TACTICAL ELEMENTS", start_page=13, end_page=30))
    test_db.commit()
    kid = test_db.query(Profile).first()
    test_db.add(Puzzle(chapter_id=1, puzzle_number=1, fen="fen", turn="w", solution_san="e4", solution_uci="e2e4"))
    test_db.commit()
    puzzle = test_db.query(Puzzle).first()

    pm = PuzzleMastery(profile_id=kid.id, puzzle_id=puzzle.id, total_attempts=1, total_correct=1)
    test_db.add(pm)
    test_db.commit()
    assert test_db.query(PuzzleMastery).first().ease_factor == 2.5


def test_puzzle_mastery_unique_constraint(test_db):
    """Duplicate profile_id + puzzle_id in puzzle_mastery is rejected."""
    test_db.add(Profile(name="Kid", role="student"))
    test_db.add(Chapter(id=1, title="Forks", section="TACTICAL ELEMENTS", start_page=13, end_page=30))
    test_db.commit()
    kid = test_db.query(Profile).first()
    test_db.add(Puzzle(chapter_id=1, puzzle_number=1, fen="fen", turn="w", solution_san="e4", solution_uci="e2e4"))
    test_db.commit()
    puzzle = test_db.query(Puzzle).first()

    test_db.add(PuzzleMastery(profile_id=kid.id, puzzle_id=puzzle.id))
    test_db.commit()
    test_db.add(PuzzleMastery(profile_id=kid.id, puzzle_id=puzzle.id))
    with pytest.raises(Exception):
        test_db.commit()
    test_db.rollback()


def test_badge_definitions_and_earned(test_db):
    """Badge definitions and earned badges work together."""
    test_db.add(Profile(name="Kid", role="student"))
    test_db.add(BadgeDefinition(key="fork_master", name="Fork Master", category="theme"))
    test_db.commit()

    kid = test_db.query(Profile).first()
    badge = test_db.query(BadgeDefinition).first()
    test_db.add(EarnedBadge(profile_id=kid.id, badge_id=badge.id))
    test_db.commit()
    assert test_db.query(EarnedBadge).count() == 1


def test_earned_badge_unique_constraint(test_db):
    """Same badge can't be earned twice by same profile."""
    test_db.add(Profile(name="Kid", role="student"))
    test_db.add(BadgeDefinition(key="fork_master", name="Fork Master", category="theme"))
    test_db.commit()

    kid = test_db.query(Profile).first()
    badge = test_db.query(BadgeDefinition).first()
    test_db.add(EarnedBadge(profile_id=kid.id, badge_id=badge.id))
    test_db.commit()
    test_db.add(EarnedBadge(profile_id=kid.id, badge_id=badge.id))
    with pytest.raises(Exception):
        test_db.commit()
    test_db.rollback()
