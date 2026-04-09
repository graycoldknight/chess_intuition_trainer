# Product Requirements Document (PRD): Chess Intuition Trainer

## 1. Product Overview
The **Chess Intuition Trainer** is a specialized web application designed to train chess tactical intuition in children (ages 7-9) using the **Christopher Yoo method** and material from Susan Polgar's *"Chess Tactics for Champions"*. The goal is to move beyond slow calculation and develop rapid, "System 1" pattern recognition for common tactical motifs.

### 1.1 Target Users
*   **Rishi (9yo, USCF 1228):** Student.
*   **Raghav (7yo, USCF 1008):** Student.
*   **Raj (Parent/Admin):** Oversight, extraction management, and graduation approval.

---

## 2. Core Methodology (Yoo's Method)
The application implements a micro-cycle spaced repetition system:
*   **Batching:** Puzzles are organized into batches of 50-100 (typically by chapter/motif).
*   **Repetition:** Each batch is repeated for 5-7 "circles."
*   **Speed Goal:** Graduation occurs when the average solve time for a circle is **< 15 seconds**.
*   **Challenge Mode:** Circles 6 and 7 introduce randomization to prevent "index-memorization."
*   **No Hints:** Pure pattern recognition—students see only the board and the side to move.

---

## 3. Functional Requirements

### 3.1 PDF Extraction Pipeline
*   **Automated Extraction:** Use Vision LLMs (Gemini 2.0 Flash / GPT-4o) to extract FEN positions from the Polgar PDF.
*   **Solution Parsing:** Extract multi-move solutions from the text sections and validate them against the board using `python-chess`.
*   **Parent Review:** A dedicated interface for parents to verify, edit, or reject extracted puzzles before they enter the training pool.

### 3.2 Training Loop
*   **Interactive Chessboard:** Powered by `react-chessboard` with automatic orientation based on side to move.
*   **Multi-Move Validation:** Students must play the entire solution sequence (both sides) to complete a puzzle.
*   **Feedback System:** Immediate visual feedback (Green/Red flashes) and move-tracking arrows for incorrect attempts.
*   **Progressive Circles:** 
    *   Circles 1-5: Sequential order to build positional memory.
    *   Circles 6-7: Randomized order ("Challenge Mode") to ensure genuine internalization.
*   **Session Management:** Daily 60-minute training cap to prevent burnout.

### 3.3 Gamification & Engagement
*   **XP System:** Points awarded for correct solves, speed bonuses, and circle completion.
*   **Badges:** 33 unique badges for theme mastery, speed milestones, and streaks.
*   **Leaderboard:** Friendly sibling competition based on XP, streaks, and improvement metrics.
*   **Streaks:** Daily tracking to encourage consistent practice.

### 3.4 Parent Panel
*   **Chapter Management:** Monitor extraction status of the 22 Polgar chapters.
*   **Graduation Approval:** Manual review of circle performance before a student moves to the next chapter.
*   **Data Analytics:** View detailed attempt history and recurring mistake patterns via the `puzzle_mastery` model.

---

## 4. Technical Architecture

### 4.1 Technology Stack
*   **Frontend:** React (Vite), TailwindCSS/Vanilla CSS, `react-chessboard`, `chess.js`.
*   **Backend:** FastAPI (Python), SQLAlchemy ORM.
*   **Database:** SQLite (Local-first).
*   **External Integration:** 
    *   **Vision LLM:** Gemini 2.0 / GPT-4o for PDF extraction.
    *   **Engine:** Stockfish (local binary) for position validation and "Show Answer" hints (debug mode).

### 4.2 Data Model
*   **Profiles:** Individual progress, XP, and streaks.
*   **Chapters:** Metadata for the 22 tactical motifs.
*   **Puzzles:** FENs, multi-move UCI solutions, and verification status.
*   **Batches:** Links profiles to chapters and tracks current circle progress.
*   **Attempts:** Granular record of every puzzle solve (time, success, user moves).
*   **Puzzle Mastery:** Aggregated analytics per puzzle per student (SM-2 logic ready for future use).

---

## 5. Implementation Roadmap

### Phase 1: Foundation
*   Scaffold project, setup SQLite schema, and seed initial data (Chapters, Profiles, Badges).

### Phase 2: Extraction Pipeline
*   Implement PyMuPDF image conversion and Vision LLM integration for PDF-to-FEN extraction.

### Phase 3: Core Training Loop
*   Build the interactive training screen with sequential circle logic and session timers.

### Phase 4: Dashboard & Analytics
*   Develop the student dashboard with progress charts and circle-by-circle statistics.

### Phase 5: Gamification
*   Integrate the XP formula, badge engine, and sibling leaderboard.

### Phase 6: Parent Panel
*   Create the management UI for extraction review and graduation approval.

### Phase 7: Polish & Mobile
*   Add animations (confetti, XP popups), session resume (localStorage), and tablet responsiveness.

### Phase 8: Multi-Move Sequences
*   Enhance the training engine to support multi-move solutions instead of single-move validation.

### Phase 9: Challenge Mode
*   Implement randomized puzzle ordering for Circles 6 and 7.

---

## 6. Quality Assurance & Testing
*   **TDD Approach:** Red/Green/Refactor cycle for all backend logic and frontend components.
*   **Showboat Docs:** Executable markdown verification for every implementation phase.
*   **E2E Testing:** Playwright automation for critical user flows (extraction to graduation).
*   **Unit Tests:** Pytest for backend and Vitest for frontend.

---

## 7. Success Metrics
*   **Speed:** Students achieving < 15s average on randomized challenge circles.
*   **Accuracy:** High first-attempt accuracy across all motifs.
*   **Engagement:** Consistent daily streaks and badge acquisition.
