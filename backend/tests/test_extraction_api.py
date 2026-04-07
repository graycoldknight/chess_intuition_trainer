"""
Phase 2 RED: Test extraction API endpoints.
"""

import pytest
from models import Chapter, Puzzle


def _add_puzzle(db, chapter_id=1, puzzle_number=1, verified=0):
    """Helper to add a test puzzle."""
    p = Puzzle(
        chapter_id=chapter_id,
        puzzle_number=puzzle_number,
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        turn="w",
        solution_san="e4",
        solution_uci="e2e4",
        verified=verified,
        extraction_confidence=1.0,
    )
    db.add(p)
    db.commit()
    return p


def test_list_chapters_returns_all_22(test_client):
    """GET /api/chapters returns all 22 chapters."""
    response = test_client.get("/api/chapters")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 22
    assert data[0]["title"] == "Forks and Double Attacks"
    assert data[0]["extraction_status"] == "pending"



def test_get_unverified_puzzles(test_client, test_engine):
    """GET /api/puzzles/unverified/1 returns unverified puzzles."""
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    _add_puzzle(db, chapter_id=1, puzzle_number=1, verified=0)
    _add_puzzle(db, chapter_id=1, puzzle_number=2, verified=1)
    db.close()

    response = test_client.get("/api/puzzles/unverified/1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["puzzle_number"] == 1
    assert data[0]["verified"] == 0


def test_verify_single_puzzle(test_client, test_engine):
    """PUT /api/puzzles/{id}/verify sets verified=1."""
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    p = _add_puzzle(db, chapter_id=1, puzzle_number=1)
    puzzle_id = p.id
    db.close()

    response = test_client.put(f"/api/puzzles/{puzzle_id}/verify")
    assert response.status_code == 200
    assert response.json()["verified"] is True


def test_verify_all_puzzles(test_client, test_engine):
    """POST /api/chapters/1/verify-all marks all puzzles verified."""
    from sqlalchemy.orm import sessionmaker
    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()
    _add_puzzle(db, chapter_id=1, puzzle_number=1, verified=0)
    _add_puzzle(db, chapter_id=1, puzzle_number=2, verified=0)
    db.close()

    response = test_client.post("/api/chapters/1/verify-all")
    assert response.status_code == 200
    data = response.json()
    assert data["verified_count"] == 2

    # Verify all are now verified
    unverified = test_client.get("/api/puzzles/unverified/1").json()
    assert len(unverified) == 0
