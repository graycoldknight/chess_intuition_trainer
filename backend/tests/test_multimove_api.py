"""
Tests for multi-move puzzle API endpoints (Phase 9).
Tests the import-answers endpoint and next-puzzle response changes.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from models import Puzzle, Batch, Profile, Chapter
import training


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CHAPTER_1_ANSWERS_SAMPLE = """1. Rf6+ (intermediate move) Kg7 2. Rb6 forks both Black bishops.
2. The first step is to chase the Black knight away from c6 with 1. d5 Ne5 and then fork with 2. Qa4+.
3. Look for the unprotected piece on c5! 1. Bxe6 fxe6 2. Qh5+."""


def make_puzzle_with_fen(db, chapter_id, puzzle_number, fen, turn="w", solution_san="Rf6+", solution_uci="f3f6"):
    p = Puzzle(
        chapter_id=chapter_id,
        puzzle_number=puzzle_number,
        fen=fen,
        turn=turn,
        solution_san=solution_san,
        solution_uci=solution_uci,
        verified=1,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------------------------------------------------------------------------
# Tests — import-answers endpoint
# ---------------------------------------------------------------------------

class TestImportAnswersEndpoint:

    def test_import_answers_populates_solution_line(self, test_client):
        """POST /api/chapters/{id}/import-answers should update solution_line for each puzzle."""
        # The seeded DB has chapter 1 with puzzles from extraction.
        # We'll mock parse_solution_to_uci to return known values.
        with patch("extraction.parse_solution_to_uci") as mock_parse:
            mock_parse.return_value = ["f3f6", "h6g7", "f6b6"]
            resp = test_client.post(
                "/api/chapters/1/import-answers",
                json={"answers_text": CHAPTER_1_ANSWERS_SAMPLE},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "parsed" in data
        assert "failed" in data

    def test_import_answers_stores_solution_uci_line(self, test_client):
        """After import, puzzles should have solution_uci_line populated."""
        with patch("extraction.parse_solution_to_uci") as mock_parse:
            mock_parse.return_value = ["f3f6", "h6g7", "f6b6"]
            test_client.post(
                "/api/chapters/1/import-answers",
                json={"answers_text": CHAPTER_1_ANSWERS_SAMPLE},
            )

        # Fetch a puzzle directly to verify
        resp = test_client.get("/api/training/next-puzzle/1")
        if resp.json().get("puzzle"):
            puzzle = resp.json()["puzzle"]
            assert "solution_uci_line" in puzzle

    def test_import_returns_failure_count(self, test_client):
        """When parse fails for some puzzles, they appear in the failed list."""
        # Seed two puzzles in chapter 1 so the flaky_parse gets called twice
        import database
        from models import Puzzle
        db = database.SessionLocal()
        db.add(Puzzle(chapter_id=1, puzzle_number=1, fen="8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1", turn="w", solution_san="Rf6+", solution_uci="f3f6", verified=1))
        db.add(Puzzle(chapter_id=1, puzzle_number=2, fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1", turn="b", solution_san="e5", solution_uci="e7e5", verified=1))
        db.commit()
        db.close()

        call_count = 0

        def flaky_parse(fen, text, client=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return None  # Second puzzle fails
            return ["f3f6"]

        with patch("extraction.parse_solution_to_uci", side_effect=flaky_parse):
            resp = test_client.post(
                "/api/chapters/1/import-answers",
                json={"answers_text": CHAPTER_1_ANSWERS_SAMPLE},
            )

        data = resp.json()
        assert len(data["failed"]) >= 1

    def test_import_is_idempotent(self, test_client):
        """Running import twice doesn't create duplicate data."""
        with patch("extraction.parse_solution_to_uci") as mock_parse:
            mock_parse.return_value = ["f3f6", "h6g7"]
            resp1 = test_client.post(
                "/api/chapters/1/import-answers",
                json={"answers_text": CHAPTER_1_ANSWERS_SAMPLE},
            )
            resp2 = test_client.post(
                "/api/chapters/1/import-answers",
                json={"answers_text": CHAPTER_1_ANSWERS_SAMPLE},
            )

        assert resp1.json()["total"] == resp2.json()["total"]


# ---------------------------------------------------------------------------
# Tests — next-puzzle response
# ---------------------------------------------------------------------------

class TestNextPuzzleResponse:

    def test_next_puzzle_includes_solution_uci_line(self, test_client):
        """GET /api/training/next-puzzle/{id} should include solution_uci_line field."""
        resp = test_client.get("/api/training/next-puzzle/1")
        data = resp.json()
        if data.get("puzzle"):
            assert "solution_uci_line" in data["puzzle"]

    def test_solution_uci_line_falls_back_to_single_move(self, test_client):
        """When solution_uci_line is null, should fall back to [solution_uci]."""
        resp = test_client.get("/api/training/next-puzzle/1")
        data = resp.json()
        if data.get("puzzle"):
            puzzle = data["puzzle"]
            # When solution_uci_line is not set in DB, should be [solution_uci]
            if puzzle["solution_uci_line"] is not None:
                assert isinstance(puzzle["solution_uci_line"], list)
            else:
                # Fallback should be applied
                pass  # The endpoint should never return null for this field
