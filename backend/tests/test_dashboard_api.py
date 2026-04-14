"""
Tests for GET /api/dashboard/{profile_id} endpoint.
RED phase: written before implementation.
"""

import pytest
from datetime import datetime, timedelta
from models import Puzzle, Batch, Session, Attempt, Profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def seed_verified_puzzles(db, chapter_id=1, count=3):
    for i in range(1, count + 1):
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


def create_batch(client):
    return client.post("/api/training/create-batch", json={"profile_id": 1, "chapter_id": 1})


# ---------------------------------------------------------------------------
# GET /api/dashboard/{profile_id}
# ---------------------------------------------------------------------------

def test_dashboard_returns_profile_info(test_client):
    resp = test_client.get("/api/dashboard/1")
    assert resp.status_code == 200
    data = resp.json()
    assert "profile" in data
    assert data["profile"]["id"] == 1
    assert "name" in data["profile"]
    assert "total_xp" in data["profile"]
    assert "current_streak" in data["profile"]


def test_dashboard_returns_training_state(test_client):
    resp = test_client.get("/api/dashboard/1")
    assert resp.status_code == 200
    data = resp.json()
    assert "training" in data
    assert "has_active_batch" in data["training"]


def test_dashboard_training_state_with_batch(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    db = sessionmaker(bind=test_engine)()
    seed_verified_puzzles(db)
    db.close()

    create_batch(test_client)
    resp = test_client.get("/api/dashboard/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["training"]["has_active_batch"] is True
    assert data["training"]["current_circle"] == 1
    assert data["training"]["total_puzzles"] == 3
    assert "circle_stats" in data["training"]


def test_dashboard_includes_session_time_remaining(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    db = sessionmaker(bind=test_engine)()
    seed_verified_puzzles(db)
    db.close()

    create_batch(test_client)
    test_client.post("/api/training/start-session/1")

    resp = test_client.get("/api/dashboard/1")
    assert resp.status_code == 200
    data = resp.json()
    remaining = data["training"]["session_time_remaining_seconds"]
    assert remaining is not None
    assert remaining > 0
    assert remaining <= 3600


def test_dashboard_circle_stats_include_avg_time_and_accuracy(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    db = sessionmaker(bind=test_engine)()
    seed_verified_puzzles(db)
    puzzles = db.query(Puzzle).all()
    db.close()

    batch_resp = create_batch(test_client)
    batch_id = batch_resp.json()["batch_id"]

    # Record attempts for all 3 puzzles in circle 1
    for p in puzzles:
        test_client.post("/api/training/attempt", json={
            "profile_id": 1,
            "puzzle_id": p.id,
            "batch_id": batch_id,
            "circle": 1,
            "success": True,
            "time_taken_ms": 8000,
            "user_move": "e7e5",
        })

    resp = test_client.get("/api/dashboard/1")
    data = resp.json()
    circle_stats = data["training"]["circle_stats"]
    assert "1" in circle_stats
    assert circle_stats["1"]["avg_time_ms"] == 8000
    assert circle_stats["1"]["correct"] == 3
    assert circle_stats["1"]["total"] == 3


def test_dashboard_streak_calculation(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker

    # Simulate a profile with a streak
    db = sessionmaker(bind=test_engine)()
    profile = db.query(Profile).get(1)
    profile.current_streak = 3
    profile.last_session_date = datetime.utcnow().strftime("%Y-%m-%d")
    db.commit()
    db.close()

    resp = test_client.get("/api/dashboard/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["profile"]["current_streak"] == 3


def test_dashboard_streak_resets_after_gap(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker

    db = sessionmaker(bind=test_engine)()
    profile = db.query(Profile).get(1)
    profile.current_streak = 5
    # Last session was 2 days ago -- streak should be reported as-is (reset happens at end_session)
    profile.last_session_date = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
    db.commit()
    db.close()

    resp = test_client.get("/api/dashboard/1")
    assert resp.status_code == 200
    data = resp.json()
    # Dashboard returns the stored streak value; reset logic fires at end_session
    assert data["profile"]["current_streak"] == 5


def test_dashboard_today_stats(test_client, test_engine):
    from sqlalchemy.orm import sessionmaker
    db = sessionmaker(bind=test_engine)()
    seed_verified_puzzles(db)
    db.close()

    create_batch(test_client)
    test_client.post("/api/training/start-session/1")

    resp = test_client.get("/api/dashboard/1")
    assert resp.status_code == 200
    data = resp.json()
    assert "today" in data
    assert "puzzles_attempted" in data["today"]
    assert "puzzles_correct" in data["today"]


def test_dashboard_404_for_unknown_profile(test_client):
    resp = test_client.get("/api/dashboard/999")
    assert resp.status_code == 404
