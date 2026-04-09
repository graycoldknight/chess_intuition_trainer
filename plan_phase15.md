# Phase 15: Enhanced PDF Extraction Pipeline for Chapters 2-22

## Context

We need to extract ~1,050 chess puzzles (FEN positions + multi-move solutions) from chapters 2-22
of Polgar's "Chess Tactics for Champions" PDF. We have validated ground truth for chapter 1
(50 puzzles) and an existing extraction pipeline in `backend/extraction.py` that uses Gemini 2.0
Flash vision + python-chess validation. The existing pipeline works but has weak prompts (only 4
few-shot examples), no evaluation harness, and no solution-guided FEN correction.

**Key decisions:**
- Evaluation-first: build harness, measure ch1 baseline, then improve prompts, then scale — can't improve what you can't measure
- Solution-constrained FEN correction: use move legality failures to generate specific correction hints for the LLM (book solution text is more reliable than vision extraction — "Qxf6" means there MUST be a capturable piece on f6)
- Enhance existing `backend/extraction.py` — don't create parallel files; no Stockfish, no model fallback, no new DB schema
- Eval harness must use `solution_uci_line[0]` as first-move truth, not `solution_san`/`solution_uci` (those fields are stale for many ch1 puzzles)
- Output: `chapterN_questions.json` + `chapterN_answers.json` per chapter (same format as ch1, consumed by existing `import_puzzles.py`)

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/extraction.py` | Enhanced prompts (12 few-shot + 5 edge cases), `generate_correction_hint()`, enhanced `refine_puzzle()`, new `extract_chapter_to_json()` |
| `backend/extract_chapter.py` | New flags: `--export`, `--evaluate`, `--report` |
| `backend/evaluate_extraction.py` | **New file** (~120 lines): `FenDiff`, `compare_fens()`, `evaluate_pipeline()`, CLI |
| `backend/tests/test_extraction_eval.py` | **New file**: unit tests for correction hints, FEN comparison, eval metrics |

---

## Implementation

### `backend/evaluate_extraction.py` (new)

**`FenDiff` dataclass:**
```python
@dataclass
class FenDiff:
    is_exact_match: bool
    squares_different: int        # count of squares that differ
    error_types: list[str]        # ["edge_blindness", "piece_misid", "rank_shift", "missing_pawn"]
    details: list[str]            # human-readable per-square diffs
