"""
Gamification for Chess Intuition Trainer.

XP formula:
  base = 10 (correct) or 2 (wrong/participation)
  speed_bonus (correct only): <5s +20, <10s +15, <15s +10, <30s +5, >=30s +0
  circle_multiplier: C1=1.0, C2=1.1, C3=1.2, C4=1.3, C5=1.5 (C6+= 1.5 cap)
  streak_multiplier: 3-6d=1.2, 7-13d=1.5, 14-29d=2.0, 30+d=3.0, <3d=1.0
  xp = floor((base + speed_bonus) * circle_mult * streak_mult)

Badge checking:
  check_and_award_badges(profile_id, db) -> list of newly-awarded BadgeDefinition rows

Leaderboard:
  get_leaderboard(db) -> list of dicts for student profiles
"""

import math
from sqlalchemy.orm import Session as DBSession
from models import Profile, Attempt, Batch, EarnedBadge, BadgeDefinition


# ---------------------------------------------------------------------------
# XP calculation
# ---------------------------------------------------------------------------

_CIRCLE_MULTIPLIERS = {1: 1.0, 2: 1.1, 3: 1.2, 4: 1.3, 5: 1.5}


def _circle_multiplier(circle: int) -> float:
    return _CIRCLE_MULTIPLIERS.get(circle, 1.5)  # cap at C5 rate for extra circles


def _streak_multiplier(streak: int) -> float:
    if streak >= 30:
        return 3.0
    if streak >= 14:
        return 2.0
    if streak >= 7:
        return 1.5
    if streak >= 3:
        return 1.2
    return 1.0


def _speed_bonus(time_ms: int) -> int:
    if time_ms < 5_000:
        return 20
    if time_ms < 10_000:
        return 15
    if time_ms < 15_000:
        return 10
    if time_ms < 30_000:
        return 5
    return 0


def calculate_xp(time_ms: int, success: bool, circle: int, streak: int) -> int:
    """Compute XP earned for a single attempt."""
    if success:
        base = 10 + _speed_bonus(time_ms)
    else:
        return 2  # participation XP, no multipliers

    return math.floor(base * _circle_multiplier(circle) * _streak_multiplier(streak))


# ---------------------------------------------------------------------------
# Badge awarding
# ---------------------------------------------------------------------------

# Mapping from chapter_id to badge key for theme mastery badges
_CHAPTER_BADGE_KEYS = {
    1: "fork_master",
    2: "pin_expert",
    3: "deflection_ace",
    4: "discovery_pro",
    5: "guard_remover",
    6: "promotion_king",
    7: "overload_master",
    8: "xray_vision",
    9: "trapper",
    10: "zugzwang_wizard",
    11: "perpetual_artist",
    12: "stalemate_savior",
    13: "fortress_builder",
    14: "back_rank_assassin",
    15: "knight_bishop_master",
    16: "heavy_hitter",
    17: "minor_piece_maestro",
    18: "double_check_destroyer",
    19: "two_move_tactician",
    20: "three_move_tactician",
    21: "complex_solver",
    22: "champion_tactician",
}


def _award_badge(profile_id: int, badge_key: str, db: DBSession):
    """Award a badge by key if not already earned. Returns BadgeDefinition or None."""
    badge_def = db.query(BadgeDefinition).filter_by(key=badge_key).first()
    if not badge_def:
        return None
    already = db.query(EarnedBadge).filter_by(
        profile_id=profile_id, badge_id=badge_def.id
    ).first()
    if already:
        return None
    earned = EarnedBadge(profile_id=profile_id, badge_id=badge_def.id)
    db.add(earned)
    db.flush()
    return badge_def


