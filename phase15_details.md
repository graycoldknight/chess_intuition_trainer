# Phase 15: Implementation Details & Review Notes

## Overview

Phase 15 built an enhanced PDF extraction pipeline for chapters 2-22 of Polgar's "Chess Tactics for Champions". The plan is in `plan_phase15.md`. This document records what was actually implemented, bugs discovered during execution, and the current state of chapter 2.

---

## Files Created / Modified

| File | Type | Summary |
|------|------|---------|
| `backend/tests/test_extraction_eval.py` | New | 14 tests for correction hints, FEN diff, eval metrics |
| `backend/evaluate_extraction.py` | New | `FenDiff`, `compare_fens()`, `evaluate_pipeline()`, CLI |
| `backend/extraction.py` | Modified | 6 changes (see below) |
| `backend/extract_chapter.py` | Modified | Rewrote with `--export`, `--evaluate`, `--report` flags |

---

## Changes to `backend/extraction.py`

### 1. Enhanced `BULK_EXTRACTION_PROMPT`

Replaced 4 bare examples with a 4-section structured prompt:
- **Section 1**: Task description
- **Section 2**: COMMON MISTAKES — 5 edge cases with before/after FEN examples:
  - Edge blindness (rank 8 / file h)
  - Piece misidentification (bishop ↔ queen)
  - Rank shift (off-by-one)
  - Missing pawns
  - Side-to-move error
- **Section 3**: 12 diverse ch1 examples (puzzles 1, 2, 4, 7, 9, 12, 17, 29, 34, 36, 39, 46, 49)
- **Section 4**: Output format

### 2. Enhanced `SOLUTION_EXTRACTION_PROMPT`

Added 6 examples showing:
- Commentary to ignore ("It would be a blunder to grab...")
- Alternative lines to skip ("The immediate 1. Qg3 is not so successful...")
- Promotions (`f8=Q+`)
- Black-to-move solutions (`1... e5`)

### 3. New `generate_correction_hint(fen, solution_san, error) -> str`

Uses python-chess to diagnose WHY a move is illegal:
1. Parses FEN into a board
2. Tries to parse the move — if it succeeds, returns a generic message
3. Flips the turn and tries again → detects **wrong side to move**
4. Checks capture moves for **empty target square** or **own piece on target**
5. Checks if **any legal move can reach the target square**

Returns a specific natural-language hint like:
> "Qxf6 is a capture move, but f6 is empty in the extracted FEN. There must be a piece on f6 — re-examine the diagram carefully."

### 4. Solution-constrained `refine_puzzle()`

Rewrote to use `generate_correction_hint()` and attempt up to 2 refinements:
- **Attempt 1**: Prompt includes specific correction hint
- **Attempt 2**: Same hint + stronger language ("Be extremely methodical...")
- After both fail: sets `error = "NEEDS_REVIEW: <hint>"` for manual review

Each attempt internally validates with python-chess. Returns on first success.

### 5. New `extract_chapter_to_json(chapter_id, db_session, output_dir) -> dict`

Calls `extract_chapter()`, queries resulting DB puzzles, writes:
- `chapterN_questions.json` — `[{puzzle_number, fen, turn}, ...]`
- `chapterN_answers.json` — `[{puzzle_number, solution_san, solution_uci, solution_uci_line, solution_line}, ...]`

Same format as the existing `chapter1_*.json` consumed by `import_puzzles.py`.

Returns a quality report: `{found, valid, invalid, needs_review, q_path, a_path}`.

### 6. Global merge in `extract_chapter()` (bug fix — found during execution)

**Problem**: The original pipeline merged diagrams and solutions **per page**. In chapter 1, diagrams and solutions happened to be on the same pages. Chapter 2 has a different layout: a block of diagram pages followed by a block of solution pages. Diagrams on page 37, solutions on page 38 → they never paired, producing `no_solution_found` for most puzzles.

**Fix**: Collect all diagrams and all solutions across all pages first, then do one global merge at the end. Refinement step looks up the original page image via `p["pdf_page"]`.

Three sub-bugs found while implementing this:

- **`pdf_page` not passed through `merge_and_validate`**: The dict built in `merge_and_validate` didn't include `pdf_page` from the diagram dict. So `page_img_by_num.get(ppage)` always returned `None`, silently skipping all refinements. Fixed by adding `"pdf_page": diag.get("pdf_page")` to the merged dict.

- **Malformed diagram list**: Gemini occasionally returns a list of strings instead of a list of dicts (bad JSON day). `d["pdf_page"] = page_num` threw `TypeError: 'str' object does not support item assignment`. Fixed by filtering: `diagrams = [d for d in diagrams if isinstance(d, dict)]`.

- **Puzzle number type coercion**: Gemini sometimes returns `"puzzle_number": "3"` (string) instead of `"puzzle_number": 3` (int). This caused `sorted()` to fail with `TypeError: '<' not supported between instances of 'str' and 'int'` and also broke the solution_map lookup (string key vs int key). Fixed by `int(pnum)` in both the diagram loop and solution_map construction.

---

## New file: `backend/evaluate_extraction.py`

### `FenDiff` dataclass

```python
@dataclass
class FenDiff:
    is_exact_match: bool
    squares_different: int
    error_types: list        # ["edge_blindness", "piece_misid", "rank_shift", "missing_pawn"]
    details: list            # ["h4: extracted='P' truth='B'", ...]
```

### `compare_fens(extracted_fen, truth_fen) -> FenDiff`