```

**`compare_fens(extracted_fen, truth_fen) -> FenDiff`:**
- Parse both FENs into 64-square arrays
- Compare square by square
- Classify differences:
  - rank 8 / file h → `edge_blindness`
  - piece type swap (b↔q, n↔b, etc.) → `piece_misid`
  - same piece shifted one rank → `rank_shift`
  - missing pawn → `missing_pawn`

**`evaluate_pipeline(extracted, truth_q, truth_a) -> dict`:**
- FEN exact match rate
- FEN piece-placement accuracy (% of 64 squares correct, averaged across puzzles)
- First move validation rate (against `solution_uci_line[0]`)
- Full line validation rate
- Error type breakdown (counts per category)
- List of failed puzzle numbers with details

**CLI:** `python evaluate_extraction.py` — loads ch1 JSON ground truth + ch1 DB puzzles, prints report.

---

### `backend/extraction.py` — enhanced prompts

**`BULK_EXTRACTION_PROMPT`** (currently 4 examples → replace with 4-section structured prompt):
- Section 1: Task description
- Section 2: COMMON MISTAKES — all 5 edge cases from `training_edge_cases.txt` with before/after FEN corrections
- Section 3: EXAMPLES — 12 diverse ch1 puzzles (puzzles 1, 4, 7, 9, 12, 17, 29, 34, 36, 39, 46, 49), chosen to cover: both colors, promotions, castling rights, various piece densities, edge pieces
- Section 4: Output format (JSON array)

Token budget: 12 examples × 80 tokens + 5 edge cases × 150 tokens ≈ 1,710 tokens — well within Gemini 2.0 Flash context limits.

**`SOLUTION_EXTRACTION_PROMPT`** — add 6 ch1 examples showing:
- Simple solutions: `"1. Rf6+ Kg7 2. Rb6"`
- Commentary to ignore: `"It would be a blunder to grab..."`
- Alternative lines to skip: `"The immediate 1. Qg3 is not so successful..."`
- Promotions: `"1. f8=Q+! Kxf8 2. Bxd6+"`

---

### `backend/extraction.py` — `generate_correction_hint()`

New function `generate_correction_hint(fen, solution_san, error) -> str`:
```python
# Uses python-chess to diagnose WHY a move is illegal:
# - Target square empty for capture → "Qxf6 requires a piece on f6, but f6 is empty"
# - No piece of right type can reach target → "No Knight can reach b6"
# - Wrong side to move → "FEN says Black to move, but solution is White's move"
```

Implementation:
1. Parse `solution_san` to extract target square and capture flag
2. Check `board.piece_at(target_square)`
3. Check `board.turn` vs expected turn
4. Generate specific natural-language hint

---

### `backend/extraction.py` — solution-constrained `refine_puzzle()`

Enhanced `refine_puzzle()`:
- Compute correction hint via `generate_correction_hint()`
- Include hint in refinement prompt (currently generic "common mistakes" only)
- Add second refinement attempt if first fails (same hint, stronger language)
- After 2 failed refinements, flag with `error_message` for manual review

---

### `backend/extraction.py` — `extract_chapter_to_json()`

New function `extract_chapter_to_json(chapter_id, db_session, output_dir=ROOT) -> dict`:
- Calls existing `extract_chapter()`
- Queries resulting puzzles from DB
- Writes `chapterN_questions.json` + `chapterN_answers.json` in same format as ch1
- Returns quality report: `{found, valid, invalid, needs_review: [puzzle_numbers]}`

---

### `backend/extract_chapter.py` — enhanced CLI

```bash
python extract_chapter.py 2                  # extract chapter 2 to DB (existing)
python extract_chapter.py 2 --export         # extract + export JSON files
python extract_chapter.py 2 --clear --export # re-extract from scratch + export
python extract_chapter.py --evaluate         # run eval harness on ch1
python extract_chapter.py --report           # quality report for all extracted chapters
```

---

## Execution Workflow

### RED — write failing tests first

Create `backend/tests/test_extraction_eval.py`:

```python
def test_generate_correction_hint_capture_on_empty():
    fen = "r6k/pp3Qpp/2bqp3/4Np2/2P5/8/PP3PPP/5RK1 w - - 0 1"
    hint = generate_correction_hint(fen, "Qxf6", "illegal san")
    assert "f6" in hint

def test_generate_correction_hint_wrong_turn():
    fen = "8/1b3pkp/pN1p2p1/3Pq3/Q3P3/8/6PP/6K1 w - - 0 1"
    hint = generate_correction_hint(fen, "Qc3", "illegal san")
    assert "turn" in hint.lower() or "black" in hint.lower()

def test_compare_fens_exact_match():
    diff = compare_fens(
        "8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1",
        "8/1b6/p6k/4p1p1/4P1Pp/3P1R1P/1b4K1/8 w - - 0 1",
    )
    assert diff.is_exact_match and diff.squares_different == 0

def test_compare_fens_edge_blindness():
    extracted = "8/p1r1k2r/1p5q/4Pp2/1P1Q2p1/6P1/3R1PK1/5R2 w - - 0 1"
    truth     = "7r/p1r1k3/1p5q/4Pp2/1P1Q2p1/6P1/3R1PK1/5R2 w - - 0 1"
    diff = compare_fens(extracted, truth)
    assert diff.squares_different > 0
    assert "edge_blindness" in diff.error_types

def test_compare_fens_rank_shift():
    extracted = "r5k1/ppq2p1p/2n3p1/8/3N3r/8/PP1Q1PPP/5RK1 w - - 0 1"
    truth     = "r7/ppq2pkp/2n3p1/8/3N3r/8/PP1Q1PPP/R4RK1 w - - 0 1"
    diff = compare_fens(extracted, truth)
    assert not diff.is_exact_match

