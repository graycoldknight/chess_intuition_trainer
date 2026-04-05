"""
Phase 2 RED: Test extraction pipeline - parsing, merging, validation.
"""

import pytest
from extraction import parse_diagram_response, parse_solution_response, merge_and_validate


class TestParseDiagramResponse:
    def test_parses_valid_json(self):
        llm_output = '''[
            {"puzzle_number": 1, "side_to_move": "w", "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"},
            {"puzzle_number": 2, "side_to_move": "b", "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 0 1"}
        ]'''
        result = parse_diagram_response(llm_output)
        assert len(result) == 2
        assert result[0]["puzzle_number"] == 1
        assert result[0]["side_to_move"] == "w"
        assert result[1]["puzzle_number"] == 2

    def test_handles_markdown_code_fences(self):
        llm_output = '''```json
[{"puzzle_number": 1, "side_to_move": "w", "fen": "8/8/8/8/8/8/8/4K3 w - - 0 1"}]
```'''
        result = parse_diagram_response(llm_output)
        assert len(result) == 1
        assert result[0]["fen"] == "8/8/8/8/8/8/8/4K3 w - - 0 1"

    def test_returns_empty_on_invalid_json(self):
        result = parse_diagram_response("not json at all")
        assert result == []

    def test_returns_empty_on_empty_array(self):
        result = parse_diagram_response("[]")
        assert result == []

    def test_skips_incomplete_items(self):
        llm_output = '[{"puzzle_number": 1, "side_to_move": "w"}, {"puzzle_number": 2, "side_to_move": "b", "fen": "valid_fen"}]'
        result = parse_diagram_response(llm_output)
        assert len(result) == 1
        assert result[0]["puzzle_number"] == 2

    def test_normalizes_side_to_move(self):
        llm_output = '[{"puzzle_number": 1, "side_to_move": "W", "fen": "8/8/8/8/8/8/8/4K3 w - - 0 1"}]'
        result = parse_diagram_response(llm_output)
        assert result[0]["side_to_move"] == "w"


class TestParseSolutionResponse:
    def test_parses_valid_json(self):
        llm_output = '''[
            {"puzzle_number": 1, "first_move_san": "Nf6+", "full_solution": "1. Nf6+ Kg7 2. Qh7#"},
            {"puzzle_number": 2, "first_move_san": "Bxh7+", "full_solution": "1. Bxh7+ Kxh7 2. Ng5+"}
        ]'''
        result = parse_solution_response(llm_output)
        assert len(result) == 2
        assert result[0]["first_move_san"] == "Nf6+"
        assert result[1]["full_solution"] == "1. Bxh7+ Kxh7 2. Ng5+"

    def test_handles_markdown_fences(self):
        llm_output = '```json\n[{"puzzle_number": 1, "first_move_san": "e4"}]\n```'
        result = parse_solution_response(llm_output)
        assert len(result) == 1

    def test_returns_empty_on_invalid(self):
        result = parse_solution_response("garbage")
        assert result == []


class TestMergeAndValidate:
    def test_merges_matching_puzzles(self):
        diagrams = [
            {"puzzle_number": 1, "side_to_move": "w", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
        ]
        solutions = [
            {"puzzle_number": 1, "first_move_san": "e4", "full_solution": "1. e4"},
        ]
        result = merge_and_validate(diagrams, solutions)
        assert len(result) == 1
        assert result[0]["valid"] is True
        assert result[0]["solution_uci"] == "e2e4"
        assert result[0]["extraction_confidence"] == 1.0

    def test_flags_missing_solution(self):
        diagrams = [{"puzzle_number": 1, "side_to_move": "w", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}]
        solutions = []
        result = merge_and_validate(diagrams, solutions)
        assert result[0]["valid"] is False
        assert result[0]["error"] == "no_solution_found"

    def test_rejects_illegal_move(self):
        # Kh9 is not a legal move in any position
        diagrams = [{"puzzle_number": 1, "side_to_move": "w", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}]
        solutions = [{"puzzle_number": 1, "first_move_san": "Kh9", "full_solution": ""}]
        result = merge_and_validate(diagrams, solutions)
        assert result[0]["valid"] is False
        assert "illegal_move" in result[0]["error"]
        assert result[0]["extraction_confidence"] == 0.0

    def test_rejects_invalid_fen(self):
        diagrams = [{"puzzle_number": 1, "side_to_move": "w", "fen": "not_a_valid_fen"}]
        solutions = [{"puzzle_number": 1, "first_move_san": "e4", "full_solution": ""}]
        result = merge_and_validate(diagrams, solutions)
        assert result[0]["valid"] is False
        assert "invalid_fen" in result[0]["error"]

    def test_converts_san_to_uci(self):
        # Standard opening position, Nf3 = g1f3
        diagrams = [{"puzzle_number": 1, "side_to_move": "w", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"}]
        solutions = [{"puzzle_number": 1, "first_move_san": "Nf3", "full_solution": "1. Nf3"}]
        result = merge_and_validate(diagrams, solutions)
        assert result[0]["solution_uci"] == "g1f3"

    def test_multiple_puzzles_partial_match(self):
        diagrams = [
            {"puzzle_number": 1, "side_to_move": "w", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
            {"puzzle_number": 2, "side_to_move": "w", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
            {"puzzle_number": 3, "side_to_move": "w", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"},
        ]
        solutions = [
            {"puzzle_number": 1, "first_move_san": "e4", "full_solution": ""},
            {"puzzle_number": 3, "first_move_san": "d4", "full_solution": ""},
        ]
        result = merge_and_validate(diagrams, solutions)
        assert result[0]["valid"] is True
        assert result[1]["valid"] is False  # puzzle 2 has no solution
        assert result[2]["valid"] is True
