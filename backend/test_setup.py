"""
Test profile setup/teardown script.
Called from e2e/setup/global-setup.ts and global-teardown.ts.
Uses the same SQLAlchemy session as the backend so data is immediately visible to the API.

Usage:
  python test_setup.py create   — inserts Test profile (ID 99) + Chapter 1 batch + session
  python test_setup.py destroy  — removes all Test profile data
"""

import sys
import json
from datetime import datetime
from database import SessionLocal
from models import Profile, Batch, Session as TrainingSession

PROFILE_ID = 99
CHAPTER_ID = 1
PUZZLE_IDS = list(range(1, 50)) + [59]  # 50 verified puzzles in chapter 1


def destroy(db):
    db.query(TrainingSession).filter(TrainingSession.profile_id == PROFILE_ID).delete()
    db.query(Batch).filter(Batch.profile_id == PROFILE_ID).delete()
    db.query(Profile).filter(Profile.id == PROFILE_ID).delete()
    db.commit()
    print(f"✔  Test profile ({PROFILE_ID}) destroyed")


def create(db):
    # Always start clean
    destroy(db)

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
        puzzle_ids=json.dumps(PUZZLE_IDS),
        total_puzzles=len(PUZZLE_IDS),
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

    print(f"✔  Test profile ({PROFILE_ID}) created — batch {batch.id}, session {session.id}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "create"
    db = SessionLocal()
    try:
        if cmd == "destroy":
            destroy(db)
        else:
            create(db)
    finally:
        db.close()
