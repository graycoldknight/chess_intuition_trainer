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

=== SECTION 1: TASK ===
For each diagram:
1. Identify the puzzle number (printed above or below the diagram).
2. Determine if it's White or Black to move (shown below the diagram as "White to move" or "Black to move").
3. Systematically list every piece on the board, rank by rank from rank 8 down to rank 1.
4. Produce the FEN piece-placement string, then the full FEN.

=== SECTION 2: COMMON MISTAKES — READ CAREFULLY ===

MISTAKE 1 — Edge blindness (rank 8 / file h):
Pieces on the top rank (rank 8) or rightmost file (h) are often missed.
WRONG: "8/p1r1k2r/1p5q/..." (rook on h7 missing from rank 8)
RIGHT: "7r/p1r1k3/1p5q/..." (rook correctly placed on h8)
→ Always scan rank 8 and file h last as a double-check.

MISTAKE 2 — Piece misidentification (bishop ↔ queen, knight ↔ bishop):
Dark-square bishops can look like queens at low resolution.
WRONG: "8/1q6/p6k/..." (queen on b7, should be bishop)
RIGHT: "8/1b6/p6k/..." (bishop on b7)
→ Count the legs: bishop has diagonal lines, queen has lines in all 8 directions.

MISTAKE 3 — Rank shift (off-by-one):
All pieces appear one rank higher or lower than their actual position.
WRONG: "r5k1/ppq2p1p/2n3p1/8/..." (king on g8, rook on a8)
RIGHT: "r7/ppq2pkp/2n3p1/8/..." (king on g7, rook on a8 on rank 8)
→ Count ranks from the bottom (rank 1) up, not from the top.

MISTAKE 4 — Missing pawns:
Pawns are small and often missed, especially in clusters.
WRONG: "r2qk2r/ppp2pp/2np4/8/..." (missing a pawn on f7)
RIGHT: "r2qk2r/ppp2ppp/2np4/8/..." (pawn on f7 present)
→ Count every pawn on each file explicitly.

MISTAKE 5 — Side to move error:
The text below the diagram always says "White to move" or "Black to move".
Use "w" for White, "b" for Black. Do NOT guess from material count.

=== SECTION 3: EXAMPLES FROM THIS BOOK ===

Puzzle 1 (White to move, fork): 8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1
  White: Rook f3, Pawns d3 e4 g4 h3; Black: Bishops b7 b2, King h6, Pawns a6 e5 g5 h4
  → Note two Black bishops, one on b7 (rank 7) and one on b2 (rank 2).

Puzzle 2 (White to move): r2qk2r/ppp2ppp/2np4/8/3Pn3/2P1B3/PP2NPPP/R2QK2R w KQkq - 0 1
  White has castling rights KQkq — check the castling field carefully.

Puzzle 4 (Black to move): 2b1rk2/pp3ppp/2p5/3pP3/3P4/2P5/PP4PP/R4RK1 b - - 0 1
  Black to move — side_to_move is "b".

Puzzle 7 (White to move): r4rk1/pp3ppp/2p5/8/3P4/2P5/PP4PP/R4RK1 w - - 0 1

Puzzle 9 (White to move): 8/p1r1k2r/1p5q/4Pp2/1P1Q2p1/6P1/3R1PK1/5R2 w - - 0 1
  Wait — is there a rook on h7? Check rank 7, file h carefully.
  CORRECT: 8/p1r1k2r/1p5q/4Pp2/1P1Q2p1/6P1/3R1PK1/5R2 w - - 0 1

Puzzle 12 (White to move): 4r1k1/p4ppp/1pp5/8/3P4/8/PP4PP/4R1K1 w - - 0 1

Puzzle 17 (White to move, promotion): 8/r4Pk1/3p2pp/8/p4B2/r4NP1/6KP/3R4 w - - 0 1
  White pawn on f7 can promote — the pawn is on f7 (rank 7), NOT f8.

Puzzle 29 (Black to move): 1r6/5ppk/p6p/4p3/2B1P3/5P1P/1r4PK/8 b - - 0 1
  Black to move. Rooks on b8 and b2.

Puzzle 34 (White to move, promotion): 8/r4Pk1/3p2pp/8/p4B2/r4NP1/6KP/3R4 w - - 0 1

