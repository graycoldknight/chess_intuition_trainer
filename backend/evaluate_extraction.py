"""
Evaluation harness for the Polgar PDF extraction pipeline.

CLI usage:
    cd backend && python evaluate_extraction.py

Functions:
    compare_fens(extracted_fen, truth_fen) -> FenDiff
    evaluate_pipeline(extracted, truth_q, truth_a) -> dict
"""

import re
import json
import os
from dataclasses import dataclass, field
import chess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# FenDiff
# ---------------------------------------------------------------------------

@dataclass
class FenDiff:
    is_exact_match: bool
    squares_different: int
    error_types: list = field(default_factory=list)
    details: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# compare_fens
# ---------------------------------------------------------------------------

def _fen_to_board_array(fen: str) -> list:
    """Parse FEN piece-placement into a 64-element list (index 0 = a1, index 63 = h8).
    Each element is a piece symbol string ('P', 'r', etc.) or None."""
    try:
        board = chess.Board(fen)
    except Exception:
        return [None] * 64
    result = []
    for sq in chess.SQUARES:  # a1..h8
        piece = board.piece_at(sq)
        result.append(piece.symbol() if piece else None)
    return result


def compare_fens(extracted_fen: str, truth_fen: str) -> FenDiff:
    """
    Compare two FEN strings square by square and classify differences.

    Error types:
    - edge_blindness: differences on rank 8 or file h (boundary squares)
    - piece_misid: same square, different piece type (e.g. bishop vs queen)
    - rank_shift: piece in extracted is present in truth one rank away
    - missing_pawn: truth has a pawn but extracted has nothing there
    """
    ext_parts = extracted_fen.split()
    tru_parts = truth_fen.split()
    extracted_pp = ext_parts[0]
    truth_pp = tru_parts[0]
    extracted_turn = ext_parts[1] if len(ext_parts) > 1 else "w"
    truth_turn = tru_parts[1] if len(tru_parts) > 1 else "w"

    if extracted_pp == truth_pp and extracted_turn == truth_turn:
        return FenDiff(is_exact_match=True, squares_different=0)

    ext_arr = _fen_to_board_array(extracted_fen)
    tru_arr = _fen_to_board_array(truth_fen)

    different_squares = []
    error_types_set = set()
    details = []

    for sq in chess.SQUARES:
        ext_piece = ext_arr[sq]
        tru_piece = tru_arr[sq]
        if ext_piece == tru_piece:
            continue

        different_squares.append(sq)
        sq_name = chess.square_name(sq)
        details.append(f"{sq_name}: extracted={ext_piece!r} truth={tru_piece!r}")

        file_idx = chess.square_file(sq)   # 0=a .. 7=h
        rank_idx = chess.square_rank(sq)   # 0=rank1 .. 7=rank8

        # edge_blindness: rank 8 (index 7) or file h (index 7)
        if rank_idx == 7 or file_idx == 7:
            error_types_set.add("edge_blindness")

        # missing_pawn: truth has pawn, extracted has nothing
        if tru_piece and tru_piece.lower() == "p" and ext_piece is None:
            error_types_set.add("missing_pawn")

        # piece_misid: both squares have a piece but different type
        if ext_piece and tru_piece and ext_piece.lower() != tru_piece.lower():
            error_types_set.add("piece_misid")

        # rank_shift: check if the truth piece appears on the square ±1 rank in extracted
        if tru_piece and rank_idx > 0:
            sq_below = chess.square(file_idx, rank_idx - 1)
            if ext_arr[sq_below] == tru_piece:
                error_types_set.add("rank_shift")
        if tru_piece and rank_idx < 7:
            sq_above = chess.square(file_idx, rank_idx + 1)
            if ext_arr[sq_above] == tru_piece:
                error_types_set.add("rank_shift")

    return FenDiff(
        is_exact_match=False,
        squares_different=len(different_squares),
        error_types=sorted(error_types_set),
        details=details,
    )


# ---------------------------------------------------------------------------
# evaluate_pipeline
# ---------------------------------------------------------------------------

