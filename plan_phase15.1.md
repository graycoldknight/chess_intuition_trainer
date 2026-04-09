# Phase 16: Extraction Accuracy — 37% to >90%

## Context

Chapter 2 extraction produced 37% valid puzzles (17/46). The dominant failure mode is "illegal san" (24 puzzles): the FEN is structurally valid but has wrong piece placement, making the book's solution move illegal. The current `refine_puzzle()` anchors on the wrong FEN (shows it to the model and asks for corrections), so the model repeats similar mistakes. We need a fundamentally different approach: **solution-constrained fresh extraction** — use the known-correct solution text to guide FEN extraction without anchoring on the wrong FEN.

**Key decisions:**
- Solution-first: extract solutions (OCR text, ~95% reliable) before FENs, then use solutions as hard constraints during FEN extraction
- Fresh extraction over refinement: do NOT show the wrong FEN to the model — this avoids anchoring bias (the #1 reason `refine_puzzle()` fails)
- Post-processing before API calls: sanitize FEN/SAN to fix trivial failures first (3 puzzles fixed for free)
- Backoff wrapper: Gemini free tier is 15 RPM — every API call needs rate-limit handling

---

## Failure Analysis (29/46 invalid)

| Category | Puzzles | Count | Root Cause |
|----------|---------|-------|------------|
| A: Wildly wrong FENs | 19-24, 28 | 7 | Near-empty boards, starting positions, two-kings — model confused by full-page bulk extraction |
| B: Piece placement errors | 1,2,3,6,7,9,10,13,15,16,26,27,30,31,32,34,38,41,47 | 19 | FEN structurally valid but pieces in wrong squares |
| C: Invalid FEN characters | 11, 17 | 2 | Coordinate labels (`h`) leaked into FEN rank strings |
| D: SAN annotation | 30 | 1 | `Ng6!` — `!` not stripped before `board.parse_san()` |
| E: Ambiguous SAN | 8 | 1 | `Rf8+` — two rooks can reach f8, needs disambiguation |
| Missing entirely | 18, 35, 36, 37 | 4 | Pages 36/38 returned 0 diagrams |

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/extraction.py` | `sanitize_fen()`, `sanitize_san()`, `build_solution_constraint()`, `extract_puzzle_fen_with_hint()`, `SINGLE_PUZZLE_EXTRACTION_PROMPT`, pipeline reorder in `extract_chapter()`, `_call_gemini_with_backoff()`, zoom param for `extract_page_images()` |
| `backend/tests/test_extraction_eval.py` | ~12 new tests for sanitizers, constraint builder, disambiguation |

---

## Implementation

### 1. `sanitize_fen(fen: str) -> str` — new function (~line 398)

Strip non-FEN characters from piece placement, repair rank sums.

```python
def sanitize_fen(fen: str) -> str:
    parts = fen.split()
    if not parts:
        return fen
    ranks = parts[0].split("/")
    cleaned_ranks = []
    for rank in ranks:
        # Keep only valid FEN piece chars and digits
        cleaned = "".join(c for c in rank if c in "rnbqkpRNBQKP12345678")
        # Verify rank sums to 8
        total = sum(int(c) if c.isdigit() else 1 for c in cleaned)
        if total < 8:
            cleaned += str(8 - total)  # pad with empty squares
        elif total > 8:
            # Try dropping trailing digit overflow
            cleaned = cleaned  # leave for python-chess to catch
        cleaned_ranks.append(cleaned)
    parts[0] = "/".join(cleaned_ranks)
    return " ".join(parts)
```

Fixes: `3r1kh1` → `3r1k2`, `1p3pph` → `1p3pp1`

### 2. `sanitize_san(san: str) -> str` — new function

```python
def sanitize_san(san: str) -> str:
    return san.strip().rstrip("!?").rstrip("!?")  # double pass for "!?" combos
```

### 3. Modify `validate_puzzle()` (line 400)

Add sanitization before python-chess parsing:

```python
# was: board = chess.Board(p["fen"])
# new: 
p["fen"] = sanitize_fen(p["fen"])
p["solution_san"] = sanitize_san(p["solution_san"]) if p.get("solution_san") else p.get("solution_san")
board = chess.Board(p["fen"])
```

Also handle ambiguous SAN (Category E): if `parse_san` raises `chess.AmbiguousMoveError`, try each legal move that matches the target square and piece type, use the one where the full solution line validates.

### 4. `build_solution_constraint(solution_san, side_to_move) -> str` — new function

Deduces board requirements from the SAN string without needing a board:

```python
def build_solution_constraint(solution_san: str, side_to_move: str) -> str:
    san = sanitize_san(solution_san)
    color = "White" if side_to_move == "w" else "Black"
    
    # Detect piece type
    piece_map = {"N": "Knight", "B": "Bishop", "R": "Rook", "Q": "Queen", "K": "King"}
    if san[0] in piece_map:
        piece = piece_map[san[0]]
    elif "=" in san:
        piece = "pawn"  # promotion
    else:
        piece = "pawn"
    
    # Extract target square
    squares = re.findall(r'[a-h][1-8]', san)
    target = squares[-1] if squares else "?"
    
    # Build constraint parts
    parts = [f"The position MUST contain a {color} {piece} that can legally move to {target}."]
    
    if "x" in san:
        opp = "Black" if color == "White" else "White"
        parts.append(f"Since this is a capture (x), there MUST be a {opp} piece on {target}.")
    
    if "=" in san:
        promo_rank = "7th" if side_to_move == "w" else "2nd"
        file = target[0]
        pawn_sq = f"{file}{7 if side_to_move == 'w' else 2}"
        parts.append(f"There MUST be a {color} pawn on {pawn_sq} ({promo_rank} rank) ready to promote.")
    
    if "+" in san or "#" in san:
        parts.append(f"This move gives check, so the opponent King must be on a square attacked from {target}.")
    
    return " ".join(parts)
```

### 5. `SINGLE_PUZZLE_EXTRACTION_PROMPT` — new constant

```
Look at diagram #{puzzle_number} on this page from Polgar's "Chess Tactics for Champions".

CONSTRAINT FROM THE BOOK'S SOLUTION:
{constraint_text}

Your task:
1. Find diagram #{puzzle_number} on the page.
2. {side_to_move_text} to move.
3. List EVERY piece on the board, rank by rank from rank 8 (top) to rank 1 (bottom).
4. After listing pieces, VERIFY your list satisfies the constraint above.
5. If it doesn't, re-examine the diagram — the constraint is definitely correct.
6. Produce the FEN.

Common mistakes to avoid:
- Edge pieces on rank 8 and file h are often missed
- Bishops can look like queens at low resolution
- Small pawns in clusters are easy to miss

Return ONLY this JSON:
{"puzzle_number": {puzzle_number}, "side_to_move": "{side_to_move}", "fen": "YOUR_FEN"}
```

### 6. `extract_puzzle_fen_with_hint()` — new function

```python
def extract_puzzle_fen_with_hint(page_image_bytes, puzzle_number, side_to_move, solution_san, client=None):
    if client is None:
        client = get_gemini_client()
    from google.genai import types
    
    constraint = build_solution_constraint(solution_san, side_to_move)
    side_text = "White" if side_to_move == "w" else "Black"
    prompt = SINGLE_PUZZLE_EXTRACTION_PROMPT.format(
        puzzle_number=puzzle_number,
        constraint_text=constraint,
        side_to_move_text=side_text,
        side_to_move=side_to_move,
    )
    
    response = _call_gemini_with_backoff(client, GEMINI_MODEL, [
        types.Content(parts=[
            types.Part.from_bytes(data=page_image_bytes, mime_type="image/png"),
            types.Part.from_text(text=prompt),
        ])
    ])
    
    result = parse_json_from_text(response.text, dict)
    if result and "fen" in result:
        result["fen"] = sanitize_fen(result["fen"])
    return result
```

### 7. `_call_gemini_with_backoff()` — new helper

```python
def _call_gemini_with_backoff(client, model, contents, max_retries=5):
    import time, random
    from google.genai import types
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            if "429" in str(e) or "rate" in str(e).lower() or "quota" in str(e).lower():
                wait = (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Rate limited, retrying in {wait:.1f}s (attempt {attempt+1})")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Gemini API failed after {max_retries} retries")
```

Replace direct `client.models.generate_content()` calls in `extract_diagrams_from_page` (line 190), `extract_solutions_from_page` (line 209), `refine_puzzle` (line 350).

### 8. Modify `extract_chapter()` pipeline — insert Step 4

After `merged = merge_and_validate(all_diagrams, all_solutions)` (line 509), BEFORE the existing refine loop (line 512):

```python
# NEW Step 4: Solution-constrained fresh re-extraction for invalid puzzles
for idx, p in enumerate(merged):
    if not p["valid"] and p.get("solution_san") and p["error"] != "no_solution_found":
        ppage = p.get("pdf_page")
        img_bytes = page_img_by_num.get(ppage)
        if img_bytes:
            print(f"    - Re-extracting puzzle {p['puzzle_number']} with solution hint...", flush=True)
            re_extracted = extract_puzzle_fen_with_hint(
                img_bytes, p["puzzle_number"], p["turn"], p["solution_san"], client
            )
            if re_extracted and re_extracted.get("fen"):
                new_p = p.copy()
                new_p["fen"] = re_extracted["fen"]
                if re_extracted.get("side_to_move"):
                    new_p["turn"] = re_extracted["side_to_move"]
                validated = validate_puzzle(new_p)
                if validated["valid"]:
                    merged[idx] = validated
```

The existing `refine_puzzle` loop (lines 512-519) stays as the final fallback for puzzles that are STILL invalid after solution-constrained extraction.

### 9. `extract_page_images()` — add `zoom` parameter

```python
# was: def extract_page_images(start_page, end_page, pdf_path=PDF_PATH):
# was:     pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))
# new:
def extract_page_images(start_page, end_page, pdf_path=PDF_PATH, zoom=4):
    ...
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
```

### 10. Zero-diagram page retry in `extract_chapter()`

After the page loop, before the global merge:

```python
# Track pages with 0 diagrams for retry
zero_pages = [(pn, ib) for pn, ib in page_images 
              if not any(d.get("pdf_page") == pn for d in all_diagrams)]
for page_num, _ in zero_pages:
    print(f"  Retrying page {page_num} at 6x zoom...", flush=True)
    retry_imgs = extract_page_images(page_num, page_num, zoom=6)
    if retry_imgs:
        _, img_bytes = retry_imgs[0]
        diagrams = extract_diagrams_from_page(img_bytes, client)
        diagrams = [d for d in diagrams if isinstance(d, dict)]
        for d in diagrams:
            d["pdf_page"] = page_num
            page_img_by_num[page_num] = img_bytes
        all_diagrams.extend(diagrams)
        solutions = extract_solutions_from_page(img_bytes, client)
        all_solutions.extend(solutions)
```

---

## Execution Workflow

### RED — write failing tests first

Add to `backend/tests/test_extraction_eval.py`:

```python
# TestSanitizeFen — 4 tests
test_strips_coordinate_h()          # "3r1kh1/..." → "3r1k2/..."
test_strips_trailing_h_in_rank()    # "1p3pph" → "1p3pp1"
test_valid_fen_unchanged()          # clean FEN passes through
test_pads_short_rank()              # rank summing to <8 gets padding

# TestSanitizeSan — 4 tests
test_strips_exclamation()           # "Ng6!" → "Ng6"
test_strips_double_annotation()     # "Qxf6!?" → "Qxf6"
test_preserves_check()              # "Rf8+" unchanged
test_preserves_checkmate()          # "Qh7#" unchanged

# TestBuildSolutionConstraint — 4 tests
test_capture_constraint()           # "Qxf6" mentions capture + piece on f6
test_promotion_constraint()         # "f8=Q+" mentions pawn on f7
test_check_constraint()             # "Rg7+" mentions check + king position
test_black_move_constraint()        # "Bxf3" with side="b" mentions Black Bishop
```

Run `cd backend && pytest tests/test_extraction_eval.py -v` — new tests should be **RED**.

### GREEN — implement in order

1. `sanitize_fen()` + `sanitize_san()` + modify `validate_puzzle()` → sanitizer tests GREEN
2. `build_solution_constraint()` → constraint tests GREEN
3. `_call_gemini_with_backoff()` → wrap existing API calls
4. `SINGLE_PUZZLE_EXTRACTION_PROMPT` + `extract_puzzle_fen_with_hint()` → new extraction path
5. Modify `extract_chapter()` pipeline (Step 4 insertion + zero-page retry)
6. Add `zoom` parameter to `extract_page_images()`

Run `cd backend && pytest` — all tests should be **GREEN**.

### SHOWBOAT — `verification/phase15.1_extraction_accuracy.md`

```
showboat exec ... bash "cd backend && pytest tests/test_extraction_eval.py -v"
showboat exec ... bash "cd backend && python extract_chapter.py 2 --clear --export"
showboat exec ... bash "cd backend && python extract_chapter.py --report"
showboat exec ... bash "cd backend && pytest -v"
```

No PLAYWRIGHT section — backend-only data pipeline.

---

## Expected Impact

| Fix | Puzzles Addressed | Expected Recovery |
|-----|-------------------|-------------------|
| `sanitize_fen` | 11, 17 (Category C) | +2 (if underlying FEN correct after cleanup) |
| `sanitize_san` | 30 (SAN fix, FEN still wrong) | 0 directly, enables further fix |
| Solution-constrained extraction | All 29 invalid (Categories A+B) | +17-22 (fresh extraction without anchoring bias) |
| Zero-page retry | 18, 35, 36, 37 (missing) | +2-4 |
| **Total** | | **38-45/50 (76-90%)** |
