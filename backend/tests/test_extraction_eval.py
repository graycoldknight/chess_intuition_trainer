"""
Tests for Phase 15 extraction evaluation utilities.
RED phase — all tests fail until implementations are in place.
"""

import pytest
from extraction import generate_correction_hint
from evaluate_extraction import compare_fens, evaluate_pipeline


# ---------------------------------------------------------------------------
# generate_correction_hint tests
# ---------------------------------------------------------------------------

class TestGenerateCorrectionHint:

    def test_capture_on_empty_square(self):
        """Qxf6 requires a piece on f6, but f6 is empty in this FEN."""
        # Position where f6 is empty but solution says Qxf6
        fen = "r6k/pp3Qpp/2bqp3/4Np2/2P5/8/PP3PPP/5RK1 w - - 0 1"
        hint = generate_correction_hint(fen, "Qxf6", "illegal san: Qxf6")
        assert "f6" in hint

    def test_wrong_turn(self):
        """FEN says White to move but solution is a Black move like ...Qc3."""
        # White to move, but solution is Qc3 which is only relevant as a black queen move
        # Let's use a FEN where white is to move but Qe5 captures something not there
        fen = "8/1b3pkp/pN1p2p1/3Pq3/Q3P3/8/6PP/6K1 w - - 0 1"
        # Qc3 is not a valid move (no queen path), checking turn mismatch differently
        # Use a FEN that says black to move but solution is white's
        fen_black_turn = "8/1b3pkp/pN1p2p1/3Pq3/Q3P3/8/6PP/6K1 b - - 0 1"
        hint = generate_correction_hint(fen_black_turn, "Qa5", "illegal san: Qa5")
        # Qa5 isn't a black queen move (black queen is on e5), but the hint should mention something useful
        assert hint  # at minimum returns a non-empty hint

    def test_wrong_turn_explicit(self):
        """FEN says Black to move, but the solution first move is clearly White's."""
        # Start position but modified: black to move, solution says e4 (only white can play e4 from e2)
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"
        hint = generate_correction_hint(fen, "e4", "illegal san: e4")
        # e4 from black to move is illegal — hint should reference wrong turn or side
        assert any(word in hint.lower() for word in ["turn", "black", "white", "move"])

    def test_no_piece_of_right_type(self):
        """Hint for a move where no piece of that type can reach target."""
        # Empty board except king — Rh1 impossible if no rook
        fen = "8/8/8/8/8/8/8/4K3 w - - 0 1"
        hint = generate_correction_hint(fen, "Rh1", "illegal san: Rh1")
        assert hint  # returns something meaningful

    def test_returns_string(self):
        """Always returns a string, even for unknown errors."""
        fen = "8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1"
        hint = generate_correction_hint(fen, "Rf6+", "some unknown error")
        assert isinstance(hint, str)


# ---------------------------------------------------------------------------
# compare_fens tests
# ---------------------------------------------------------------------------

class TestCompareFens:

    def test_exact_match(self):
        fen = "8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1"
        diff = compare_fens(fen, fen)
        assert diff.is_exact_match
        assert diff.squares_different == 0
        assert diff.error_types == []

    def test_edge_blindness(self):
        """Rook on h8 misread as absent — classic edge blindness."""
        extracted = "8/p1r1k2r/1p5q/4Pp2/1P1Q2p1/6P1/3R1PK1/5R2 w - - 0 1"
        truth     = "7r/p1r1k3/1p5q/4Pp2/1P1Q2p1/6P1/3R1PK1/5R2 w - - 0 1"
        diff = compare_fens(extracted, truth)
        assert diff.squares_different > 0
        assert "edge_blindness" in diff.error_types

    def test_rank_shift(self):
        """Pieces shifted by one rank."""
        extracted = "r5k1/ppq2p1p/2n3p1/8/3N3r/8/PP1Q1PPP/5RK1 w - - 0 1"
        truth     = "r7/ppq2pkp/2n3p1/8/3N3r/8/PP1Q1PPP/R4RK1 w - - 0 1"
        diff = compare_fens(extracted, truth)
        assert not diff.is_exact_match
        assert diff.squares_different > 0

    def test_returns_fenDiff_with_details(self):
        """FenDiff object has all expected fields."""
        fen1 = "8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1"
        fen2 = "8/1b6/p6k/4p1p1/4P1Pp/3P1R2/1b4K1/8 w - - 0 1"
        diff = compare_fens(fen1, fen2)
        assert not diff.is_exact_match
        assert isinstance(diff.squares_different, int)
        assert isinstance(diff.error_types, list)
        assert isinstance(diff.details, list)

    def test_piece_misidentification(self):
        """Bishop misread as queen."""
        # Same position but one piece changed b→q
        extracted = "8/1q6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1"
        truth     = "8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1"
        diff = compare_fens(extracted, truth)
        assert not diff.is_exact_match
        assert diff.squares_different >= 1
        assert "piece_misid" in diff.error_types


