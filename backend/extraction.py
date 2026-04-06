"""
PDF -> FEN extraction pipeline for Polgar's Chess Tactics for Champions.
Uses PyMuPDF to render pages, Gemini 2.0 Flash for vision extraction, python-chess to validate.
"""

import os
import json
import logging
import fitz  # PyMuPDF
import chess
import io
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# LLM config
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
PDF_PATH = os.getenv(
    "POLGAR_PDF_PATH",
    str(Path(__file__).resolve().parent.parent / "chess_tactics_for_champions_by_Polgar.pdf"),
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
    Returns list of (page_number, pil_image_bytes) tuples.
    """
    doc = fitz.open(pdf_path)
    images = []
    for page_num in range(start_page - 1, min(end_page, len(doc))):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
        img_bytes = pix.tobytes("png")
        images.append((page_num + 1, img_bytes))
    doc.close()
    return images


BULK_EXTRACTION_PROMPT = """Analyze this page from Susan Polgar's "Chess Tactics for Champions".
This page contains several chess diagrams. 

For each diagram:
1. Identify the puzzle number.
2. Determine if it's White or Black to move (shown below the diagram).
3. Systematically list the pieces on the board by square.
4. Provide the FEN string.

### EXAMPLES FROM THIS BOOK:
Puzzle 1: 8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1
Puzzle 2: r2qk2r/ppp2ppp/2np4/8/3Pn3/2P1B3/PP2NPPP/R2QK2R w KQkq - 0 1
Puzzle 50: 8/k7/p1p5/6p1/4p3/2B3P1/P4P1P/R5K1 w - - 0 1 (White moves Bd4+ to pin/skew)
Puzzle 51: k7/7R/8/8/8/8/2B5/K7 w - - 0 1 (White moves Be4+ to pin/skew)

Return a JSON array of objects:
[
  {"puzzle_number": 1, "side_to_move": "w", "fen": "FEN_HERE"},
  ...
]

Provide your reasoning (piece list) first, then the JSON block wrapped in ```json code blocks."""


SOLUTION_EXTRACTION_PROMPT = """You are extracting chess puzzle solutions from Susan Polgar's "Chess Tactics for Champions" book.
Extract the solution for each puzzle number visible on this page.

For each solution, extract:
1. The puzzle number
2. The first move only in Standard Algebraic Notation (SAN)
3. The full solution text

Return a JSON array:
[
  {"puzzle_number": 1, "first_move_san": "Nf6+", "full_solution": "1. Nf6+ Kg7 2. Qh7#"},
  ...
]
Return ONLY the JSON array."""


def extract_diagrams_from_page(page_image_bytes: bytes, client=None) -> list[dict]:
    """Extract diagrams using Gemini Flash."""
    if client is None:
        client = get_gemini_client()

    from google.genai import types
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(parts=[
                types.Part.from_bytes(data=page_image_bytes, mime_type="image/png"),
                types.Part.from_text(text=BULK_EXTRACTION_PROMPT),
            ])
        ],
    )

    return parse_json_from_text(response.text, list)


def extract_solutions_from_page(page_image_bytes: bytes, client=None) -> list[dict]:
    """Extract solutions from a page image."""
    if client is None:
        client = get_gemini_client()

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

    return parse_json_from_text(response.text, list)


def refine_puzzle(page_image_bytes: bytes, puzzle_data: dict, client=None) -> dict:
    """Asks the LLM to re-examine a specific puzzle that failed validation."""
    if client is None:
        client = get_gemini_client()

    from google.genai import types
    prompt = f"""I extracted puzzle #{puzzle_data['puzzle_number']} from this page, but it's incorrect.
Extracted FEN: {puzzle_data['fen']}
Intended Move: {puzzle_data['solution_san']}
Error: {puzzle_data['error']}

Please re-examine diagram #{puzzle_data['puzzle_number']} on the provided page image.
Look extremely closely at every square.
Common mistakes: missing pawns, confusing White/Black pieces, off-by-one errors.

Return the CORRECTED JSON for this puzzle:
{{
  "puzzle_number": {puzzle_data['puzzle_number']},
  "side_to_move": "{puzzle_data['turn']}",
  "fen": "CORRECT_FEN_HERE"
}}
Return ONLY the JSON."""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Content(parts=[
                types.Part.from_bytes(data=page_image_bytes, mime_type="image/png"),
                types.Part.from_text(text=prompt),
            ])
        ],
    )

    ref_data = parse_json_from_text(response.text, dict)
    if ref_data and "fen" in ref_data:
        new_p = puzzle_data.copy()
        new_p["fen"] = ref_data["fen"]
        if "side_to_move" in ref_data:
            new_p["turn"] = ref_data["side_to_move"].lower()
        return new_p
    return puzzle_data


def parse_json_from_text(text: str, expected_type=list):
    """Robust JSON extraction from LLM text."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    
    start_char = "[" if expected_type == list else "{"
    end_char = "]" if expected_type == list else "}"
    
    if start_char in text:
        text = text[text.find(start_char):]
        if end_char in text:
            text = text[:text.rfind(end_char)+1]
            
    try:
        return json.loads(text)
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        return [] if expected_type == list else {}


def validate_puzzle(p: dict) -> dict:
    """Validate FEN and move legality."""
    p["valid"] = False
    p["error"] = None
    p["solution_uci"] = None
    p["extraction_confidence"] = 0.0

    if not p.get("solution_san"):
        p["error"] = "no_solution_found"
        return p

    try:
        board = chess.Board(p["fen"])
        expected_turn = chess.WHITE if p["turn"] == "w" else chess.BLACK
        if board.turn != expected_turn:
            p["error"] = f"turn_mismatch: fen says {'w' if board.turn == chess.WHITE else 'b'}, expected {p['turn']}"
        
        move = board.parse_san(p["solution_san"])
        p["solution_uci"] = move.uci()
        p["valid"] = True
        p["extraction_confidence"] = 1.0
        p["error"] = None
    except Exception as e:
        p["error"] = str(e)
        p["extraction_confidence"] = 0.0
    
    return p


def merge_and_validate(diagrams: list[dict], solutions: list[dict]) -> list[dict]:
    """Initial merge of diagrams and solutions."""
    solution_map = {s["puzzle_number"]: s for s in solutions if "puzzle_number" in s}
    merged = []

    for diag in diagrams:
        pnum = diag.get("puzzle_number")
        if not pnum: continue

        sol = solution_map.get(pnum)
        p = {
            "puzzle_number": pnum,
            "fen": diag.get("fen"),
            "turn": diag.get("side_to_move"),
            "solution_san": sol.get("first_move_san") if sol else None,
            "solution_line": sol.get("full_solution") if sol else None,
        }
        merged.append(validate_puzzle(p))

    return merged


def extract_chapter(chapter_id: int, db_session, max_pages: Optional[int] = None, clear_existing: bool = False) -> dict:
    """Full extraction pipeline for a chapter."""
    from models import Chapter, Puzzle

    if clear_existing:
        db_session.query(Puzzle).filter_by(chapter_id=chapter_id).delete()
        db_session.commit()
        print(f"  Cleared existing puzzles for chapter {chapter_id}")

    chapter = db_session.query(Chapter).get(chapter_id)
    if not chapter:
        raise ValueError(f"Chapter {chapter_id} not found")

    chapter.extraction_status = "extracting"
    db_session.commit()

    try:
        end_page = chapter.end_page
        if max_pages:
            end_page = min(chapter.start_page + max_pages - 1, chapter.end_page)
            
        page_images = extract_page_images(chapter.start_page, end_page)
        client = get_gemini_client()
        all_puzzles = []
        
        for i, (page_num, img_bytes) in enumerate(page_images, 1):
            print(f"  Page {page_num} ({i}/{len(page_images)})...", flush=True)
            diagrams = extract_diagrams_from_page(img_bytes, client)
            solutions = extract_solutions_from_page(img_bytes, client)
            
            for d in diagrams:
                d["pdf_page"] = page_num
            
            page_merged = merge_and_validate(diagrams, solutions)
            
            # Refine
            for idx, p in enumerate(page_merged):
                if not p["valid"] and p["error"] != "no_solution_found":
                    print(f"    - Refining puzzle {p['puzzle_number']}...", flush=True)
                    refined = refine_puzzle(img_bytes, p, client)
                    page_merged[idx] = validate_puzzle(refined)

            print(f"    -> {len(diagrams)} diagrams, {len(solutions)} solutions", flush=True)
            all_puzzles.extend(page_merged)

        # Final deduplication
        unique_puzzles = {}
        for p in all_puzzles:
            pnum = p["puzzle_number"]
            if pnum not in unique_puzzles or (p["valid"] and not unique_puzzles[pnum]["valid"]):
                unique_puzzles[pnum] = p
        
        final_list = list(unique_puzzles.values())

        stored = 0
        for p in final_list:
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
                error_message=p.get("error")
            )
            db_session.add(puzzle)
            stored += 1

        db_session.commit()
        
        total_puzzles = db_session.query(Puzzle).filter_by(chapter_id=chapter_id).count()
        chapter.puzzle_count = total_puzzles
        chapter.extraction_status = "review"
        db_session.commit()

        return {
            "chapter_id": chapter_id,
            "puzzles_found": len(final_list),
            "puzzles_stored": stored,
            "valid": sum(1 for p in final_list if p["valid"]),
            "invalid": sum(1 for p in final_list if not p["valid"]),
        }

    except Exception as e:
        db_session.rollback()
        chapter = db_session.query(Chapter).get(chapter_id)
        if chapter:
            chapter.extraction_status = "pending"
            db_session.commit()
        raise


# ---------------------------------------------------------------------------
# Multi-move solution parsing (Phase 9)
# ---------------------------------------------------------------------------

SOLUTION_MOVE_EXTRACTION_PROMPT = """Extract ONLY the MAIN LINE chess moves from this solution text, in order.
Return a JSON array of SAN (Standard Algebraic Notation) moves, alternating between the two sides.
Include ALL moves played by BOTH sides in the MAIN LINE ONLY.
Do NOT include move numbers, commentary, or annotations.

IMPORTANT: Many solutions mention SIDE VARIATIONS or ALTERNATIVE LINES (e.g. "after 1... Qd4+",
"the immediate 1. Qg3 is not so successful because of 1... Rb6", "On the other hand 1. Qe4+ is not sufficient").
IGNORE these — extract ONLY the primary recommended sequence of moves.

Examples:
- Input: "1. Rf6+ (intermediate move) Kg7 2. Rb6 forks both Black bishops."
  Output: ["Rf6+", "Kg7", "Rb6"]
- Input: "The right answer is: 1. Qxc7+ Kxc7 2. Nd5+."
  Output: ["Qxc7+", "Kxc7", "Nd5+"]
- Input: "1. f8=Q+! Kxf8 and now 2. Bxd6+."
  Output: ["f8=Q+", "Kxf8", "Bxd6+"]
- Input: "1... e5 is the best reply."
  Output: ["e5"]
- Input: "Here White needs to find a pretty queen sacrifice: 1. Qxe7! Rxe7 2. Nf6+. It is also important to see that after 1.... Qd4+ White saves the queen, by blocking the check with 2. Qe3."
  Output: ["Qxe7", "Rxe7", "Nf6+"]
- Input: "White wins a rook with 1. Qxf6! gxf6 2. Nf7+. The immediate 1. Qg3 is not so successful because of 1... Rb6."
  Output: ["Qxf6", "gxf6", "Nf7+"]

Solution text: {solution_text}

Return ONLY the JSON array, nothing else."""


def parse_solution_to_uci(fen: str, solution_text: str, client=None) -> list[str] | None:
    """
    Parse prose solution text into a validated list of UCI move strings.

    1. Use Gemini to extract the SAN move sequence from the prose.
    2. Validate each move with python-chess against the FEN.
    3. Return list of UCI strings, or None on failure.
    """
    if not solution_text or not fen:
        return None

    # Step 1: Extract SAN moves via LLM
    try:
        if client is None:
            client = get_gemini_client()

        from google.genai import types
        prompt = SOLUTION_MOVE_EXTRACTION_PROMPT.format(solution_text=solution_text)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Content(parts=[
                    types.Part.from_text(text=prompt),
                ])
            ],
        )
        san_moves = parse_json_from_text(response.text, list)
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        return None

    if not san_moves:
        return None

    # Step 2: Validate each move with python-chess
    try:
        board = chess.Board(fen)
        uci_moves = []
        for san in san_moves:
            # Clean annotation characters that python-chess handles but just in case
            clean_san = san.strip().rstrip("!?")
            move = board.parse_san(clean_san)
            uci_moves.append(move.uci())
            board.push(move)
        return uci_moves
    except Exception as e:
        logger.error(f"Move validation failed: {e}")
        return None
