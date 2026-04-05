"""
Tests for training API endpoints in main.py.
Uses the test_client fixture (seeded, in-memory DB).
"""

import pytest
from models import Puzzle, Batch, Session
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def seed_verified_puzzles(db, chapter_id=1, count=3):
    for i in range(1, count + 1):
        p = Puzzle(
            chapter_id=chapter_id,
            puzzle_number=i,
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            turn="b",
            solution_san="e5",
            solution_uci="e7e5",
            verified=1,
        )
        db.add(p)
    db.commit()


def create_batch_via_api(client):
    return client.post(
        "/api/training/create-batch",
        json={"profile_id": 1, "chapter_id": 1},
    )


# ---------------------------------------------------------------------------
# GET /api/training/state/{profile_id}
# ---------------------------------------------------------------------------

def test_training_state_no_batch(test_client):
    resp = test_client.get("/api/training/state/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_active_batch"] is False


def test_training_state_with_batch(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    seed_verified_puzzles(db)
    db.close()

    create_batch_via_api(test_client)
    resp = test_client.get("/api/training/state/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_active_batch"] is True
    assert data["current_circle"] == 1
    assert data["total_puzzles"] == 3
    assert data["status"] == "active"


# ---------------------------------------------------------------------------
# GET /api/training/next-puzzle/{profile_id}
# ---------------------------------------------------------------------------

def test_next_puzzle_no_batch(test_client):
    resp = test_client.get("/api/training/next-puzzle/1")
    assert resp.status_code == 200
    assert resp.json()["puzzle"] is None


def test_next_puzzle_returns_puzzle(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    seed_verified_puzzles(db)
    db.close()

    create_batch_via_api(test_client)
    resp = test_client.get("/api/training/next-puzzle/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["puzzle"] is not None
    assert "fen" in data["puzzle"]
    assert "solution_uci" in data["puzzle"]


# ---------------------------------------------------------------------------
# POST /api/training/create-batch
# ---------------------------------------------------------------------------

def test_create_batch_success(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    seed_verified_puzzles(db)
    db.close()

    resp = create_batch_via_api(test_client)
    assert resp.status_code == 200
    data = resp.json()
    assert data["batch_id"] is not None
    assert data["total_puzzles"] == 3
    assert data["current_circle"] == 1
    assert data["status"] == "active"


def test_create_batch_no_verified_puzzles(test_client):
    resp = create_batch_via_api(test_client)
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/training/attempt
# ---------------------------------------------------------------------------

def test_record_attempt_success(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    seed_verified_puzzles(db)
    puzzle = db.query(Puzzle).first()
    db.close()

    batch_resp = create_batch_via_api(test_client)
    batch_id = batch_resp.json()["batch_id"]

    resp = test_client.post("/api/training/attempt", json={
        "profile_id": 1,
        "puzzle_id": puzzle.id,
        "batch_id": batch_id,
        "circle": 1,
        "success": True,
        "time_taken_ms": 8500,
        "user_move": "e7e5",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["attempt_id"] is not None
    assert data["success"] is True


# ---------------------------------------------------------------------------
# POST /api/training/start-session/{profile_id}
# ---------------------------------------------------------------------------

def test_start_session(test_client):
    resp = test_client.post("/api/training/start-session/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] is not None
    assert data["profile_id"] == 1


# ---------------------------------------------------------------------------
# POST /api/training/end-session/{session_id}
# ---------------------------------------------------------------------------

def test_end_session(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    session = Session(
        profile_id=1,
        started_at=datetime.utcnow(),
        puzzles_attempted=5,
        puzzles_correct=4,
        xp_earned=0,
    )
    db.add(session)
    db.commit()
    session_id = session.id
    db.close()

    resp = test_client.post(f"/api/training/end-session/{session_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["ended_at"] is not None
    assert data["duration_seconds"] >= 0


# ---------------------------------------------------------------------------
# POST /api/training/approve-graduation/{batch_id}
# ---------------------------------------------------------------------------

def test_approve_graduation(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    seed_verified_puzzles(db)
    db.close()

    batch_resp = create_batch_via_api(test_client)
    batch_id = batch_resp.json()["batch_id"]

    # Manually set ready_to_graduate
    db = TestSession()
    b = db.query(Batch).get(batch_id)
    b.status = "ready_to_graduate"
    db.commit()
    db.close()

    resp = test_client.post(f"/api/training/approve-graduation/{batch_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "graduated"
