"""
Tests for backend/training.py -- Yoo Method state machine.
All tests use in-memory SQLite via the conftest fixtures.
"""

import pytest
from datetime import datetime, timedelta
from models import Puzzle, Batch, Attempt, Session, PuzzleMastery, Profile
import training


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_puzzle(db, chapter_id=1, puzzle_number=1, verified=1):
    p = Puzzle(
        chapter_id=chapter_id,
        puzzle_number=puzzle_number,
        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        turn="b",
        solution_san="e5",
        solution_uci="e7e5",
        verified=verified,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def make_puzzles(db, chapter_id=1, count=3):
    puzzles = []
    for i in range(1, count + 1):
        puzzles.append(make_puzzle(db, chapter_id=chapter_id, puzzle_number=i))
    return puzzles


def record_all_puzzles_in_circle(db, batch, profile_id, circle, time_ms=8000, success=True):
    """Helper: record a correct attempt for every puzzle in the batch's circle."""
    for pid in batch.puzzle_ids:
        training.record_attempt(
            profile_id=profile_id,
            puzzle_id=pid,
            batch_id=batch.id,
            circle=circle,
            success=success,
            time_taken_ms=time_ms,
            user_move="e7e5",
            db=db,
        )
        db.refresh(batch)


# ---------------------------------------------------------------------------
# create_batch
# ---------------------------------------------------------------------------

def test_create_batch_uses_verified_puzzles_only(seeded_db):
    db = seeded_db
    # 2 verified, 1 unverified
    p1 = make_puzzle(db, puzzle_number=1, verified=1)
    p2 = make_puzzle(db, puzzle_number=2, verified=1)
    p3 = make_puzzle(db, puzzle_number=3, verified=0)

    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    assert batch.id is not None
    assert batch.profile_id == 1
    assert batch.chapter_id == 1
    assert batch.total_puzzles == 2
    assert p1.id in batch.puzzle_ids
    assert p2.id in batch.puzzle_ids
    assert p3.id not in batch.puzzle_ids
    assert batch.current_circle == 1
    assert batch.status == "active"


def test_create_batch_raises_if_no_verified_puzzles(seeded_db):
    db = seeded_db
    make_puzzle(db, puzzle_number=1, verified=0)

    with pytest.raises(ValueError):
        training.create_batch(profile_id=1, chapter_id=1, db=db)


# ---------------------------------------------------------------------------
# get_next_puzzle
# ---------------------------------------------------------------------------

def test_get_next_puzzle_returns_first_puzzle(seeded_db):
    db = seeded_db
    puzzles = make_puzzles(db, count=3)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    puzzle = training.get_next_puzzle(profile_id=1, db=db)

    assert puzzle is not None
    assert puzzle.id == puzzles[0].id


def test_get_next_puzzle_skips_attempted(seeded_db):
    db = seeded_db
    puzzles = make_puzzles(db, count=3)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    # Record attempt for first puzzle
    training.record_attempt(
        profile_id=1,
        puzzle_id=puzzles[0].id,
        batch_id=batch.id,
        circle=1,
        success=True,
        time_taken_ms=5000,
        user_move="e7e5",
        db=db,
    )

    puzzle = training.get_next_puzzle(profile_id=1, db=db)
    assert puzzle.id == puzzles[1].id


def test_get_next_puzzle_returns_none_when_circle_complete(seeded_db):
    db = seeded_db
    puzzles = make_puzzles(db, count=2)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    # Attempt all puzzles in circle 1 -- this also advances circle
    record_all_puzzles_in_circle(db, batch, profile_id=1, circle=1)
    db.refresh(batch)

    # Batch should now be on circle 2, next puzzle is the first one again
    assert batch.current_circle == 2
    puzzle = training.get_next_puzzle(profile_id=1, db=db)
    # Still has puzzles -- in circle 2
    assert puzzle is not None
    assert puzzle.id == puzzles[0].id


def test_get_next_puzzle_returns_none_when_no_active_batch(seeded_db):
    db = seeded_db
    puzzle = training.get_next_puzzle(profile_id=1, db=db)
    assert puzzle is None


# ---------------------------------------------------------------------------
# record_attempt -- correct
# ---------------------------------------------------------------------------

def test_record_attempt_correct_creates_attempt(seeded_db):
    db = seeded_db
    p = make_puzzle(db)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    attempt = training.record_attempt(
        profile_id=1,
        puzzle_id=p.id,
        batch_id=batch.id,
        circle=1,
        success=True,
        time_taken_ms=7500,
        user_move="e7e5",
        db=db,
    )

    assert attempt.id is not None
    assert attempt.success == 1
    assert attempt.time_taken_ms == 7500
    assert attempt.user_move == "e7e5"
    assert attempt.circle == 1


def test_record_attempt_creates_puzzle_mastery(seeded_db):
    db = seeded_db
    p = make_puzzle(db)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    training.record_attempt(
        profile_id=1, puzzle_id=p.id, batch_id=batch.id,
        circle=1, success=True, time_taken_ms=7500, user_move="e7e5", db=db,
    )

    mastery = db.query(PuzzleMastery).filter_by(profile_id=1, puzzle_id=p.id).first()
    assert mastery is not None
    assert mastery.total_attempts == 1
    assert mastery.total_correct == 1
    assert mastery.total_wrong == 0
    assert mastery.best_time_ms == 7500
    assert mastery.last_time_ms == 7500
    assert mastery.first_seen_at is not None
    assert mastery.last_seen_at is not None


def test_record_attempt_updates_best_time(seeded_db):
    db = seeded_db
    p = make_puzzle(db)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    training.record_attempt(
        profile_id=1, puzzle_id=p.id, batch_id=batch.id,
        circle=1, success=True, time_taken_ms=10000, user_move="e7e5", db=db,
    )
    # Second attempt faster
    training.record_attempt(
        profile_id=1, puzzle_id=p.id, batch_id=batch.id,
        circle=2, success=True, time_taken_ms=4000, user_move="e7e5", db=db,
    )

    mastery = db.query(PuzzleMastery).filter_by(profile_id=1, puzzle_id=p.id).first()
    assert mastery.best_time_ms == 4000
    assert mastery.total_attempts == 2
    assert mastery.total_correct == 2


# ---------------------------------------------------------------------------
# record_attempt -- wrong
# ---------------------------------------------------------------------------

def test_record_attempt_wrong_appends_to_wrong_moves(seeded_db):
    db = seeded_db
    p = make_puzzle(db)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    training.record_attempt(
        profile_id=1, puzzle_id=p.id, batch_id=batch.id,
        circle=1, success=False, time_taken_ms=5000, user_move="d7d5", db=db,
    )

    mastery = db.query(PuzzleMastery).filter_by(profile_id=1, puzzle_id=p.id).first()
    assert mastery.total_wrong == 1
    assert mastery.total_correct == 0
    assert len(mastery.wrong_moves) == 1
    assert mastery.wrong_moves[0]["move"] == "d7d5"
    assert mastery.wrong_moves[0]["circle"] == 1


def test_wrong_moves_accumulates_across_circles(seeded_db):
    db = seeded_db
    p = make_puzzle(db)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    training.record_attempt(
        profile_id=1, puzzle_id=p.id, batch_id=batch.id,
        circle=1, success=False, time_taken_ms=5000, user_move="d7d5", db=db,
    )
    training.record_attempt(
        profile_id=1, puzzle_id=p.id, batch_id=batch.id,
        circle=3, success=False, time_taken_ms=6000, user_move="c7c5", db=db,
    )

    mastery = db.query(PuzzleMastery).filter_by(profile_id=1, puzzle_id=p.id).first()
    assert len(mastery.wrong_moves) == 2
    circles = {wm["circle"] for wm in mastery.wrong_moves}
    assert circles == {1, 3}


# ---------------------------------------------------------------------------
# Circle auto-advance
# ---------------------------------------------------------------------------

def test_circle_advances_after_all_puzzles_attempted(seeded_db):
    db = seeded_db
    puzzles = make_puzzles(db, count=2)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)
    assert batch.current_circle == 1

    record_all_puzzles_in_circle(db, batch, profile_id=1, circle=1)
    db.refresh(batch)

    assert batch.current_circle == 2


