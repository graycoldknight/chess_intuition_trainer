# Gemini CLI Activity Summary - Chess Intuition Trainer

## 1. Bug Fixes & Database Integrity
*   **Resolved `IntegrityError`:** Fixed a crash where duplicate `puzzle_number` entries were being inserted into the database during bulk extraction.
    *   Implemented deduplication in `merge_and_validate` to ensure only one instance of a puzzle number is processed per page.
    *   Added a final deduplication step in `extract_chapter` to handle duplicates across multiple pages.
*   **Fixed Transaction Handling:** Resolved `PendingRollbackError` by adding explicit `db_session.rollback()` calls in exception handlers.
*   **Database Schema Update:** Added an `error_message` column to the `puzzles` table to store validation failures (e.g., illegal moves or invalid FENs) for easier debugging.
*   **Seeding Fix:** Added a `__main__` block to `backend/seed.py` to allow direct database initialization.

## 2. Extraction Pipeline Improvements
*   **Rendering Quality:** Increased PDF-to-image rendering from **2x to 4x DPI**, significantly improving the vision model's ability to distinguish small chess pieces.
*   **Path Resolution:** Updated `PDF_PATH` to use absolute resolution via `.resolve()`, fixing "File Not Found" errors when running scripts from different directories.
*   **Refinement Loop (Self-Correction):** Implemented a retry mechanism where the LLM is given the specific error (e.g., "illegal move Nf6+") and asked to re-examine the diagram to fix the FEN.
*   **Robust Parsing:** Enhanced JSON extraction to handle LLM conversational "filler" using regex-like markers (` ```json `) and bracket matching.

## 3. Accuracy & Prompt Engineering
*   **Chain-of-Thought (CoT):** Updated prompts to require the LLM to "reason" by listing all pieces and their coordinates before generating the final FEN string.
*   **Few-Shot Prompting:** Incorporated **Ground Truth** examples directly into the system prompt. Using verified FENs for Puzzles 1, 2, 50, and 51, we "taught" the model the specific visual style of the book.
*   **Model Configuration:** Updated `backend/.env` and `extraction.py` to allow easy switching between `gemini-2.0-flash` and Pro models.

## 4. Ground Truth Integration
*   **Chapter 1 Population:** Manually imported **49 verified FENs** (puzzles 1–49) for Chapter 1.
*   **Verification Flags:** Updated the import logic to mark ground-truth puzzles as `verified=1` with `extraction_confidence=1.0`.

## 5. CLI & Workflow Tools
*   **Targeted Extraction:** Modified `extract_chapter.py` to support `max_pages` (e.g., `python3 extract_chapter.py 1 3`) for faster testing.
*   **Clean Slate Logic:** Added a `--clear` flag to `extract_chapter.py` to allow wiping existing chapter data before a re-run.
*   **Model Discovery:** Created `backend/list_models.py` to verify available API models.

## Current Status
*   **Chapter 1:** Fully populated with 49 verified FENs.
*   **Chapter 2:** Extraction pipeline is active; currently tuning for 100% accuracy using the few-shot examples and refinement loop.
*   **Core Infrastructure:** The backend is now stable, handles errors gracefully, and is optimized for high-resolution vision tasks.