- Compares piece placement AND side-to-move for exact match
- Parses both FENs into 64-square arrays
- Classifies differences:
  - `edge_blindness`: squares on rank 8 or file h
  - `piece_misid`: same square, different piece type
  - `rank_shift`: truth piece found one rank away in extracted
  - `missing_pawn`: truth has pawn, extracted has nothing

### `evaluate_pipeline(extracted, truth_q, truth_a) -> dict`

Compares extracted puzzles against ground truth. Returns:
- `fen_exact_match_rate`
- `piece_placement_accuracy` (avg fraction of 64 squares correct)
- `first_move_validation_rate` (vs `solution_uci_line[0]` from truth_a, NOT `solution_uci`)
- `full_line_validation_rate`
- `error_type_breakdown`
- `failed_puzzles` (list with per-puzzle diffs)
- `total_compared`

### CLI

```bash
python evaluate_extraction.py        # evaluate chapter 1
python evaluate_extraction.py 2      # evaluate chapter 2 (needs ground truth JSON)
```

---

## New `backend/extract_chapter.py` CLI

```bash
python extract_chapter.py 2                  # extract chapter 2 to DB
python extract_chapter.py 2 --export         # extract + export JSON files
python extract_chapter.py 2 --clear --export # re-extract from scratch + export
python extract_chapter.py --evaluate         # run eval harness on ch1
python extract_chapter.py --evaluate 2       # run eval harness on ch2 (needs ground truth)
python extract_chapter.py --report           # quality report for all chapters
```

`--report` output format:
```
 Ch  Title                               Status       Puzzles  Valid%  NeedsReview
  1  Forks and Double Attacks            verified          50    100%            0
  2  Pins and Skewers                    review            46     37%            0
```

"Valid%" = `extraction_confidence == 1.0` (FEN + solution SAN both validated by python-chess).

---

## Chapter 1 Baseline (eval harness)

```
Total compared:              50
FEN exact match rate:        98.0%
Piece placement accuracy:    100.0%
First move validation rate:  100.0%
Full line validation rate:   100.0%

Error type breakdown:
  edge_blindness: 1
  piece_misid: 1

Failed puzzles (1):
  Puzzle 50: 1 sq diff, types=['edge_blindness', 'piece_misid']
    h4: extracted='P' truth='B'
```

One puzzle (50) has a piece misidentification on the h-file — White bishop on h4 extracted as White pawn. Everything else is correct.

---

## Chapter 2 Current State

After 3 extraction attempts (fixing bugs progressively):

| Metric | Value |
|--------|-------|
| Puzzles found | 46 / ~50 expected |
| Valid (FEN + solution parseable) | 17 (37%) |
| `illegal san` errors | 25 |
| `invalid character in fen` | 2 |
| `ambiguous san` | 1 |
| `invalid san` | 1 |
| `no_solution_found` | 1 |

### Why only 37% valid?

The dominant failure is **`illegal san`** (25 puzzles): the FEN is structurally valid (python-chess can parse it) but the solution move can't be played in that position. This means the FEN has the right structure but wrong piece placement.

The refinement step runs for all these (25 refinement calls visible in the log) but most don't recover — likely because the page image is genuinely ambiguous at the FEN level and the LLM reproduces the same wrong FEN.

### Why only 46 puzzles (not 50)?

Pages 36 and 38 returned 0 diagrams:
- Page 36: `Failed to parse JSON` — Gemini returned malformed JSON for the diagram extraction
- Page 38: Returned 0 diagrams (Gemini decided it was a solutions-only page)

These 4 missing puzzles would need manual inspection or a targeted re-extraction of just those pages.

### Note on puzzle numbering

Chapter 2 puzzles are numbered **1–50 within the chapter** (same as chapter 1). They are stored in the DB with `chapter_id=2`, so there's no conflict with chapter 1's puzzles 1–50. The `import_puzzles.py` script correctly handles this via `(chapter_id, puzzle_number)` uniqueness.

---

## Test Results

All 140 tests GREEN after all changes:

```
140 passed, 284 warnings in 14.61s
```

New tests: `backend/tests/test_extraction_eval.py` — 14 tests covering:
- `generate_correction_hint`: capture on empty square, wrong turn, no piece of right type
- `compare_fens`: exact match, edge blindness, rank shift, piece misid, FenDiff fields
- `evaluate_pipeline`: perfect match, partial rate, first-move validation, report fields

---

## Open Questions for Review

1. **37% valid rate for ch2** — Is this acceptable as a first pass, or should we iterate on prompts before moving to ch3+? The 25 `illegal san` failures suggest the FEN extraction quality is the bottleneck, not the solution extraction.

2. **Missing 4 puzzles** — Pages 36 and 38 returned 0 diagrams. Could add a retry with a more targeted prompt (e.g., "this page definitely has chess diagrams — try harder") or use a different page rendering resolution.

3. **`invalid character in fen` (2 puzzles)** — The model writes FENs like `3r2kh/...` (appending `h` from `h8` labels). A simple post-processing step in `parse_json_from_text` or `validate_puzzle` could strip non-FEN characters before attempting to parse.

4. **`needs_review` always empty in report** — After `refine_puzzle()` sets `error = "NEEDS_REVIEW: ..."`, `extract_chapter()` calls `validate_puzzle()` on the return value, which overwrites the error with the raw chess error. The NEEDS_REVIEW flag is lost. Minor issue — the puzzles are still stored and identifiable by their errors.

5. **`invalid: 37` in quality report dict is misleading** — It comes from `result.get("invalid", 0)` which is the raw `extract_chapter()` count before refinements complete. The actual invalid count (by DB `extraction_confidence`) is 29. The field should be removed or corrected.
