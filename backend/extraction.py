"""
PDF -> FEN extraction pipeline for Polgar's Chess Tactics for Champions.
Uses PyMuPDF to render pages, vision LLM to extract positions, python-chess to validate.
"""

import os
import json
import logging
import fitz  # PyMuPDF
import chess
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# LLM config
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
PDF_PATH = os.getenv(
    "POLGAR_PDF_PATH",
    str(Path(__file__).parent.parent / "chess_tactics_for_champions_by_Polgar.pdf"),
)


def get_gemini_client():
    """Get Google Gemini client."""
    try:
        import google.genai as genai
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not set")
        client = genai.Client(api_key=api_key)
        return client
    except ImportError:
        raise ImportError("google-genai package required: pip install google-genai")


def extract_page_images(start_page: int, end_page: int, pdf_path: str = PDF_PATH) -> list:
    """
    Render PDF pages to PIL Images.
    Pages are 0-indexed internally but 1-indexed in the chapters table.
    Returns list of (page_number, pil_image) tuples.
    """
    doc = fitz.open(pdf_path)
    images = []
    # Convert 1-indexed to 0-indexed
    for page_num in range(start_page - 1, min(end_page, len(doc))):
        page = doc[page_num]
        # Render at 2x for better OCR quality
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        images.append((page_num + 1, img_bytes))  # Return 1-indexed page number
    doc.close()
    return images


DIAGRAM_EXTRACTION_PROMPT = """You are a chess diagram analyzer. Look at this page from Susan Polgar's "Chess Tactics for Champions" book.

This page contains chess puzzle diagrams. For each puzzle diagram on this page, extract:
1. The puzzle number (shown above the diagram, e.g., "1.", "2.", etc.)
2. Whether it's "White to move" or "Black to move" (shown below the diagram)
3. The FEN (Forsyth-Edwards Notation) representing the exact position on the board

IMPORTANT FEN rules:
- Read the board from rank 8 (top) to rank 1 (bottom), left to right
- Uppercase = White pieces (K, Q, R, B, N, P), Lowercase = Black pieces (k, q, r, b, n, p)
- Empty squares are counted as numbers (1-8)
- Ranks separated by /
- After the position, add: space, then side to move (w/b), then " - - 0 1" for simplicity

Return a JSON array. If no puzzles are on this page, return [].

Example output:
[
  {"puzzle_number": 1, "side_to_move": "w", "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w - - 0 1"},
  {"puzzle_number": 2, "side_to_move": "b", "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b - - 0 1"}
]

Return ONLY the JSON array, no other text."""


SOLUTION_EXTRACTION_PROMPT = """You are extracting chess puzzle solutions from Susan Polgar's "Chess Tactics for Champions" book.

This page contains solutions to puzzles. Extract the solution for each puzzle number visible.

For each solution, extract:
1. The puzzle number
2. The first move only in Standard Algebraic Notation (SAN), e.g., "Nf6+", "Bxh7+", "Qd8#"
3. The full solution text as written in the book

Return a JSON array:
[
  {"puzzle_number": 1, "first_move_san": "Nf6+", "full_solution": "1. Nf6+ Kg7 2. Qh7#"},
  {"puzzle_number": 2, "first_move_san": "Bxh7+", "full_solution": "1. Bxh7+ Kxh7 2. Ng5+"}
]

Return ONLY the JSON array, no other text."""


def extract_diagrams_from_page(page_image_bytes: bytes, client=None) -> list[dict]:
    """
    Send a page image to vision LLM and extract puzzle diagrams.
    Returns list of dicts: [{puzzle_number, side_to_move, fen}, ...]
    """
    if client is None:
        client = get_gemini_client()

    import google.genai as genai
    from google.genai import types

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(parts=[
                types.Part.from_bytes(data=page_image_bytes, mime_type="image/png"),
                types.Part.from_text(text=DIAGRAM_EXTRACTION_PROMPT),
            ])
        ],
    )

    return parse_diagram_response(response.text)


def extract_solutions_from_page(page_image_bytes: bytes, client=None) -> list[dict]:
    """
    Send a solution page image to vision LLM and extract solutions.
    Returns list of dicts: [{puzzle_number, first_move_san, full_solution}, ...]
    """
    if client is None:
        client = get_gemini_client()

    import google.genai as genai
    from google.genai import types

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(parts=[
                types.Part.from_bytes(data=page_image_bytes, mime_type="image/png"),
                types.Part.from_text(text=SOLUTION_EXTRACTION_PROMPT),
            ])
        ],
    )

    return parse_solution_response(response.text)