# ---------------------------------------------------------------------------
# evaluate_pipeline tests
# ---------------------------------------------------------------------------

class TestEvaluatePipeline:

    def _make_puzzle(self, num, fen, turn, solution_san, solution_uci, solution_uci_line=None, solution_line=None):
        return {
            "puzzle_number": num,
            "fen": fen,
            "turn": turn,
            "solution_san": solution_san,
            "solution_uci": solution_uci,
            "solution_uci_line": solution_uci_line or [solution_uci],
            "solution_line": solution_line or "",
        }

    def test_all_exact_match(self):
        fen = "8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1"
        truth_q = [{"puzzle_number": 1, "fen": fen, "turn": "w"}]
        truth_a = [self._make_puzzle(1, fen, "w", "Rf6+", "f3f6", ["f3f6", "h6g7", "f6b6"])]
        extracted = [self._make_puzzle(1, fen, "w", "Rf6+", "f3f6", ["f3f6", "h6g7", "f6b6"])]
        report = evaluate_pipeline(extracted, truth_q, truth_a)
        assert report["fen_exact_match_rate"] == pytest.approx(1.0)

    def test_partial_match_rate(self):
        fen1 = "8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1"
        fen2 = "r2qk2r/ppp2ppp/2np4/8/3Pn3/2P1B3/PP2NPPP/R2QK2R w KQkq - 0 1"
        fen2_wrong = "r2qk2r/ppp2ppp/2np4/8/3Pn3/2P1B3/PP2NPPP/R2QK2R b KQkq - 0 1"

        truth_q = [
            {"puzzle_number": 1, "fen": fen1, "turn": "w"},
            {"puzzle_number": 2, "fen": fen2, "turn": "w"},
            {"puzzle_number": 3, "fen": fen1, "turn": "w"},
        ]
        truth_a = [
            self._make_puzzle(1, fen1, "w", "Rf6+", "f3f6", ["f3f6"]),
            self._make_puzzle(2, fen2, "w", "Nd6+", "e4d6", ["e4d6"]),
            self._make_puzzle(3, fen1, "w", "Rf6+", "f3f6", ["f3f6"]),
        ]
        extracted = [
            self._make_puzzle(1, fen1, "w", "Rf6+", "f3f6", ["f3f6"]),       # exact
            self._make_puzzle(2, fen2_wrong, "w", "Nd6+", "e4d6", ["e4d6"]), # FEN mismatch
            self._make_puzzle(3, fen1, "w", "Rf6+", "f3f6", ["f3f6"]),       # exact
        ]
        report = evaluate_pipeline(extracted, truth_q, truth_a)
        assert report["fen_exact_match_rate"] == pytest.approx(2 / 3)

    def test_first_move_validation_rate(self):
        """First move validation uses solution_uci_line[0] from truth."""
        fen = "8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1"
        truth_q = [{"puzzle_number": 1, "fen": fen, "turn": "w"}]
        truth_a = [self._make_puzzle(1, fen, "w", "Rf6+", "f3f6", ["f3f6", "h6g7", "f6b6"])]
        # Extracted has wrong first move
        extracted = [self._make_puzzle(1, fen, "w", "Rg3", "f3g3", ["f3g3"])]
        report = evaluate_pipeline(extracted, truth_q, truth_a)
        assert report["first_move_validation_rate"] == pytest.approx(0.0)

    def test_report_has_all_fields(self):
        fen = "8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1"
        truth_q = [{"puzzle_number": 1, "fen": fen, "turn": "w"}]
        truth_a = [self._make_puzzle(1, fen, "w", "Rf6+", "f3f6")]
        extracted = [self._make_puzzle(1, fen, "w", "Rf6+", "f3f6")]
        report = evaluate_pipeline(extracted, truth_q, truth_a)
        for key in ["fen_exact_match_rate", "piece_placement_accuracy",
                    "first_move_validation_rate", "full_line_validation_rate",
                    "error_type_breakdown", "failed_puzzles"]:
            assert key in report, f"Missing key: {key}"
