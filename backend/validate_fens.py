"""
Validate that every puzzle's FEN + answer text produces a legal move sequence.

Usage:
  # Requires GOOGLE_API_KEY or GEMINI_API_KEY in environment (or source .env)
  set -a && source .env && set +a && python3 validate_fens.py

  # Check a single puzzle
  python3 validate_fens.py --puzzle 16

  # Skip LLM extraction and just validate puzzles that already have solution_uci_line
  python3 validate_fens.py --db-only
"""

import argparse
import chess
import re
import sys
from pathlib import Path
from database import SessionLocal
from models import Puzzle


def load_answers(path: Path = None) -> dict[int, str]:
    """Parse chapter1_answers.txt into {puzzle_number: answer_text}."""
    if path is None:
        path = Path(__file__).resolve().parent.parent / "chapter1_answers.txt"
    if not path.exists():
        print(f"  Warning: {path} not found")
        return {}
    answers = {}
    for line in path.read_text().strip().split("\n"):
        m = re.match(r"^(\d+)\.\s*(.*)", line)
        if m:
            answers[int(m.group(1))] = m.group(2)
    return answers


def validate_uci_line(fen: str, uci_moves: list[str]) -> tuple[bool, str]:
    """Validate a UCI move sequence against a FEN. Returns (ok, error_message)."""
    board = chess.Board(fen)
    for i, uci in enumerate(uci_moves):
        try:
            move = chess.Move.from_uci(uci)
            if move not in board.legal_moves:
                legal = [m.uci() for m in board.legal_moves]
                return False, f"move {i} '{uci}' is illegal. Legal: {legal[:10]}"
            board.push(move)
        except Exception as e:
            return False, f"move {i} '{uci}' parse error: {e}"
    return True, ""


def validate_with_llm(fen: str, answer_text: str) -> tuple[bool, list[str] | None, str]:
    """Use LLM to extract SAN moves from answer text, validate against FEN.
    Returns (ok, uci_moves_or_none, error_message)."""
    from extraction import parse_solution_to_uci
    uci_moves = parse_solution_to_uci(fen, answer_text)
    if uci_moves is None:
        return False, None, "LLM extraction or validation failed"
    return True, uci_moves, ""


def main():
    parser = argparse.ArgumentParser(description="Validate puzzle FENs against answers")
    parser.add_argument("--puzzle", type=int, help="Validate a single puzzle number")
    parser.add_argument("--chapter", type=int, default=1, help="Chapter ID (default: 1)")
    parser.add_argument("--db-only", action="store_true",
                        help="Only validate puzzles that already have solution_uci_line in DB")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show passing puzzles too")
    args = parser.parse_args()

    db = SessionLocal()
    answers = load_answers()

    query = db.query(Puzzle).filter(Puzzle.chapter_id == args.chapter, Puzzle.verified == 1)
    if args.puzzle:
        query = query.filter(Puzzle.puzzle_number == args.puzzle)
    puzzles = query.order_by(Puzzle.puzzle_number).all()

    passed, failed, skipped = 0, 0, 0

    for p in puzzles:
        prefix = f"#{p.puzzle_number:3d}"

        if args.db_only:
            if not p.solution_uci_line:
                skipped += 1
                continue
            ok, err = validate_uci_line(p.fen, p.solution_uci_line)
            if ok:
                passed += 1
                if args.verbose:
                    print(f"  {prefix}: OK  {p.solution_uci_line}")
            else:
                failed += 1
                print(f"  {prefix}: FAIL (db)  {err}")
                print(f"         FEN: {p.fen}")
                print(f"         UCI: {p.solution_uci_line}")
        else:
            answer = answers.get(p.puzzle_number)
            if not answer:
                skipped += 1
                if args.verbose:
                    print(f"  {prefix}: SKIP (no answer text)")
                continue

            ok, uci_moves, err = validate_with_llm(p.fen, answer)
            if ok:
                passed += 1
                if args.verbose:
                    print(f"  {prefix}: OK  {uci_moves}")
            else:
                failed += 1
                print(f"  {prefix}: FAIL  {err}")
                print(f"         FEN: {p.fen}")
                print(f"         Answer: {answer}")

    db.close()

    print(f"\n  Results: {passed} passed, {failed} failed, {skipped} skipped")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