def parse_diagram_response(llm_text: str) -> list[dict]:
    """
    Parse vision LLM output into puzzle dicts.
    Handles markdown code fences and raw JSON.
    """
    text = llm_text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (``` markers)
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse diagram response: {text[:200]}")
        return []

    if not isinstance(data, list):
        return []

    results = []
    for item in data:
        if all(k in item for k in ("puzzle_number", "side_to_move", "fen")):
            results.append({
                "puzzle_number": int(item["puzzle_number"]),
                "side_to_move": item["side_to_move"].lower(),
                "fen": item["fen"].strip(),
            })
    return results


def parse_solution_response(llm_text: str) -> list[dict]:
    """
    Parse solution LLM output into solution dicts.
    """
    text = llm_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse solution response: {text[:200]}")
        return []

    if not isinstance(data, list):
        return []

    results = []
    for item in data:
        san = item.get("first_move_san")
        if item.get("puzzle_number") is not None and san:
            results.append({
                "puzzle_number": int(item["puzzle_number"]),
                "first_move_san": san.strip(),
                "full_solution": item.get("full_solution", ""),
            })
    return results


def merge_and_validate(diagrams: list[dict], solutions: list[dict]) -> list[dict]:
    """
    Cross-reference diagrams with solutions.
    Validates solution move is legal in extracted FEN using python-chess.
    Converts SAN to UCI.
    Returns list of merged puzzle dicts with validation status.
    """
    solution_map = {s["puzzle_number"]: s for s in solutions}
    merged = []

    for diag in diagrams:
        pnum = diag["puzzle_number"]
        sol = solution_map.get(pnum)

        result = {
            "puzzle_number": pnum,
            "fen": diag["fen"],
            "turn": diag["side_to_move"],
            "solution_san": sol["first_move_san"] if sol else None,
            "solution_uci": None,
            "solution_line": sol["full_solution"] if sol else None,
            "extraction_confidence": 0.0,
            "valid": False,
            "error": None,
        }

        if not sol:
            result["error"] = "no_solution_found"
            merged.append(result)
            continue

        # Validate FEN and solution move
        try:
            board = chess.Board(result["fen"])
        except ValueError as e:
            result["error"] = f"invalid_fen: {e}"
            merged.append(result)
            continue

        # Verify turn matches
        expected_turn = chess.WHITE if result["turn"] == "w" else chess.BLACK
        if board.turn != expected_turn:
            result["error"] = f"turn_mismatch: fen says {'w' if board.turn == chess.WHITE else 'b'}, expected {result['turn']}"

        # Try to parse and validate the solution move
        try:
            move = board.parse_san(sol["first_move_san"])
            result["solution_uci"] = move.uci()
            result["valid"] = True
            result["extraction_confidence"] = 1.0
            result["error"] = None
        except (chess.IllegalMoveError, chess.InvalidMoveError, chess.AmbiguousMoveError) as e:
            result["error"] = f"illegal_move: {sol['first_move_san']} - {e}"
            result["extraction_confidence"] = 0.0

        merged.append(result)

    return merged


def extract_chapter(chapter_id: int, db_session) -> dict:
    """
    Full extraction pipeline for a chapter.
    1. Get page range from chapters table
    2. Render pages to images
    3. Extract diagrams and solutions via vision LLM
    4. Merge and validate
    5. Store puzzles in database
    Returns summary dict.
    """
    from models import Chapter, Puzzle

    chapter = db_session.query(Chapter).get(chapter_id)
    if not chapter:
        raise ValueError(f"Chapter {chapter_id} not found")

    chapter.extraction_status = "extracting"
    db_session.commit()

    try:
        # Render pages
        page_images = extract_page_images(chapter.start_page, chapter.end_page)

        # Extract diagrams from puzzle pages and solutions from solution pages
        client = get_gemini_client()
        all_diagrams = []
        all_solutions = []

        total_pages = len(page_images)
        for i, (page_num, img_bytes) in enumerate(page_images, 1):
            print(f"  Page {page_num} ({i}/{total_pages})...", flush=True)
            diagrams = extract_diagrams_from_page(img_bytes, client)
            solutions = extract_solutions_from_page(img_bytes, client)
            for d in diagrams:
                d["pdf_page"] = page_num
            all_diagrams.extend(diagrams)
            all_solutions.extend(solutions)
            print(f"    -> {len(diagrams)} diagrams, {len(solutions)} solutions", flush=True)

        # Merge and validate
        merged = merge_and_validate(all_diagrams, all_solutions)

        # Store in database
        stored = 0
        for p in merged:
            existing = db_session.query(Puzzle).filter_by(
                chapter_id=chapter_id, puzzle_number=p["puzzle_number"]
            ).first()
            if existing:
                continue

            puzzle = Puzzle(
                chapter_id=chapter_id,
                puzzle_number=p["puzzle_number"],
                fen=p["fen"],
                turn=p["turn"],
                solution_san=p["solution_san"] or "",
                solution_uci=p["solution_uci"] or "",
                solution_line=p.get("solution_line"),
                pdf_page=p.get("pdf_page"),
                verified=0,
                extraction_confidence=p["extraction_confidence"],
            )
            db_session.add(puzzle)
            stored += 1

        chapter.puzzle_count = stored
        chapter.extraction_status = "review"
        db_session.commit()

        return {
            "chapter_id": chapter_id,
            "diagrams_found": len(all_diagrams),
            "solutions_found": len(all_solutions),
            "puzzles_stored": stored,
            "valid": sum(1 for p in merged if p["valid"]),
            "invalid": sum(1 for p in merged if not p["valid"]),
        }

    except Exception as e:
        chapter.extraction_status = "pending"
        db_session.commit()
        raise