Puzzle 36 (White to move): 5rk1/pp3ppp/2p5/8/3P4/2P5/PP4PP/5RK1 w - - 0 1

Puzzle 39 (White to move): 8/pp2kppp/2p5/8/3P4/8/PP3PPP/4K3 w - - 0 1

Puzzle 46 (White to move): r5k1/ppq2p1p/2n3p1/8/3N3r/8/PP1Q1PPP/R4RK1 w - - 0 1
  Rook on h4 (rank 4), NOT h8.

Puzzle 49 (Black to move): 8/k7/p1p5/6p1/4p3/2B3P1/P4P1P/R5K1 b - - 0 1
  Black king on a7, pawns a6 c6 g5 e4; White bishop c3.

=== SECTION 4: OUTPUT FORMAT ===

Return a JSON array of objects:
[
  {"puzzle_number": 1, "side_to_move": "w", "fen": "FEN_HERE"},
  ...
]

Provide your reasoning (piece list rank by rank) first, then the JSON block wrapped in ```json code blocks."""


SOLUTION_EXTRACTION_PROMPT = """You are extracting chess puzzle solutions from Susan Polgar's "Chess Tactics for Champions" book.
Extract the solution for each puzzle number visible on this page.

For each solution, extract:
1. The puzzle number
2. The first move only in Standard Algebraic Notation (SAN)
3. The full solution text (main line only — ignore side variations and commentary)

IMPORTANT: The full solution text must be the MAIN LINE only.
- Ignore commentary like "It would be a blunder to grab..."
- Ignore alternative lines like "The immediate 1. Qg3 is not so successful because..."
- Include ALL moves in the main line (both sides)

### EXAMPLES:

Input page snippet: "1. Rf6+ (intermediate move) Kg7 2. Rb6 forks both Black bishops."
→ {"puzzle_number": 1, "first_move_san": "Rf6+", "full_solution": "1. Rf6+ Kg7 2. Rb6"}

Input page snippet: "Look for the unprotected piece on c5! 1. Bxe6 fxe6 2. Qh5+."
→ {"puzzle_number": 3, "first_move_san": "Bxe6", "full_solution": "1. Bxe6 fxe6 2. Qh5+"}

Input page snippet: "the f7 pawn can be used in a very beneficial way: 1. f8=Q+! Kxf8 and now 2. Bxd6+."
→ {"puzzle_number": 34, "first_move_san": "f8=Q+", "full_solution": "1. f8=Q+ Kxf8 2. Bxd6+"}

Input page snippet: "Here White needs to find a pretty queen sacrifice: 1. Qxe7! Rxe7 2. Nf6+. It is also important to see that after 1.... Qd4+ White saves the queen, by blocking the check with 2. Qe3."
→ first_move_san: "Qxe7", full_solution: "1. Qxe7 Rxe7 2. Nf6+"  (ignore the alternative variation)

Input page snippet: "White wins a rook with 1. Qxf6! gxf6 2. Nf7+. The immediate 1. Qg3 is not so successful because of 1... Rb6."
→ first_move_san: "Qxf6", full_solution: "1. Qxf6 gxf6 2. Nf7+"  (ignore "The immediate 1. Qg3..." side line)

Input page snippet: "1... e5 is the best reply."
→ first_move_san: "e5", full_solution: "1... e5"

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


def generate_correction_hint(fen: str, solution_san: str, error: str) -> str:
    """
    Diagnose WHY a move is illegal and return a specific natural-language hint
    for the LLM to use when re-examining the diagram.

    Uses python-chess to identify:
    - Target square empty for a capture move
    - Wrong side to move
    - No piece of the right type can reach the target
    """
    try:
        board = chess.Board(fen)
    except Exception:
        return f"FEN is invalid: {fen}"

    # Strip annotation characters
    clean_san = solution_san.strip().rstrip("!?+#")

    # Check side to move
    # Try to detect if this looks like a Black move on a White-to-move board or vice versa
    # We do this by checking if the clean_san is parseable after flipping turn
    try:
        board.parse_san(clean_san)
        # If it parses without error, the error is something else
        return f"Move {solution_san} parsed OK but failed validation: {error}"
    except Exception:
        pass

    # Detect wrong turn by seeing if the move parses on the other side
    flipped = chess.Board(fen)
    flipped.turn = chess.BLACK if board.turn == chess.WHITE else chess.WHITE
    try:
        flipped.parse_san(clean_san)
        actual_turn = "White" if board.turn == chess.WHITE else "Black"
        expected_turn = "Black" if board.turn == chess.WHITE else "White"
        return (
            f"FEN says {actual_turn} to move, but {solution_san} is a {expected_turn} move. "
            f"Check the side-to-move field in the FEN."
        )
    except Exception:
        pass

    # Detect capture on empty square
    is_capture = "x" in clean_san
    if is_capture:
        # Extract target square from SAN: last two chars that look like a square
        import re
        squares = re.findall(r"[a-h][1-8]", clean_san)
        if squares:
            target_sq = chess.parse_square(squares[-1])
            piece_at_target = board.piece_at(target_sq)
            if piece_at_target is None:
                sq_name = chess.square_name(target_sq)
                return (
                    f"{solution_san} is a capture move, but {sq_name} is empty in the extracted FEN. "
                    f"There must be a piece on {sq_name} — re-examine the diagram carefully."
                )
            elif piece_at_target.color == board.turn:
                sq_name = chess.square_name(target_sq)
                return (
                    f"{solution_san} tries to capture on {sq_name}, but the piece there belongs "
                    f"to the side that's moving (can't capture own pieces). Check piece colors."
                )

    # Detect no piece of right type can reach target
    import re
    squares = re.findall(r"[a-h][1-8]", clean_san)
    if squares:
        target_sq_name = squares[-1]
        # Check if there are ANY legal moves to that square
        target_sq = chess.parse_square(target_sq_name)
        legal_to_target = [m for m in board.legal_moves if m.to_square == target_sq]
        if not legal_to_target:
            return (
                f"No legal move can reach {target_sq_name} from the current position. "
                f"The FEN may be missing a piece or have it on the wrong square."
            )

    return f"Move {solution_san} is illegal in this position: {error}"


def _build_refinement_prompt(puzzle_data: dict, correction_hint: str, attempt: int = 1) -> str:
    """Build the prompt for a refinement attempt."""
    urgency = "" if attempt == 1 else (
        "\n\nThis is your SECOND attempt. The first correction still failed. "
        "Be extremely methodical — count every piece on every square from rank 8 down to rank 1."
    )
    return f"""I extracted puzzle #{puzzle_data['puzzle_number']} from this page, but the extracted FEN is incorrect.

Extracted FEN: {puzzle_data['fen']}
Book solution (first move): {puzzle_data['solution_san']}
Validation error: {puzzle_data['error']}

SPECIFIC CORRECTION NEEDED: {correction_hint}

Please re-examine diagram #{puzzle_data['puzzle_number']} on the provided page image.
Scan rank 8 and file h carefully (edge pieces are often missed).
Check every pawn — small pieces are easy to miss.
Verify the side to move matches "{'White' if puzzle_data.get('turn') == 'w' else 'Black'} to move" text below the diagram.{urgency}

Return the CORRECTED JSON for this puzzle:
{{
  "puzzle_number": {puzzle_data['puzzle_number']},
  "side_to_move": "{puzzle_data['turn']}",
  "fen": "CORRECT_FEN_HERE"
}}
Return ONLY the JSON."""


def refine_puzzle(page_image_bytes: bytes, puzzle_data: dict, client=None) -> dict:
    """
    Asks the LLM to re-examine a specific puzzle that failed validation.
    Uses solution-constrained correction hints from generate_correction_hint().
    Makes up to 2 attempts; flags with error_message after both fail.
    """
    if client is None:
        client = get_gemini_client()

    from google.genai import types

    correction_hint = generate_correction_hint(
        puzzle_data.get("fen", ""),
        puzzle_data.get("solution_san", ""),
        puzzle_data.get("error", ""),
    )

    for attempt in (1, 2):
        prompt = _build_refinement_prompt(puzzle_data, correction_hint, attempt)
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
            validated = validate_puzzle(new_p)
            if validated["valid"]:
                return validated
            # Not valid yet — loop to attempt 2 with same hint
            puzzle_data = validated  # carry updated FEN into next attempt

    # Both attempts failed — flag for manual review
    puzzle_data["error"] = f"NEEDS_REVIEW: {correction_hint}"
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
    solution_map = {}
    for s in solutions:
        if "puzzle_number" not in s:
            continue
        try:
            solution_map[int(s["puzzle_number"])] = s
        except (TypeError, ValueError):
            pass
    merged = []

    for diag in diagrams:
        pnum = diag.get("puzzle_number")
        if not pnum: continue
        try:
            pnum = int(pnum)
        except (TypeError, ValueError):
            continue

        sol = solution_map.get(pnum)
        p = {
            "puzzle_number": pnum,
            "fen": diag.get("fen"),
            "turn": diag.get("side_to_move"),
            "solution_san": sol.get("first_move_san") if sol else None,
            "solution_line": sol.get("full_solution") if sol else None,
            "pdf_page": diag.get("pdf_page"),
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

        # Collect all diagrams and solutions across all pages first,
        # then do a global merge so diagram/solution pairs separated across
        # pages (e.g., diagram section + answer section layout) are matched.
        all_diagrams = []
        all_solutions = []
        page_img_by_num = {}

        for i, (page_num, img_bytes) in enumerate(page_images, 1):
            print(f"  Page {page_num} ({i}/{len(page_images)})...", flush=True)
            diagrams = extract_diagrams_from_page(img_bytes, client)
            solutions = extract_solutions_from_page(img_bytes, client)

            diagrams = [d for d in diagrams if isinstance(d, dict)]
            for d in diagrams:
                d["pdf_page"] = page_num
                page_img_by_num[page_num] = img_bytes

            print(f"    -> {len(diagrams)} diagrams, {len(solutions)} solutions", flush=True)
            all_diagrams.extend(diagrams)
            all_solutions.extend(solutions)

        # Global merge: best solution wins per puzzle number
        merged = merge_and_validate(all_diagrams, all_solutions)

        # Refine invalid puzzles using their original page image
        for idx, p in enumerate(merged):
            if not p["valid"] and p["error"] != "no_solution_found":
                ppage = p.get("pdf_page")
                img_bytes = page_img_by_num.get(ppage)
                if img_bytes:
                    print(f"    - Refining puzzle {p['puzzle_number']}...", flush=True)
                    refined = refine_puzzle(img_bytes, p, client)
                    merged[idx] = validate_puzzle(refined)

        # Final deduplication: prefer valid over invalid for same puzzle number
        unique_puzzles = {}
        for p in merged:
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
# JSON export
# ---------------------------------------------------------------------------

ROOT = str(Path(__file__).resolve().parent.parent)


def extract_chapter_to_json(chapter_id: int, db_session, output_dir: str = ROOT) -> dict:
    """
    Extract a chapter and export chapterN_questions.json + chapterN_answers.json
    in the same format as chapter1_*.json (consumed by import_puzzles.py).

    Returns a quality report dict.
    """
    from models import Puzzle

    # Run extraction
    result = extract_chapter(chapter_id, db_session)

    # Query resulting puzzles from DB
    puzzles = (
        db_session.query(Puzzle)
        .filter_by(chapter_id=chapter_id)
        .order_by(Puzzle.puzzle_number)
        .all()
    )

    questions = []
    answers = []
    needs_review = []

    for p in puzzles:
        questions.append({
            "puzzle_number": p.puzzle_number,
            "fen": p.fen,
            "turn": p.turn,
        })
        answers.append({
            "puzzle_number": p.puzzle_number,
            "solution_san": p.solution_san,
            "solution_uci": p.solution_uci,
            "solution_uci_line": p.solution_uci_line,
            "solution_line": p.solution_line,
        })
        if p.error_message and p.error_message.startswith("NEEDS_REVIEW"):
            needs_review.append(p.puzzle_number)

    q_path = os.path.join(output_dir, f"chapter{chapter_id}_questions.json")
    a_path = os.path.join(output_dir, f"chapter{chapter_id}_answers.json")

    with open(q_path, "w") as f:
        json.dump(questions, f, indent=2)
    with open(a_path, "w") as f:
        json.dump(answers, f, indent=2)

    print(f"  Exported: {q_path}")
    print(f"  Exported: {a_path}")

    valid_count = sum(1 for p in puzzles if not p.error_message or not p.error_message.startswith("NEEDS_REVIEW"))
    return {
        "chapter_id": chapter_id,
        "found": len(puzzles),
        "valid": valid_count,
        "invalid": result.get("invalid", 0),
        "needs_review": needs_review,
        "q_path": q_path,
        "a_path": a_path,
    }


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
