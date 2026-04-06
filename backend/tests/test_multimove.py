"""
Tests for multi-move puzzle sequence parsing (Phase 9).
Tests parse_solution_to_uci utility that converts prose answer text + FEN
into a validated list of UCI move strings.
"""

import pytest
from unittest.mock import patch, MagicMock
from models import Puzzle
import extraction


# ---------------------------------------------------------------------------
# Fixtures — real puzzle FENs + answers from chapter1_answers.txt
# ---------------------------------------------------------------------------

# Puzzle 1: "1. Rf6+ Kg7 2. Rb6 forks both Black bishops."
PUZZLE_1_FEN = "8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1"
PUZZLE_1_ANSWER = "Rf6+ (intermediate move) Kg7 2. Rb6 forks both Black bishops."

# Puzzle 3: "Look for the unprotected piece on c5! 1. Bxe6 fxe6 2. Qh5+."
PUZZLE_3_FEN = "r2qk2r/ppp2ppp/2n1b3/2b5/2BpP3/8/PPPN1PPP/R1BQ1RK1 w kq - 0 1"
PUZZLE_3_ANSWER = "Look for the unprotected piece on c5! 1. Bxe6 fxe6 2. Qh5+."

# Puzzle 34 (promotion): "1. f8=Q+! Kxf8 and now 2. Bxd6+."
PUZZLE_34_FEN = "8/r4Pk1/3p2pp/8/p4B2/r4NP1/6KP/3R4 w - - 0 1"
PUZZLE_34_ANSWER = "the f7 pawn can be used in a very beneficial way: 1. f8=Q+! Kxf8 and now 2. Bxd6+."

# Single-move puzzle: solution is just one move
SINGLE_MOVE_FEN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
SINGLE_MOVE_ANSWER = "1... e5 is the best reply."


# ---------------------------------------------------------------------------
# Mock LLM response helper
# ---------------------------------------------------------------------------

def mock_gemini_extract(san_moves: list[str]):
    """Create a mock Gemini client that returns the given SAN move list."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    import json
    mock_response.text = json.dumps(san_moves)
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParseSolutionToUci:
    """Tests for extraction.parse_solution_to_uci(fen, solution_text)."""

    def test_multi_move_returns_correct_uci_list(self):
        """Puzzle 1: Rf6+ Kg7 Rb6 should return 3 UCI moves."""
        mock_client = mock_gemini_extract(["Rf6+", "Kg7", "Rb6"])
        result = extraction.parse_solution_to_uci(PUZZLE_1_FEN, PUZZLE_1_ANSWER, client=mock_client)
        assert result is not None
        assert len(result) == 3
        assert result[0] == "f3f6"  # Rf6+
        assert result[1] == "h6g7"  # Kg7
        assert result[2] == "f6b6"  # Rb6

    def test_two_move_sequence(self):
        """Puzzle 3: Bxe6 fxe6 Qh5+ should return 3 UCI moves."""
        mock_client = mock_gemini_extract(["Bxe6", "fxe6", "Qh5+"])
        result = extraction.parse_solution_to_uci(PUZZLE_3_FEN, PUZZLE_3_ANSWER, client=mock_client)
        assert result is not None
        assert len(result) == 3
        assert result[0] == "c4e6"  # Bxe6
        assert result[1] == "f7e6"  # fxe6
        assert result[2] == "d1h5"  # Qh5+

    def test_promotion_move(self):
        """Puzzle 34: f8=Q+ should include promotion suffix."""
        mock_client = mock_gemini_extract(["f8=Q+", "Kxf8", "Bxd6+"])
        result = extraction.parse_solution_to_uci(PUZZLE_34_FEN, PUZZLE_34_ANSWER, client=mock_client)
        assert result is not None
        assert len(result) == 3
        assert result[0] == "f7f8q"  # f8=Q+ (promotion to queen)
        assert result[1] == "g7f8"   # Kxf8 (king on g7 takes promoted queen)
        # Bxd6+ after — bishop was on f4
        assert result[2] == "f4d6"   # Bxd6+

    def test_single_move_returns_single_element_list(self):
        """A single-move solution should still return a list with one element."""
        mock_client = mock_gemini_extract(["e5"])
        result = extraction.parse_solution_to_uci(SINGLE_MOVE_FEN, SINGLE_MOVE_ANSWER, client=mock_client)
        assert result is not None
        assert len(result) == 1
        assert result[0] == "e7e5"

    def test_unparseable_text_returns_none(self):
        """When LLM returns empty or garbage, should return None."""
        mock_client = mock_gemini_extract([])
        result = extraction.parse_solution_to_uci(PUZZLE_1_FEN, "This puzzle is tricky", client=mock_client)
        assert result is None

    def test_illegal_move_returns_none(self):
        """When LLM extracts a move that's illegal in the position, return None."""
        mock_client = mock_gemini_extract(["Qh7#"])  # No queen can reach h7 from starting pos
        result = extraction.parse_solution_to_uci(SINGLE_MOVE_FEN, "1. Qh7#", client=mock_client)
        assert result is None

    def test_move_illegal_mid_sequence_returns_none(self):
        """If the first move is valid but second is not, return None."""
        # Rf6+ is valid, but Qh1 doesn't make sense as Black's reply
        mock_client = mock_gemini_extract(["Rf6+", "Qh1"])
        result = extraction.parse_solution_to_uci(PUZZLE_1_FEN, PUZZLE_1_ANSWER, client=mock_client)
        assert result is None