def test_evaluate_pipeline_metrics():
    # 2 exact matches + 1 FEN mismatch
    report = evaluate_pipeline(extracted=[...], truth_q=[...], truth_a=[...])
    assert report["fen_exact_match_rate"] == pytest.approx(2/3)
```

Run `cd backend && pytest tests/test_extraction_eval.py -v` — all tests should be **RED**.

### GREEN — implement in this order

1. `generate_correction_hint()` + `compare_fens()` in `extraction.py`/`evaluate_extraction.py` (pure python-chess logic, no API calls) → correction hint tests GREEN
2. `evaluate_pipeline()` in `evaluate_extraction.py` → eval metric tests GREEN
3. Run eval on ch1 to establish **BASELINE** accuracy numbers
4. Enhanced `BULK_EXTRACTION_PROMPT` + `SOLUTION_EXTRACTION_PROMPT` → re-run eval, compare vs baseline
5. Solution-constrained `refine_puzzle()` → re-run eval, compare numbers
6. Target: >90% FEN exact match, >95% first move validation on ch1
7. `extract_chapter_to_json()` + enhanced `extract_chapter.py` CLI
8. Extract chapters 2-22 one at a time, reviewing quality reports

Run `cd backend && pytest` — all tests should be **GREEN**.

### SHOWBOAT — `verification/phase15_extraction_pipeline.md`

```
showboat exec ... bash "cd backend && pytest tests/test_extraction_eval.py -v"
showboat exec ... bash "cd backend && python evaluate_extraction.py"
showboat exec ... bash "cd backend && python extract_chapter.py 2 --export"
showboat exec ... bash "cd backend && pytest -v"
```

No PLAYWRIGHT section — backend-only data pipeline.

---

## Risk Notes

1. **Rate limits:** ~50 Gemini calls/chapter × 21 chapters ≈ 1,050 calls. At 15 RPM free tier, ~70 min total. Use tenacity with exponential backoff.
2. **Solution pages separate from diagram pages:** Some chapters may have solutions in a different section. Verify ch2 PDF structure before assuming same layout as ch1.
3. **Unknown puzzle counts:** Use "no gaps in puzzle number sequence" as heuristic for completeness check.
4. **Ch1 ground truth quality:** `solution_san`/`solution_uci` are stale for many puzzles. Eval harness MUST use `solution_uci_line[0]` as first-move truth.

---

## Chapter Page Ranges (from `seed.py`)

| Chapter | Pages | Topic |
|---------|-------|-------|
| Ch 1  | 13–30   | Forks and Double Attacks |
| Ch 2  | 31–48   | Pins and Skewers |
| Ch 3  | 49–64   | Deflection and Decoy |
| Ch 4  | 65–80   | Discovery and Double Check |
| Ch 5  | 81–96   | Removing the Guard |
| Ch 6  | 97–112  | Pawn Promotion |
| Ch 7  | 113–126 | Overloaded Pieces |
| Ch 8  | 127–142 | X-ray and Intermediate Moves |
| Ch 9  | 143–156 | Trapped Pieces |
| Ch 10 | 157–172 | Zugzwang and Stalemate Themes |
| Ch 11 | 173–186 | Perpetual Check |
| Ch 12 | 187–200 | Stalemate Saves |
| Ch 13 | 201–214 | Fortress and Drawing Techniques |
| Ch 14 | 215–230 | Back Rank Mates |
| Ch 15 | 231–246 | Knight and Bishop Mates |
| Ch 16 | 247–262 | Queen and Rook Mates |
| Ch 17 | 263–276 | Pawn and Minor Piece Mates |
| Ch 18 | 277–290 | Double Check Mates |
| Ch 19 | 291–310 | Two-Move Combinations |
| Ch 20 | 311–330 | Three-Move Combinations |
| Ch 21 | 331–352 | Complex Combinations |
| Ch 22 | 353–376 | Championship-Level Tactics |
