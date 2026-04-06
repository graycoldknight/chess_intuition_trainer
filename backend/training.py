"""
Core training loop for Chess Intuition Trainer -- Yoo Method state machine.

Key operations:
- create_batch: assign a set of verified puzzles to a profile
- get_next_puzzle: serve the next unsolved puzzle in the current circle
- record_attempt: record a solve (correct or wrong) and update mastery
- start_session / end_session: enforce the 60-minute daily cap
- approve_graduation: parent marks a ready_to_graduate batch as graduated
- get_training_state: full snapshot for the UI
"""

import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session as DBSession
from models import Batch, Attempt, Session, PuzzleMastery, Puzzle, Profile

SESSION_CAP_SECONDS = 60 * 60  # 60 minutes
GRADUATION_AVG_MS = 15_000      # 15 seconds
RANDOMIZED_FROM_CIRCLE = 6      # circles 6+ use independently shuffled puzzle order


# ---------------------------------------------------------------------------
# Batch management
# ---------------------------------------------------------------------------

def create_batch(profile_id: int, chapter_id: int, db: DBSession) -> Batch:
    """Create a new training batch from verified puzzles in a chapter."""
    puzzles = (
        db.query(Puzzle)
        .filter(Puzzle.chapter_id == chapter_id, Puzzle.verified == 1)
        .order_by(Puzzle.puzzle_number)
        .all()
    )
    if not puzzles:
        raise ValueError(f"No verified puzzles in chapter {chapter_id}")

    batch = Batch(
        profile_id=profile_id,
        chapter_id=chapter_id,
        puzzle_ids=[p.id for p in puzzles],
        total_puzzles=len(puzzles),
        current_circle=1,
        status="active",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def approve_graduation(batch_id: int, db: DBSession) -> Batch:
    """Parent approves graduation for a ready_to_graduate batch."""
    batch = db.query(Batch).get(batch_id)
    if not batch:
        return None
    batch.status = "graduated"
    db.commit()
    db.refresh(batch)
    return batch


# ---------------------------------------------------------------------------
# Puzzle serving
# ---------------------------------------------------------------------------

def get_next_puzzle(profile_id: int, db: DBSession):
    """Return the next puzzle to solve, or None if session cap hit or circle done."""
    # Session cap check
    session = _get_active_session(profile_id, db)
    if session and _is_over_cap(session):
        return None

    # Active batch
    batch = (
        db.query(Batch)
        .filter(Batch.profile_id == profile_id, Batch.status == "active")
        .first()
    )
    if not batch:
        return None

    # Find first puzzle not yet attempted in current circle
    attempted_ids = {
        a.puzzle_id
        for a in db.query(Attempt).filter(
            Attempt.profile_id == profile_id,
            Attempt.batch_id == batch.id,
            Attempt.circle == batch.current_circle,
        ).all()
    }

    # Use pre-generated shuffled order for circles >= RANDOMIZED_FROM_CIRCLE
    orders = batch.circle_puzzle_orders or {}
    puzzle_order = orders.get(str(batch.current_circle), batch.puzzle_ids)

    for puzzle_id in puzzle_order:
        if puzzle_id not in attempted_ids:
            return db.query(Puzzle).get(puzzle_id)

    return None  # All puzzles in this circle are done


# ---------------------------------------------------------------------------
# Attempt recording
# ---------------------------------------------------------------------------

def record_attempt(
    profile_id: int,
    puzzle_id: int,
    batch_id: int,
    circle: int,
    success: bool,
    time_taken_ms: int,
    user_move: str,
    db: DBSession,
) -> Attempt:
    """Record a solve attempt; update mastery and advance circle if complete."""
    now = datetime.utcnow()

    attempt = Attempt(
        profile_id=profile_id,
        puzzle_id=puzzle_id,
        batch_id=batch_id,
        circle=circle,
        success=1 if success else 0,
        time_taken_ms=time_taken_ms,
        user_move=user_move,
        attempted_at=now,
    )
    db.add(attempt)

    # Update active session counters
    session = _get_active_session(profile_id, db)
    if session:
        session.puzzles_attempted += 1
        if success:
            session.puzzles_correct += 1

    # Upsert puzzle mastery
    mastery = (
        db.query(PuzzleMastery)
        .filter(PuzzleMastery.profile_id == profile_id, PuzzleMastery.puzzle_id == puzzle_id)
        .first()
    )
    if mastery is None:
        mastery = PuzzleMastery(
            profile_id=profile_id,
            puzzle_id=puzzle_id,
            total_attempts=0,
            total_correct=0,
            total_wrong=0,
            wrong_moves=[],
            first_seen_at=now,
        )
        db.add(mastery)
        db.flush()

    mastery.total_attempts += 1
    mastery.last_seen_at = now
    mastery.last_time_ms = time_taken_ms

    if success:
        mastery.total_correct += 1
        if mastery.best_time_ms is None or time_taken_ms < mastery.best_time_ms:
            mastery.best_time_ms = time_taken_ms
    else:
        mastery.total_wrong += 1
        wrong_moves = list(mastery.wrong_moves or [])
        wrong_moves.append({"move": user_move, "at": now.isoformat(), "circle": circle})
        mastery.wrong_moves = wrong_moves

    db.commit()

    # Check if current circle is complete and advance
    batch = db.query(Batch).get(batch_id)
    if batch:
        _maybe_advance_circle(batch, profile_id, db)

    return attempt


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def start_session(profile_id: int, db: DBSession) -> Session:
    """Open a new training session."""
    session = Session(
        profile_id=profile_id,
        started_at=datetime.utcnow(),
        puzzles_attempted=0,
        puzzles_correct=0,
        xp_earned=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def end_session(session_id: int, db: DBSession) -> Session:
    """Close a session and update the profile's streak."""
    session = db.query(Session).get(session_id)
    if not session:
        return None

    now = datetime.utcnow()
    session.ended_at = now
    session.duration_seconds = int((now - session.started_at).total_seconds())

    # Update streak
    profile = db.query(Profile).get(session.profile_id)
    if profile:
        today = now.strftime("%Y-%m-%d")
        if profile.last_session_date != today:
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            if profile.last_session_date == yesterday:
                profile.current_streak = (profile.current_streak or 0) + 1
            else:
                profile.current_streak = 1
            if profile.current_streak > (profile.longest_streak or 0):
                profile.longest_streak = profile.current_streak
            profile.last_session_date = today

    db.commit()
    db.refresh(session)
    return session


# ---------------------------------------------------------------------------
# Training state
# ---------------------------------------------------------------------------

def get_training_state(profile_id: int, db: DBSession) -> dict:
    """Full training state snapshot for the UI."""
    batch = (
        db.query(Batch)
        .filter(
            Batch.profile_id == profile_id,
            Batch.status.in_(["active", "ready_to_graduate"]),
        )
        .first()
    )

    session = _get_active_session(profile_id, db)
    session_time_remaining = None
    if session:
        elapsed = (datetime.utcnow() - session.started_at).total_seconds()
        session_time_remaining = max(0.0, SESSION_CAP_SECONDS - elapsed)

    profile = db.query(Profile).get(profile_id)
    profile_xp = profile.total_xp or 0 if profile else 0

    if not batch:
        return {
            "has_active_batch": False,
            "total_xp": profile_xp,
            "session": _session_dict(session),
            "session_time_remaining_seconds": session_time_remaining,
        }

    # Per-circle stats
    circle_stats = {}
    for circle in range(1, batch.current_circle + 1):
        attempts = db.query(Attempt).filter(
            Attempt.profile_id == profile_id,
            Attempt.batch_id == batch.id,
            Attempt.circle == circle,
        ).all()
        if attempts:
            correct = [a for a in attempts if a.success == 1]
            circle_stats[circle] = {
                "total": len(attempts),
                "correct": len(correct),
                "avg_time_ms": int(sum(a.time_taken_ms for a in correct) / len(correct)) if correct else None,
            }

    return {
        "has_active_batch": True,
        "batch_id": batch.id,
        "chapter_id": batch.chapter_id,
        "current_circle": batch.current_circle,
        "total_puzzles": batch.total_puzzles,
        "status": batch.status,
        "circle_stats": circle_stats,
        "total_xp": profile_xp,
        "session": _session_dict(session),
        "session_time_remaining_seconds": session_time_remaining,
        "puzzle_ids": batch.puzzle_ids,
        "is_randomized_circle": batch.current_circle >= RANDOMIZED_FROM_CIRCLE,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_active_session(profile_id: int, db: DBSession):
    return (
        db.query(Session)
        .filter(Session.profile_id == profile_id, Session.ended_at == None)  # noqa: E711
        .order_by(Session.started_at.desc())
        .first()
    )


def _is_over_cap(session: Session) -> bool:
    elapsed = (datetime.utcnow() - session.started_at).total_seconds()
    return elapsed >= SESSION_CAP_SECONDS


def _maybe_advance_circle(batch: Batch, profile_id: int, db: DBSession):
    """Advance current_circle if all puzzles have been attempted; check graduation on circle 7+."""
    attempted_count = db.query(Attempt).filter(
        Attempt.profile_id == profile_id,
        Attempt.batch_id == batch.id,
        Attempt.circle == batch.current_circle,
    ).count()

    if attempted_count < batch.total_puzzles:
        return  # Circle not yet complete

    if batch.current_circle >= 7:
        # Check graduation: avg correct time on this circle
        correct_attempts = db.query(Attempt).filter(
            Attempt.profile_id == profile_id,
            Attempt.batch_id == batch.id,
            Attempt.circle == batch.current_circle,
            Attempt.success == 1,
        ).all()

        if correct_attempts:
            avg_ms = sum(a.time_taken_ms for a in correct_attempts) / len(correct_attempts)
        else:
            avg_ms = float("inf")

        if avg_ms < GRADUATION_AVG_MS:
            batch.status = "ready_to_graduate"
        else:
            # Allow extra circles; generate new shuffle
            batch.current_circle += 1
            _store_shuffle(batch)
    else:
        batch.current_circle += 1
        if batch.current_circle >= RANDOMIZED_FROM_CIRCLE:
            _store_shuffle(batch)

    db.commit()


def _store_shuffle(batch: Batch):
    """Generate and store a fresh shuffle for the new current_circle."""
    shuffled = list(batch.puzzle_ids)
    random.shuffle(shuffled)
    orders = dict(batch.circle_puzzle_orders or {})
    orders[str(batch.current_circle)] = shuffled
    batch.circle_puzzle_orders = orders


def _session_dict(session) -> dict | None:
    if session is None:
        return None
    return {
        "id": session.id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "puzzles_attempted": session.puzzles_attempted,
        "puzzles_correct": session.puzzles_correct,
    }
