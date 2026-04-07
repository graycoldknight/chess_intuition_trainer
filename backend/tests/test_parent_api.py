"""
Tests for Phase 6 parent panel API endpoints.
RED phase: written before implementation.

Note: extraction is handled manually (out of scope for Phase 6 tests).

Endpoints tested:
  GET  /api/chapters                         -- list with extraction_status
  GET  /api/graduations/pending              -- batches with ready_to_graduate status
  POST /api/training/approve-graduation/{id} -- changes status, returns next_chapter_id
  POST /api/training/create-batch            -- validates chapter has verified puzzles
"""

import pytest
from models import Profile, Chapter, Puzzle, Batch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_verified_chapter(db, chapter_id=1):
    """Set chapter extraction_status to 'verified' and add a verified puzzle."""
    chapter = db.query(Chapter).get(chapter_id)
    chapter.extraction_status = "verified"
    puzzle = Puzzle(
        chapter_id=chapter_id,
        puzzle_number=1,
        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        turn="b",
        solution_san="e5",
        solution_uci="e7e5",
        verified=1,
    )
    db.add(puzzle)
    db.commit()
    return chapter, puzzle


def make_ready_batch(db, profile_id, chapter_id=1):
    """Create a batch in ready_to_graduate status."""
    batch = Batch(
        profile_id=profile_id,
        chapter_id=chapter_id,
        puzzle_ids=[],
        total_puzzles=0,
        current_circle=5,
        status="ready_to_graduate",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


# ---------------------------------------------------------------------------
# GET /api/graduations/pending
# ---------------------------------------------------------------------------

def test_graduations_pending_empty_when_no_ready_batches(test_client):
    resp = test_client.get("/api/graduations/pending")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_graduations_pending_returns_ready_batches(test_client, test_engine):
    """Create a ready_to_graduate batch and verify it appears in pending list."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=test_engine)
    db = Session()
    try:
        rishi = db.query(Profile).filter_by(name="Rishi").first()
        batch = make_ready_batch(db, profile_id=rishi.id, chapter_id=1)
        batch_id = batch.id
    finally:
        db.close()

    resp = test_client.get("/api/graduations/pending")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["batch_id"] == batch_id
    assert data[0]["status"] == "ready_to_graduate"
    assert "profile_name" in data[0]
    assert "chapter_title" in data[0]


def test_graduations_pending_excludes_active_and_graduated_batches(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=test_engine)
    db = Session()
    try:
        rishi = db.query(Profile).filter_by(name="Rishi").first()
        # active batch -- should NOT appear
        db.add(Batch(
            profile_id=rishi.id, chapter_id=1,
            puzzle_ids=[], total_puzzles=0,
            current_circle=1, status="active",
        ))
        # graduated batch -- should NOT appear
        db.add(Batch(
            profile_id=rishi.id, chapter_id=2,
            puzzle_ids=[], total_puzzles=0,
            current_circle=5, status="graduated",
        ))
        db.commit()
    finally:
        db.close()

    resp = test_client.get("/api/graduations/pending")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /api/training/approve-graduation/{batch_id}
# ---------------------------------------------------------------------------

def test_approve_graduation_changes_status_to_graduated(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=test_engine)
    db = Session()
    try:
        rishi = db.query(Profile).filter_by(name="Rishi").first()
        batch = make_ready_batch(db, profile_id=rishi.id, chapter_id=1)
        batch_id = batch.id
    finally:
        db.close()

    resp = test_client.post(f"/api/training/approve-graduation/{batch_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "graduated"


def test_approve_graduation_returns_next_chapter_id(test_client, test_engine):
    """After graduating chapter 1, response should suggest chapter 2."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=test_engine)
    db = Session()
    try:
        rishi = db.query(Profile).filter_by(name="Rishi").first()
        batch = make_ready_batch(db, profile_id=rishi.id, chapter_id=1)
        batch_id = batch.id
    finally:
        db.close()

    resp = test_client.post(f"/api/training/approve-graduation/{batch_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "next_chapter_id" in data
    assert data["next_chapter_id"] == 2  # chapter 1 + 1


def test_approve_graduation_last_chapter_returns_null_next(test_client, test_engine):
    """Graduating chapter 22 (last) returns next_chapter_id: null."""
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=test_engine)
    db = Session()
    try:
        rishi = db.query(Profile).filter_by(name="Rishi").first()
        batch = make_ready_batch(db, profile_id=rishi.id, chapter_id=22)
        batch_id = batch.id
    finally:
        db.close()

    resp = test_client.post(f"/api/training/approve-graduation/{batch_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["next_chapter_id"] is None


def test_approve_graduation_404_for_unknown_batch(test_client):
    resp = test_client.post("/api/training/approve-graduation/9999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/training/create-batch -- chapter validation
# ---------------------------------------------------------------------------

def test_create_batch_requires_verified_chapter(test_client):
    """Chapter with extraction_status='pending' and no verified puzzles -> 400."""
    resp = test_client.post(
        "/api/training/create-batch",
        json={"profile_id": 1, "chapter_id": 1},
    )
    assert resp.status_code == 400


def test_create_batch_succeeds_with_verified_puzzles(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=test_engine)
    db = Session()
    try:
        make_verified_chapter(db, chapter_id=1)
        rishi = db.query(Profile).filter_by(name="Rishi").first()
        profile_id = rishi.id
    finally:
        db.close()

    resp = test_client.post(
        "/api/training/create-batch",
        json={"profile_id": profile_id, "chapter_id": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["chapter_id"] == 1
    assert data["total_puzzles"] == 1
    assert data["status"] == "active"


# ---------------------------------------------------------------------------
# GET /api/parent/activity  (Phase 11)
# ---------------------------------------------------------------------------

def seed_verified_puzzles(db, chapter_id=1, count=3):
    """Mark the first `count` puzzles in the chapter as verified.
    Works whether puzzles were pre-imported by the startup event or not.
    """
    from models import Puzzle, Chapter
    chapter = db.query(Chapter).get(chapter_id)
    if chapter:
        chapter.extraction_status = "verified"
    existing = (
        db.query(Puzzle)
        .filter(Puzzle.chapter_id == chapter_id)
        .order_by(Puzzle.puzzle_number)
        .limit(count)
        .all()
    )
    # Update existing puzzles to verified
    for p in existing:
        p.verified = 1
    # If not enough puzzles exist, insert the missing ones
    existing_nums = {p.puzzle_number for p in existing}
    for i in range(1, count + 1):
        if i not in existing_nums:
            db.add(Puzzle(
                chapter_id=chapter_id,
                puzzle_number=i,
                fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
                turn="b",
                solution_san="e5",
                solution_uci="e7e5",
                verified=1,
            ))
    db.commit()


def test_parent_activity_returns_children(test_client):
    resp = test_client.get("/api/parent/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert "children" in data
    assert "refreshed_at" in data
    assert isinstance(data["children"], list)


def test_parent_activity_child_shape(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    seed_verified_puzzles(db)
    db.close()

    resp = test_client.get("/api/parent/activity")
    data = resp.json()
    students = [c for c in data["children"] if c["name"] in ("Rishi", "Raghav")]
    assert len(students) >= 2
    child = students[0]
    assert "profile_id" in child
    assert "name" in child
    assert "total_xp" in child
    assert "session" in child
    assert "training" in child
    assert "current_puzzle" in child
    assert "recent_attempts" in child
    assert isinstance(child["recent_attempts"], list)


def test_parent_activity_excludes_parent_profiles(test_client):
    resp = test_client.get("/api/parent/activity")
    data = resp.json()
    names = [c["name"] for c in data["children"]]
    assert "Raj" not in names


def test_parent_activity_recent_attempts_shape(test_client, test_engine):
    """When a child has attempts, they should appear in recent_attempts."""
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    seed_verified_puzzles(db, count=3)
    db.close()

    batch_resp = test_client.post("/api/training/create-batch", json={"profile_id": 1, "chapter_id": 1})
    batch_id = batch_resp.json()["batch_id"]
    puzzle_resp = test_client.get("/api/training/next-puzzle/1")
    puzzle_id = puzzle_resp.json()["puzzle"]["id"]
    test_client.post("/api/training/attempt", json={
        "profile_id": 1, "puzzle_id": puzzle_id, "batch_id": batch_id,
        "circle": 1, "success": True, "time_taken_ms": 7500, "user_move": "e7e5",
    })

    resp = test_client.get("/api/parent/activity")
    data = resp.json()
    rishi = next(c for c in data["children"] if c["profile_id"] == 1)
    assert len(rishi["recent_attempts"]) >= 1
    attempt = rishi["recent_attempts"][0]
    assert "puzzle_number" in attempt
    assert "chapter_title" in attempt
    assert "success" in attempt
    assert "time_taken_ms" in attempt
    assert attempt["success"] is True
    assert attempt["time_taken_ms"] == 7500
