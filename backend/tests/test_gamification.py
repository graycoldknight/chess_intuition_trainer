"""
Tests for backend/gamification.py -- XP, badges, leaderboard.
RED phase: written before implementation.
"""

import pytest
from models import Profile, Puzzle, Batch, Attempt, EarnedBadge, BadgeDefinition, Session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_puzzle(db, chapter_id=1, puzzle_number=1):
    p = Puzzle(
        chapter_id=chapter_id,
        puzzle_number=puzzle_number,
        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        turn="b",
        solution_san="e5",
        solution_uci="e7e5",
        verified=1,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def make_batch(db, profile_id=1, chapter_id=1, puzzle_ids=None, current_circle=1):
    if puzzle_ids is None:
        puzzle_ids = []
    b = Batch(
        profile_id=profile_id,
        chapter_id=chapter_id,
        puzzle_ids=puzzle_ids,
        total_puzzles=len(puzzle_ids),
        current_circle=current_circle,
        status="active",
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


# ---------------------------------------------------------------------------
# XP calculation
# ---------------------------------------------------------------------------

def test_xp_base_correct(seeded_db):
    from gamification import calculate_xp
    # Correct solve, slow time (>=30s), C1, 0-day streak
    xp = calculate_xp(time_ms=35_000, success=True, circle=1, streak=0)
    assert xp == 10  # base only, no speed bonus, no multipliers


def test_xp_base_wrong(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=35_000, success=False, circle=1, streak=0)
    assert xp == 2  # participation XP only


def test_xp_speed_bonus_under_5s(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=4_000, success=True, circle=1, streak=0)
    assert xp == 30  # (10 + 20) * 1.0 * 1.0


def test_xp_speed_bonus_under_10s(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=8_000, success=True, circle=1, streak=0)
    assert xp == 25  # (10 + 15) * 1.0 * 1.0


def test_xp_speed_bonus_under_15s(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=12_000, success=True, circle=1, streak=0)
    assert xp == 20  # (10 + 10) * 1.0 * 1.0


def test_xp_speed_bonus_under_30s(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=20_000, success=True, circle=1, streak=0)
    assert xp == 15  # (10 + 5) * 1.0 * 1.0


def test_xp_no_speed_bonus_wrong(seeded_db):
    """Speed bonus does NOT apply to wrong answers."""
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=4_000, success=False, circle=1, streak=0)
    assert xp == 2  # just participation XP


def test_xp_circle_multiplier_c2(seeded_db):
    from gamification import calculate_xp
    # Correct, slow (no speed bonus), C2, no streak
    xp = calculate_xp(time_ms=35_000, success=True, circle=2, streak=0)
    assert xp == int(10 * 1.1)  # floor(10 * 1.1) = 11


def test_xp_circle_multiplier_c3(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=35_000, success=True, circle=3, streak=0)
    assert xp == int(10 * 1.2)  # 12


def test_xp_circle_multiplier_c4(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=35_000, success=True, circle=4, streak=0)
    assert xp == int(10 * 1.3)  # 13


def test_xp_circle_multiplier_c5(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=35_000, success=True, circle=5, streak=0)
    assert xp == int(10 * 1.5)  # 15


def test_xp_streak_multiplier_3_days(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=35_000, success=True, circle=1, streak=3)
    assert xp == int(10 * 1.2)  # 12


def test_xp_streak_multiplier_7_days(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=35_000, success=True, circle=1, streak=7)
    assert xp == int(10 * 1.5)  # 15


def test_xp_streak_multiplier_14_days(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=35_000, success=True, circle=1, streak=14)
    assert xp == int(10 * 2.0)  # 20


def test_xp_streak_multiplier_30_days(seeded_db):
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=35_000, success=True, circle=1, streak=30)
    assert xp == int(10 * 3.0)  # 30


def test_xp_full_formula(seeded_db):
    """Correct in 4s, circle 3, 7-day streak = floor((10+20)*1.2*1.5) = 54"""
    from gamification import calculate_xp
    xp = calculate_xp(time_ms=4_000, success=True, circle=3, streak=7)
    assert xp == 54


# ---------------------------------------------------------------------------
# Badge awarding
# ---------------------------------------------------------------------------

