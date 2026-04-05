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