def test_puzzles_served_in_same_order_across_circles(seeded_db):
    db = seeded_db
    puzzles = make_puzzles(db, count=3)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    # Circle 1 order
    circle1_order = []
    for _ in range(3):
        p = training.get_next_puzzle(profile_id=1, db=db)
        circle1_order.append(p.id)
        training.record_attempt(
            profile_id=1, puzzle_id=p.id, batch_id=batch.id,
            circle=1, success=True, time_taken_ms=5000, user_move="e7e5", db=db,
        )
        db.refresh(batch)

    # Circle 2 order
    circle2_order = []
    for _ in range(3):
        p = training.get_next_puzzle(profile_id=1, db=db)
        circle2_order.append(p.id)
        training.record_attempt(
            profile_id=1, puzzle_id=p.id, batch_id=batch.id,
            circle=2, success=True, time_taken_ms=5000, user_move="e7e5", db=db,
        )
        db.refresh(batch)

    assert circle1_order == circle2_order


# ---------------------------------------------------------------------------
# Graduation
# ---------------------------------------------------------------------------

def test_graduation_ready_when_avg_time_under_15s(seeded_db):
    db = seeded_db
    puzzles = make_puzzles(db, count=2)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    # Complete circles 1-4
    for circle in range(1, 5):
        db.refresh(batch)
        record_all_puzzles_in_circle(db, batch, profile_id=1, circle=circle)

    db.refresh(batch)
    assert batch.current_circle == 5

    # Complete circle 5 with fast times (avg < 15s = 15000ms)
    record_all_puzzles_in_circle(db, batch, profile_id=1, circle=5, time_ms=8000)

    db.refresh(batch)
    assert batch.status == "ready_to_graduate"


