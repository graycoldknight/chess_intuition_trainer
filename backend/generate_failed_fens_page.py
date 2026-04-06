"""
Generate an HTML review page for puzzles that fail FEN validation.

Reads the DB + chapter1_answers.txt, runs move validation, and outputs
failed_fens.html with board images and text boxes for corrections.

Usage:
  set -a && source .env && set +a && python3 generate_failed_fens_page.py

  # Specify chapter
  python3 generate_failed_fens_page.py --chapter 2

  # Custom output path
  python3 generate_failed_fens_page.py -o /tmp/review.html
"""

import argparse
import chess
import re
import sys
from pathlib import Path
from database import SessionLocal
from models import Puzzle
from extraction import parse_solution_to_uci


def load_answers(chapter_id: int = 1) -> dict[int, str]:
    path = Path(__file__).resolve().parent.parent / f"chapter{chapter_id}_answers.txt"
    if not path.exists():
        print(f"Warning: {path} not found")
        return {}
    answers = {}
    for line in path.read_text().strip().split("\n"):
        m = re.match(r"^(\d+)\.\s*(.*)", line)
        if m:
            answers[int(m.group(1))] = m.group(2)
    return answers


def find_failing_puzzles(chapter_id: int) -> list[dict]:
    """Return list of {puzzle, answer_text, error} for puzzles that fail validation."""
    db = SessionLocal()
    answers = load_answers(chapter_id)
    puzzles = (
        db.query(Puzzle)
        .filter(Puzzle.chapter_id == chapter_id, Puzzle.verified == 1)
        .order_by(Puzzle.puzzle_number)
        .all()
    )

    failures = []
    for p in puzzles:
        answer = answers.get(p.puzzle_number)
        if not answer:
            continue

        uci_line = parse_solution_to_uci(p.fen, answer)
        if uci_line is None:
            # Figure out where it fails for the error message
            error = diagnose_failure(p.fen, answer)
            failures.append({
                "num": p.puzzle_number,
                "fen": p.fen,
                "turn": p.turn,
                "page": p.pdf_page,
                "solution_san": p.solution_san,
                "answer": answer,
                "error": error,
            })

    db.close()
    return failures


def diagnose_failure(fen: str, answer: str) -> str:
    """Try to extract moves and find where validation breaks."""
    try:
        from extraction import (
            get_gemini_client, SOLUTION_MOVE_EXTRACTION_PROMPT,
            parse_json_from_text, GEMINI_MODEL,
        )
        from google.genai import types

        client = get_gemini_client()
        prompt = SOLUTION_MOVE_EXTRACTION_PROMPT.format(solution_text=answer)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[types.Content(parts=[types.Part.from_text(text=prompt)])],
        )
        san_moves = parse_json_from_text(response.text, list)
        if not san_moves:
            return "LLM returned no moves"

        board = chess.Board(fen)
        for i, san in enumerate(san_moves):
            clean = san.strip().rstrip("!?")
            try:
                move = board.parse_san(clean)
                board.push(move)
            except Exception as e:
                legal = [board.san(m) for m in list(board.legal_moves)[:8]]
                return (
                    f"Move {i+1} \"{clean}\" is illegal. "
                    f"Extracted sequence: {san_moves}. "
                    f"Legal moves at failure: {legal}"
                )
        return "Unknown failure"
    except Exception as e:
        return f"Diagnosis error: {e}"


def render_html(failures: list[dict], output_path: Path):
    """Generate the HTML review page."""
    cards = []
    for f in failures:
        turn_class = "turn-w" if f["turn"] == "w" else "turn-b"
        turn_label = "White" if f["turn"] == "w" else "Black"
        fen_img = f["fen"].split(" ")[0]  # just the board part for the image URL

        cards.append(f"""
<div class="puzzle">
  <div class="puzzle-header">
    <span class="puzzle-num">#{f['num']}</span>
    <span class="puzzle-page">PDF page {f['page'] or '?'}</span>
  </div>
  <div class="board-container">
    <img src="https://fen2image.chessvision.ai/{fen_img}" width="360" alt="Puzzle {f['num']} board">
  </div>
  <div class="fen">FEN: {f['fen']}</div>
  <div class="field"><span class="label">Turn:</span> <span class="turn {turn_class}">{turn_label}</span></div>
  <div class="field"><span class="label">Stored solution_san:</span> {f['solution_san']}</div>
  <div class="answer">
    <span class="label">Book answer:</span><br>
    {f['answer']}
  </div>
  <div class="error">Fail: {f['error']}</div>
  <textarea rows="2" placeholder="Corrected FEN..."></textarea>
</div>""")

    count = len(failures)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Chapter 1 — Failed FEN Verification</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; max-width: 900px; margin: 0 auto; padding: 20px; }}
  h1 {{ color: #7c3aed; text-align: center; }}
  .intro {{ text-align: center; color: #aaa; margin-bottom: 32px; font-size: 0.95rem; }}
  .puzzle {{ background: #16213e; border-radius: 12px; padding: 20px; margin-bottom: 24px; border-left: 4px solid #e74c3c; }}
  .puzzle-header {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }}
  .puzzle-num {{ font-size: 1.3rem; font-weight: 700; color: #facc15; }}
  .puzzle-page {{ color: #888; font-size: 0.85rem; }}
  .board-container {{ text-align: center; margin: 16px 0; }}
  .fen {{ font-family: monospace; font-size: 0.8rem; color: #888; word-break: break-all; margin: 8px 0; }}
  .field {{ margin: 6px 0; }}
  .label {{ color: #7c3aed; font-weight: 600; font-size: 0.85rem; }}
  .answer {{ background: #0f3460; padding: 10px 14px; border-radius: 8px; margin-top: 10px; line-height: 1.5; }}
  .error {{ color: #f87171; font-size: 0.85rem; margin-top: 8px; }}
  .turn {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }}
  .turn-w {{ background: #fff; color: #000; }}
  .turn-b {{ background: #333; color: #fff; }}
  textarea {{ width: 100%; font-family: monospace; font-size: 0.85rem; background: #0a0a1a; color: #4ade80; border: 1px solid #333; border-radius: 6px; padding: 8px; margin-top: 6px; resize: vertical; }}
  .success {{ text-align: center; color: #4ade80; font-size: 1.2rem; margin-top: 40px; }}
</style>
</head>
<body>

<h1>Failed FEN Verification — Chapter 1</h1>
<p class="intro">
  {count} puzzle{'s' if count != 1 else ''} where the stored FEN doesn't match the book's answer.<br>
  Compare each board against the PDF, then paste the corrected FEN in the box.
</p>

{"".join(cards) if cards else '<div class="success">All puzzles validate! No corrections needed.</div>'}

<script>
document.querySelectorAll('textarea').forEach((ta, i) => {{
  const key = 'fen_fix_gen_' + i;
  ta.value = localStorage.getItem(key) || '';
  ta.addEventListener('input', () => localStorage.setItem(key, ta.value));
}});
</script>

</body>
</html>"""

    output_path.write_text(html)
    print(f"Wrote {output_path} ({count} failing puzzle{'s' if count != 1 else ''})")


def main():
    parser = argparse.ArgumentParser(description="Generate HTML review page for failing FENs")
    parser.add_argument("--chapter", type=int, default=1)
    parser.add_argument("-o", "--output", type=str,
                        default=str(Path(__file__).resolve().parent.parent / "failed_fens.html"))
    args = parser.parse_args()

    print(f"Finding failing puzzles for chapter {args.chapter}...")
    failures = find_failing_puzzles(args.chapter)
    render_html(failures, Path(args.output))


if __name__ == "__main__":
    main()
