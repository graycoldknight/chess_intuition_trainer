import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database import SessionLocal
from models import Puzzle

CHAPTER_ID = 1
DUMMY_PUZZLE_ID = 1  # test fixture, not from PDF

db = SessionLocal()
puzzles = (
    db.query(Puzzle)
    .filter(Puzzle.chapter_id == CHAPTER_ID, Puzzle.id != DUMMY_PUZZLE_ID)
    .order_by(Puzzle.puzzle_number)
    .all()
)

questions = [{"puzzle_number": p.puzzle_number, "fen": p.fen, "turn": p.turn} for p in puzzles]
answers = [
    {
        "puzzle_number": p.puzzle_number,
        "solution_san": p.solution_san,
        "solution_uci": p.solution_uci,
        "solution_uci_line": p.solution_uci_line or [p.solution_uci],
        "solution_line": p.solution_line,
    }
    for p in puzzles
]

out_dir = os.path.join(os.path.dirname(__file__), "..")
with open(os.path.join(out_dir, "chapter1_questions.json"), "w") as f:
    json.dump(questions, f, indent=2)
with open(os.path.join(out_dir, "chapter1_answers.json"), "w") as f:
    json.dump(answers, f, indent=2)

print(f"Exported {len(puzzles)} puzzles.")
db.close()
