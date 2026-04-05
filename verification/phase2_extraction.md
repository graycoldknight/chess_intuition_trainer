# Phase 2: Extraction Pipeline Verification

*2026-04-05T03:48:06Z by Showboat 0.6.1*
<!-- showboat-id: 078edb76-26f2-4b7a-8f1b-9a3cc40ca3f3 -->

Verify PDF extraction parsing, FEN validation, and chapter API.

```bash
cd backend && python3 -m pytest tests/test_extraction.py tests/test_extraction_api.py -v --tb=no 2>&1 | grep -E '(PASSED|FAILED|ERROR)' | head -30
```

```output
tests/test_extraction.py::TestParseDiagramResponse::test_parses_valid_json PASSED [  4%]
tests/test_extraction.py::TestParseDiagramResponse::test_handles_markdown_code_fences PASSED [  9%]
tests/test_extraction.py::TestParseDiagramResponse::test_returns_empty_on_invalid_json PASSED [ 14%]
tests/test_extraction.py::TestParseDiagramResponse::test_returns_empty_on_empty_array PASSED [ 19%]
tests/test_extraction.py::TestParseDiagramResponse::test_skips_incomplete_items PASSED [ 23%]
tests/test_extraction.py::TestParseDiagramResponse::test_normalizes_side_to_move PASSED [ 28%]
tests/test_extraction.py::TestParseSolutionResponse::test_parses_valid_json PASSED [ 33%]
tests/test_extraction.py::TestParseSolutionResponse::test_handles_markdown_fences PASSED [ 38%]
tests/test_extraction.py::TestParseSolutionResponse::test_returns_empty_on_invalid PASSED [ 42%]
tests/test_extraction.py::TestMergeAndValidate::test_merges_matching_puzzles PASSED [ 47%]
tests/test_extraction.py::TestMergeAndValidate::test_flags_missing_solution PASSED [ 52%]
tests/test_extraction.py::TestMergeAndValidate::test_rejects_illegal_move PASSED [ 57%]
tests/test_extraction.py::TestMergeAndValidate::test_rejects_invalid_fen PASSED [ 61%]
tests/test_extraction.py::TestMergeAndValidate::test_converts_san_to_uci PASSED [ 66%]
tests/test_extraction.py::TestMergeAndValidate::test_multiple_puzzles_partial_match PASSED [ 71%]
tests/test_extraction_api.py::test_list_chapters_returns_all_22 PASSED   [ 76%]
tests/test_extraction_api.py::test_extract_chapter_returns_202 PASSED    [ 80%]
tests/test_extraction_api.py::test_extract_nonexistent_chapter_404 PASSED [ 85%]
tests/test_extraction_api.py::test_get_unverified_puzzles PASSED         [ 90%]
tests/test_extraction_api.py::test_verify_single_puzzle PASSED           [ 95%]
tests/test_extraction_api.py::test_verify_all_puzzles PASSED             [100%]
```