def test_graduation_not_ready_when_avg_time_over_15s(seeded_db):
    db = seeded_db
    puzzles = make_puzzles(db, count=2)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    # Complete circles 1-4
    for circle in range(1, 5):
        db.refresh(batch)
        record_all_puzzles_in_circle(db, batch, profile_id=1, circle=circle)

    db.refresh(batch)
    assert batch.current_circle == 5

    # Complete circle 5 with slow times (avg > 15s)
    record_all_puzzles_in_circle(db, batch, profile_id=1, circle=5, time_ms=20000)

    db.refresh(batch)
    assert batch.status == "active"
    assert batch.current_circle == 6  # allows extra circles


def test_approve_graduation(seeded_db):
    db = seeded_db
    puzzles = make_puzzles(db, count=1)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)
    batch.status = "ready_to_graduate"
    db.commit()

    updated = training.approve_graduation(batch_id=batch.id, db=db)

    assert updated.status == "graduated"


# ---------------------------------------------------------------------------
# Session cap
# ---------------------------------------------------------------------------

def test_start_session_creates_record(seeded_db):
    db = seeded_db
    session = training.start_session(profile_id=1, db=db)

    assert session.id is not None
    assert session.profile_id == 1
    assert session.started_at is not None
    assert session.ended_at is None


def test_get_next_puzzle_returns_none_after_60_min(seeded_db):
    db = seeded_db
    puzzles = make_puzzles(db, count=2)
    training.create_batch(profile_id=1, chapter_id=1, db=db)

    # Create a session that started 61 minutes ago
    old_session = Session(
        profile_id=1,
        started_at=datetime.utcnow() - timedelta(minutes=61),
        puzzles_attempted=0,
        puzzles_correct=0,
        xp_earned=0,
    )
    db.add(old_session)
    db.commit()

    puzzle = training.get_next_puzzle(profile_id=1, db=db)
    assert puzzle is None


def test_get_next_puzzle_works_within_60_min(seeded_db):
    db = seeded_db
    puzzles = make_puzzles(db, count=2)
    training.create_batch(profile_id=1, chapter_id=1, db=db)

    # Create a session that started 30 minutes ago
    session = Session(
        profile_id=1,
        started_at=datetime.utcnow() - timedelta(minutes=30),
        puzzles_attempted=0,
        puzzles_correct=0,
        xp_earned=0,
    )
    db.add(session)
    db.commit()

    puzzle = training.get_next_puzzle(profile_id=1, db=db)
    assert puzzle is not None


# ---------------------------------------------------------------------------
# get_training_state
# ---------------------------------------------------------------------------

def test_get_training_state_no_batch(seeded_db):
    db = seeded_db
    state = training.get_training_state(profile_id=1, db=db)

    assert state["has_active_batch"] is False


def test_get_training_state_with_active_batch(seeded_db):
    db = seeded_db
    make_puzzles(db, count=3)
    batch = training.create_batch(profile_id=1, chapter_id=1, db=db)

    state = training.get_training_state(profile_id=1, db=db)

    assert state["has_active_batch"] is True
    assert state["batch_id"] == batch.id
    assert state["current_circle"] == 1
    assert state["total_puzzles"] == 3
    assert state["status"] == "active"