def test_badge_fork_master_on_graduation(seeded_db):
    """'Fork Master' badge earned when Ch 1 batch is graduated."""
    from gamification import check_and_award_badges
    db = seeded_db
    # Graduate a batch for chapter 1, profile 1
    puzzle = make_puzzle(db)
    batch = make_batch(db, profile_id=1, chapter_id=1, puzzle_ids=[puzzle.id])
    batch.status = "graduated"
    db.commit()

    new_badges = check_and_award_badges(profile_id=1, db=db)
    badge_keys = [b.key for b in new_badges]
    assert "fork_master" in badge_keys


def test_badge_lightning_reflexes(seeded_db):
    """'Lightning Reflexes' badge earned when a puzzle is solved in <3s."""
    from gamification import check_and_award_badges
    db = seeded_db
    puzzle = make_puzzle(db)
    batch = make_batch(db, profile_id=1, chapter_id=1, puzzle_ids=[puzzle.id])
    # Record a <3s correct attempt
    db.add(Attempt(
        profile_id=1,
        puzzle_id=puzzle.id,
        batch_id=batch.id,
        circle=1,
        success=1,
        time_taken_ms=2_500,
        user_move="e7e5",
    ))
    db.commit()

    new_badges = check_and_award_badges(profile_id=1, db=db)
    badge_keys = [b.key for b in new_badges]
    assert "lightning_reflexes" in badge_keys


def test_badge_first_solve(seeded_db):
    """'First Solve' badge earned on first correct attempt."""
    from gamification import check_and_award_badges
    db = seeded_db
    puzzle = make_puzzle(db)
    batch = make_batch(db, profile_id=1, chapter_id=1, puzzle_ids=[puzzle.id])
    db.add(Attempt(
        profile_id=1,
        puzzle_id=puzzle.id,
        batch_id=batch.id,
        circle=1,
        success=1,
        time_taken_ms=8_000,
        user_move="e7e5",
    ))
    db.commit()

    new_badges = check_and_award_badges(profile_id=1, db=db)
    badge_keys = [b.key for b in new_badges]
    assert "first_solve" in badge_keys


def test_badge_not_double_awarded(seeded_db):
    """Earning the same badge twice is idempotent -- no duplicate rows."""
    from gamification import check_and_award_badges
    db = seeded_db
    puzzle = make_puzzle(db)
    batch = make_batch(db, profile_id=1, chapter_id=1, puzzle_ids=[puzzle.id])
    db.add(Attempt(
        profile_id=1,
        puzzle_id=puzzle.id,
        batch_id=batch.id,
        circle=1,
        success=1,
        time_taken_ms=2_500,
        user_move="e7e5",
    ))
    db.commit()

    # Award once
    check_and_award_badges(profile_id=1, db=db)
    count_before = db.query(EarnedBadge).filter_by(profile_id=1).count()

    # Award again -- should be idempotent
    check_and_award_badges(profile_id=1, db=db)
    count_after = db.query(EarnedBadge).filter_by(profile_id=1).count()

    assert count_before == count_after


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

def test_leaderboard_returns_both_kids(seeded_db):
    """Leaderboard includes Rishi and Raghav."""
    from gamification import get_leaderboard
    db = seeded_db
    board = get_leaderboard(db=db)
    names = [row["name"] for row in board]
    assert "Rishi" in names
    assert "Raghav" in names


def test_leaderboard_metrics(seeded_db):
    """Leaderboard rows include xp, streak, chapters_graduated fields."""
    from gamification import get_leaderboard
    db = seeded_db
    board = get_leaderboard(db=db)
    for row in board:
        assert "name" in row
        assert "total_xp" in row
        assert "current_streak" in row
        assert "chapters_graduated" in row


def test_leaderboard_excludes_parent(seeded_db):
    """Raj (parent role) should NOT appear in leaderboard."""
    from gamification import get_leaderboard
    db = seeded_db
    board = get_leaderboard(db=db)
    names = [row["name"] for row in board]
    assert "Raj" not in names


def test_leaderboard_xp_reflects_profile(seeded_db):
    """Leaderboard XP matches the profile's total_xp."""
    from gamification import get_leaderboard
    db = seeded_db
    # Give Rishi some XP
    rishi = db.query(Profile).filter_by(name="Rishi").first()
    rishi.total_xp = 150
    db.commit()

    board = get_leaderboard(db=db)
    rishi_row = next(r for r in board if r["name"] == "Rishi")
    assert rishi_row["total_xp"] == 150