def check_and_award_badges(profile_id: int, db: DBSession) -> list:
    """
    Check all badge conditions for a profile and award any newly-earned badges.
    Returns list of BadgeDefinition objects for newly awarded badges.
    """
    new_badges = []

    # --- Theme mastery: graduated batches ---
    graduated_batches = (
        db.query(Batch)
        .filter(Batch.profile_id == profile_id, Batch.status == "graduated")
        .all()
    )
    for batch in graduated_batches:
        badge_key = _CHAPTER_BADGE_KEYS.get(batch.chapter_id)
        if badge_key:
            awarded = _award_badge(profile_id, badge_key, db)
            if awarded:
                new_badges.append(awarded)

    # --- Speed: Lightning Reflexes (<3s correct solve) ---
    fast_solve = (
        db.query(Attempt)
        .filter(
            Attempt.profile_id == profile_id,
            Attempt.success == 1,
            Attempt.time_taken_ms < 3_000,
        )
        .first()
    )
    if fast_solve:
        awarded = _award_badge(profile_id, "lightning_reflexes", db)
        if awarded:
            new_badges.append(awarded)

    # --- Speed: Speed Demon (circle avg <10s) ---
    # Check all batches for any circle with avg time < 10s
    batches = db.query(Batch).filter(Batch.profile_id == profile_id).all()
    for batch in batches:
        for circle in range(1, batch.current_circle + 1):
            correct = (
                db.query(Attempt)
                .filter(
                    Attempt.profile_id == profile_id,
                    Attempt.batch_id == batch.id,
                    Attempt.circle == circle,
                    Attempt.success == 1,
                )
                .all()
            )
            if correct and (sum(a.time_taken_ms for a in correct) / len(correct)) < 10_000:
                awarded = _award_badge(profile_id, "speed_demon", db)
                if awarded:
                    new_badges.append(awarded)
                break

    # --- Streak badges ---
    profile = db.query(Profile).get(profile_id)
    if profile:
        streak = profile.current_streak or 0
        for days, key in [(30, "streak_30"), (14, "streak_14"), (7, "streak_7"), (3, "streak_3")]:
            if streak >= days:
                awarded = _award_badge(profile_id, key, db)
                if awarded:
                    new_badges.append(awarded)

    # --- Milestone: First Solve ---
    total_correct = (
        db.query(Attempt)
        .filter(Attempt.profile_id == profile_id, Attempt.success == 1)
        .count()
    )
    if total_correct >= 1:
        awarded = _award_badge(profile_id, "first_solve", db)
        if awarded:
            new_badges.append(awarded)

    # --- Milestone: Century (100 correct) ---
    if total_correct >= 100:
        awarded = _award_badge(profile_id, "century", db)
        if awarded:
            new_badges.append(awarded)

    # --- Milestone: 500 Club ---
    if total_correct >= 500:
        awarded = _award_badge(profile_id, "five_hundred", db)
        if awarded:
            new_badges.append(awarded)

    # --- Milestone: Full Book (all 22 chapters graduated) ---
    graduated_chapter_ids = {b.chapter_id for b in graduated_batches}
    if len(graduated_chapter_ids) >= 22:
        awarded = _award_badge(profile_id, "full_book", db)
        if awarded:
            new_badges.append(awarded)

    # --- Improvement: Half the Time ---
    for batch in batches:
        if batch.current_circle >= 2:
            c1 = (
                db.query(Attempt)
                .filter(
                    Attempt.profile_id == profile_id,
                    Attempt.batch_id == batch.id,
                    Attempt.circle == 1,
                    Attempt.success == 1,
                )
                .all()
            )
            latest = (
                db.query(Attempt)
                .filter(
                    Attempt.profile_id == profile_id,
                    Attempt.batch_id == batch.id,
                    Attempt.circle == batch.current_circle - 1,
                    Attempt.success == 1,
                )
                .all()
            )
            if c1 and latest:
                avg_c1 = sum(a.time_taken_ms for a in c1) / len(c1)
                avg_latest = sum(a.time_taken_ms for a in latest) / len(latest)
                if avg_latest < avg_c1 * 0.5:
                    awarded = _award_badge(profile_id, "half_the_time", db)
                    if awarded:
                        new_badges.append(awarded)
                    break

    db.commit()
    return new_badges


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

def get_leaderboard(db: DBSession) -> list:
    """Return leaderboard rows for student profiles only."""
    students = (
        db.query(Profile)
        .filter(Profile.role == "student")
        .all()
    )
    rows = []
    for p in students:
        # Count graduated chapters
        chapters_graduated = (
            db.query(Batch)
            .filter(Batch.profile_id == p.id, Batch.status == "graduated")
            .count()
        )
        # Best single puzzle time (fastest correct attempt)
        best_attempt = (
            db.query(Attempt)
            .filter(Attempt.profile_id == p.id, Attempt.success == 1)
            .order_by(Attempt.time_taken_ms.asc())
            .first()
        )
        rows.append({
            "id": p.id,
            "name": p.name,
            "total_xp": p.total_xp or 0,
            "current_streak": p.current_streak or 0,
            "chapters_graduated": chapters_graduated,
            "best_puzzle_time_ms": best_attempt.time_taken_ms if best_attempt else None,
        })
    return rows