def evaluate_pipeline(extracted: list, truth_q: list, truth_a: list) -> dict:
    """
    Compare extracted puzzles against ground-truth questions + answers.

    Parameters:
        extracted  - list of dicts with puzzle_number, fen, solution_uci_line, etc.
        truth_q    - list of dicts with puzzle_number, fen, turn
        truth_a    - list of dicts with puzzle_number, solution_uci_line, solution_uci

    Returns a report dict with:
        fen_exact_match_rate
        piece_placement_accuracy  (avg fraction of 64 squares correct)
        first_move_validation_rate
        full_line_validation_rate
        error_type_breakdown
        failed_puzzles
    """
    ext_by_num = {p["puzzle_number"]: p for p in extracted}
    tru_q_by_num = {q["puzzle_number"]: q for q in truth_q}
    tru_a_by_num = {a["puzzle_number"]: a for a in truth_a}

    puzzle_numbers = sorted(set(tru_q_by_num) & set(tru_a_by_num) & set(ext_by_num))

    fen_matches = 0
    placement_accuracies = []
    first_move_matches = 0
    full_line_matches = 0
    error_type_counts: dict[str, int] = {}
    failed_puzzles = []

    for num in puzzle_numbers:
        ext = ext_by_num[num]
        tru_q = tru_q_by_num[num]
        tru_a = tru_a_by_num[num]

        # FEN comparison
        diff = compare_fens(ext.get("fen", ""), tru_q.get("fen", ""))
        if diff.is_exact_match:
            fen_matches += 1
        else:
            for et in diff.error_types:
                error_type_counts[et] = error_type_counts.get(et, 0) + 1
            failed_puzzles.append({
                "puzzle_number": num,
                "squares_different": diff.squares_different,
                "error_types": diff.error_types,
                "details": diff.details[:5],  # first 5 diffs
            })

        # Piece placement accuracy: fraction of 64 squares that agree
        accuracy = 1.0 - (diff.squares_different / 64.0)
        placement_accuracies.append(max(0.0, accuracy))

        # First-move validation: compare solution_uci_line[0] from truth_a
        truth_uci_line = tru_a.get("solution_uci_line") or []
        ext_uci_line = ext.get("solution_uci_line") or []
        truth_first = truth_uci_line[0] if truth_uci_line else tru_a.get("solution_uci")
        ext_first = ext_uci_line[0] if ext_uci_line else ext.get("solution_uci")
        if truth_first and ext_first and truth_first == ext_first:
            first_move_matches += 1

        # Full line validation
        if truth_uci_line and ext_uci_line and truth_uci_line == ext_uci_line:
            full_line_matches += 1

    n = len(puzzle_numbers)
    if n == 0:
        return {
            "fen_exact_match_rate": 0.0,
            "piece_placement_accuracy": 0.0,
            "first_move_validation_rate": 0.0,
            "full_line_validation_rate": 0.0,
            "error_type_breakdown": {},
            "failed_puzzles": [],
            "total_compared": 0,
        }

    return {
        "fen_exact_match_rate": fen_matches / n,
        "piece_placement_accuracy": sum(placement_accuracies) / n,
        "first_move_validation_rate": first_move_matches / n,
        "full_line_validation_rate": full_line_matches / n,
        "error_type_breakdown": error_type_counts,
        "failed_puzzles": failed_puzzles,
        "total_compared": n,
    }


# ---------------------------------------------------------------------------
# CLI — evaluate against chapter 1 ground truth
# ---------------------------------------------------------------------------

def _load_json(path: str) -> list:
    with open(path) as f:
        return json.load(f)


def main():
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    from dotenv import load_dotenv
    load_dotenv()

    from database import SessionLocal, init_db
    import models  # noqa: register tables
    init_db()

    chapter_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    q_path = os.path.join(ROOT, f"chapter{chapter_id}_questions.json")
    a_path = os.path.join(ROOT, f"chapter{chapter_id}_answers.json")

    if not os.path.exists(q_path) or not os.path.exists(a_path):
        print(f"Ground truth not found: {q_path} / {a_path}")
        return

    truth_q = _load_json(q_path)
    truth_a = _load_json(a_path)

    # Load extracted puzzles from DB
    db = SessionLocal()
    try:
        from models import Puzzle
        db_puzzles = db.query(Puzzle).filter_by(chapter_id=chapter_id).all()
        if not db_puzzles:
            print(f"No puzzles in DB for chapter {chapter_id}. Run extract_chapter.py first.")
            return

        extracted = []
        for p in db_puzzles:
            extracted.append({
                "puzzle_number": p.puzzle_number,
                "fen": p.fen,
                "turn": p.turn,
                "solution_san": p.solution_san,
                "solution_uci": p.solution_uci,
                "solution_uci_line": p.solution_uci_line,
                "solution_line": p.solution_line,
            })
    finally:
        db.close()

    report = evaluate_pipeline(extracted, truth_q, truth_a)

    print(f"\n=== Chapter {chapter_id} Extraction Evaluation ===")
    print(f"Total compared:              {report['total_compared']}")
    print(f"FEN exact match rate:        {report['fen_exact_match_rate']:.1%}")
    print(f"Piece placement accuracy:    {report['piece_placement_accuracy']:.1%}")
    print(f"First move validation rate:  {report['first_move_validation_rate']:.1%}")
    print(f"Full line validation rate:   {report['full_line_validation_rate']:.1%}")

    if report["error_type_breakdown"]:
        print(f"\nError type breakdown:")
        for et, count in sorted(report["error_type_breakdown"].items(), key=lambda x: -x[1]):
            print(f"  {et}: {count}")

    if report["failed_puzzles"]:
        print(f"\nFailed puzzles ({len(report['failed_puzzles'])}):")
        for fp in report["failed_puzzles"][:10]:
            print(f"  Puzzle {fp['puzzle_number']}: {fp['squares_different']} sq diff, types={fp['error_types']}")
            for d in fp["details"][:3]:
                print(f"    {d}")


if __name__ == "__main__":
    main()
