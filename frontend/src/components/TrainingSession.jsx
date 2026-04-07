import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Chessboard } from 'react-chessboard';
import { Chess } from 'chess.js';
import Stopwatch from './Stopwatch';
import SessionTimer from './SessionTimer';
import ConfettiOverlay from './ConfettiOverlay';
import XpPopup from './XpPopup';
import * as api from '../services/api';
import { saveSessionToStorage, loadSessionFromStorage, clearSessionFromStorage } from '../services/sessionStorage';

const PROFILE_NAMES = { 1: 'Rishi', 2: 'Raghav', 3: 'Raj' };
const EDIT_PROFILES = new Set([3, 99]); // Raj (parent) + test profile
const PIECE_SYMBOLS = {
  wK: '♔', wQ: '♕', wR: '♖', wB: '♗', wN: '♘', wP: '♙',
  bK: '♚', bQ: '♛', bR: '♜', bB: '♝', bN: '♞', bP: '♟',
};
const AUTO_ADVANCE_CORRECT_MS = 1000;
const AUTO_ADVANCE_WRONG_MS = 2000;

// How often the stopwatch display refreshes per circle (coarser = less pressure)
function stopwatchTickMs(circle) {
  if (circle <= 1) return 30_000;
  if (circle === 2) return 15_000;
  if (circle === 3) return 1_000;
  return 50;
}

// ---------------------------------------------------------------------------
// FEN position helpers for free-placement editing (no chess.js validation)
// ---------------------------------------------------------------------------
function fenToBoard(fen) {
  const board = {};
  const rows = fen.split(' ')[0].split('/');
  for (let ri = 0; ri < 8; ri++) {
    let fi = 0;
    for (const ch of rows[ri]) {
      if (ch >= '1' && ch <= '8') { fi += parseInt(ch, 10); }
      else {
        const sq = 'abcdefgh'[fi] + (8 - ri);
        board[sq] = { type: ch.toLowerCase(), color: ch === ch.toUpperCase() ? 'w' : 'b' };
        fi++;
      }
    }
  }
  return board;
}

function boardToFenPosition(board) {
  let pos = '';
  for (let rank = 8; rank >= 1; rank--) {
    let empty = 0;
    for (const file of 'abcdefgh') {
      const p = board[file + rank];
      if (p) {
        if (empty) { pos += empty; empty = 0; }
        pos += p.color === 'w' ? p.type.toUpperCase() : p.type;
      } else { empty++; }
    }
    if (empty) pos += empty;
    if (rank > 1) pos += '/';
  }
  return pos;
}

function movePieceInFen(fen, from, to) {
  const parts = fen.split(' ');
  const board = fenToBoard(fen);
  const piece = board[from];
  if (!piece) return fen;
  delete board[from];
  board[to] = piece;
  parts[0] = boardToFenPosition(board);
  return parts.join(' ');
}

function applyFenTurn(fen, turn) {
  const parts = fen.split(' ');
  parts[1] = turn;
  return parts.join(' ');
}

function TrainingSession() {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const pid = parseInt(profileId, 10);
  const canEdit = EDIT_PROFILES.has(pid);

  const [puzzle, setPuzzle] = useState(null);
  const [puzzleLoading, setPuzzleLoading] = useState(true); // true until first fetch completes
  const [game, setGame] = useState(new Chess());
  const [state, setState] = useState(null); // training state
  const [session, setSession] = useState(null);
  const [batchId, setBatchId] = useState(null);

  // Solve feedback
  const [solveStatus, setSolveStatus] = useState(null); // 'correct' | 'wrong' | null
  const [arrows, setArrows] = useState([]);
  const [stopwatchActive, setStopwatchActive] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [xpEarned, setXpEarned] = useState(null);
  const [totalXp, setTotalXp] = useState(0);
  const solveTimeRef = useRef(0);
  const advancing = useRef(false);

  // Multi-move state
  const [solutionMoves, setSolutionMoves] = useState([]); // ['f3f6', 'h6g7', 'f6b6']
  const [moveIndex, setMoveIndex] = useState(0);

  // Browse navigation (test profile 99 only)
  const [puzzleIds, setPuzzleIds] = useState([]);
  const puzzleIdsRef = useRef([]);
  const [browseIndex, setBrowseIndex] = useState(0);
  const browseIndexRef = useRef(0);
  const [showAnswer, setShowAnswer] = useState(false);

  // Edit mode (Raj + test profile)
  const [editMode, setEditMode] = useState(false);
  const [editFen, setEditFen] = useState('');
  const [editTurn, setEditTurn] = useState('w');
  const [editSolutionSan, setEditSolutionSan] = useState('');
  const [editSolutionUci, setEditSolutionUci] = useState('');
  const [editSolutionLine, setEditSolutionLine] = useState('');
  const [editSolutionUciLine, setEditSolutionUciLine] = useState('');
  const [editSaving, setEditSaving] = useState(false);
  const [placePiece, setPlacePiece] = useState(null); // e.g. {type:'q', color:'w'}

  // Load state + start session on mount
  useEffect(() => {
    (async () => {
      const trainingState = await api.getTrainingState(pid);
      setState(trainingState);
      if (trainingState.total_xp != null) setTotalXp(trainingState.total_xp);

      if (trainingState.has_active_batch) {
        setBatchId(trainingState.batch_id);

        if (canEdit && trainingState.puzzle_ids) {
          setPuzzleIds(trainingState.puzzle_ids);
          puzzleIdsRef.current = trainingState.puzzle_ids;
        }

        // Start session if none active
        if (!trainingState.session) {
          const sess = await api.startSession(pid);
          setSession(sess);
        } else {
          setSession(trainingState.session);
        }

        loadNextPuzzle();
      } else {
        setPuzzleLoading(false);
      }
    })();
  }, [pid]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadNextPuzzle = useCallback(async (fromCircle) => {
    advancing.current = false;
    setSolveStatus(null);
    setArrows([]);
    setPuzzleLoading(true);

    const resp = await api.getNextPuzzle(pid);
    setPuzzleLoading(false);

    if (!resp.puzzle) {
      setPuzzle(null);
      setStopwatchActive(false);
      return;
    }

    // Circle just advanced — show results before starting next circle
    if (fromCircle != null && resp.current_circle != null && resp.current_circle !== fromCircle) {
      navigate(`/results/${pid}`, { replace: true });
      return;
    }

    const p = resp.puzzle;
    setPuzzle(p);
    const g = new Chess(p.fen);
    setGame(g);
    // Resolve solution moves: use solution_uci_line if available, else fall back to [solution_uci]
    setSolutionMoves(p.solution_uci_line ?? [p.solution_uci]);
    setMoveIndex(0);
    setShowAnswer(false);
    setStopwatchActive(true);
    if (canEdit) {
      const idx = puzzleIdsRef.current.indexOf(p.id);
      if (idx >= 0) { setBrowseIndex(idx); browseIndexRef.current = idx; }
    }
  }, [pid]);

  const handlePieceDrop = useCallback(
    (sourceSquare, targetSquare, piece) => {
      if (!puzzle || solveStatus || advancing.current) return false;

      const userUci = sourceSquare + targetSquare;
      // Include promotion suffix if piece is a pawn reaching back rank
      const promotionSuffix = piece && piece[1] === 'P' && (targetSquare[1] === '8' || targetSquare[1] === '1') ? 'q' : '';
      const userUciFull = userUci + promotionSuffix;

      const expectedUci = solutionMoves[moveIndex] ?? '';
      // Match ignoring promotion case differences (e.g. 'f7f8q' vs 'f7f8Q')
      const isCorrect = userUciFull.toLowerCase() === expectedUci.toLowerCase()
        || userUci.toLowerCase() === expectedUci.slice(0, 4).toLowerCase();

      if (isCorrect) {
        // Apply move visually
        setArrows([[sourceSquare, targetSquare, 'green']]);
        try {
          game.move({ from: sourceSquare, to: targetSquare, promotion: 'q' });
          setGame(new Chess(game.fen()));
        } catch (_) {}

        const isLastMove = moveIndex === solutionMoves.length - 1;

        if (isLastMove) {
          // Puzzle complete
          setStopwatchActive(false);
          setSolveStatus('correct');

          api.recordAttempt({
            profile_id: pid,
            puzzle_id: puzzle.id,
            batch_id: batchId,
            circle: state?.current_circle ?? 1,
            success: true,
            time_taken_ms: solveTimeRef.current,
            user_move: userUci,
          }).then((res) => {
            if (res?.xp_earned) {
              setXpEarned(res.xp_earned);
              setShowConfetti(true);
              setTimeout(() => { setShowConfetti(false); setXpEarned(null); }, 2000);
            }
            if (res?.total_xp != null) setTotalXp(res.total_xp);
            saveSessionToStorage({
              profileId: pid,
              batchId,
              circle: state?.current_circle ?? 1,
              puzzleIndex: puzzle.puzzle_number,
            });
          }).catch(console.error);

          advancing.current = true;
          if (canEdit) {
            setTimeout(() => {
              const next = browseIndexRef.current + 1;
              if (next < puzzleIdsRef.current.length) loadPuzzleById(puzzleIdsRef.current[next], next);
            }, AUTO_ADVANCE_CORRECT_MS);
          } else {
            const circle = state?.current_circle ?? 1;
            setTimeout(() => loadNextPuzzle(circle), AUTO_ADVANCE_CORRECT_MS);
          }
        } else {
          // Intermediate correct move — advance index, keep timer running
          setMoveIndex(moveIndex + 1);
        }
        return true;
      } else {
        // Wrong move at any index
        setStopwatchActive(false);
        setSolveStatus('wrong');

        const expected = solutionMoves[moveIndex] ?? puzzle.solution_uci;
        const from = expected.slice(0, 2);
        const to = expected.slice(2, 4);
        setArrows([[from, to, 'red']]);

        api.recordAttempt({
          profile_id: pid,
          puzzle_id: puzzle.id,
          batch_id: batchId,
          circle: state?.current_circle ?? 1,
          success: false,
          time_taken_ms: solveTimeRef.current,
          user_move: userUci,
        }).catch(console.error);

        advancing.current = true;
        if (canEdit) {
          setTimeout(() => {
            const next = browseIndexRef.current + 1;
            if (next < puzzleIdsRef.current.length) loadPuzzleById(puzzleIdsRef.current[next], next);
          }, AUTO_ADVANCE_WRONG_MS);
        } else {
          const circle = state?.current_circle ?? 1;
          setTimeout(() => loadNextPuzzle(circle), AUTO_ADVANCE_WRONG_MS);
        }
        return false;
      }
    },
    [puzzle, solveStatus, batchId, state, pid, loadNextPuzzle, solutionMoves, moveIndex, game]
  );

  const handleStopwatchStop = useCallback((ms) => {
    solveTimeRef.current = ms;
  }, []);

  const loadPuzzleById = useCallback(async (puzzleId, index) => {
    advancing.current = false;
    setSolveStatus(null);
    setArrows([]);
    setPuzzleLoading(true);
    const resp = await api.getPuzzleById(puzzleId);
    setPuzzleLoading(false);
    if (!resp.puzzle) return;
    const p = resp.puzzle;
    setPuzzle(p);
    setGame(new Chess(p.fen));
    setSolutionMoves(p.solution_uci_line ?? [p.solution_uci]);
    setMoveIndex(0);
    setBrowseIndex(index);
    browseIndexRef.current = index;
    // No stopwatch — browse/validation mode only
  }, []);

  const handlePrev = useCallback(() => {
    const idx = browseIndex - 1;
    if (idx >= 0) loadPuzzleById(puzzleIds[idx], idx);
  }, [browseIndex, puzzleIds, loadPuzzleById]);

  const handleNext = useCallback(() => {
    const idx = browseIndex + 1;
    if (idx < puzzleIds.length) loadPuzzleById(puzzleIds[idx], idx);
  }, [browseIndex, puzzleIds, loadPuzzleById]);

  const handleEnterEdit = useCallback(() => {
    setEditFen(puzzle.fen);
    setEditTurn(puzzle.turn);
    setEditSolutionSan(puzzle.solution_san || '');
    setEditSolutionUci(puzzle.solution_uci || '');
    setEditSolutionLine(puzzle.solution_line || '');
    setEditSolutionUciLine((puzzle.solution_uci_line || []).join(' '));
    setPlacePiece(null);
    setStopwatchActive(false);
    setEditMode(true);
  }, [puzzle]);

  const handleCancelEdit = useCallback(() => {
    setEditMode(false);
  }, []);

  const handleEditPieceDrop = useCallback((sourceSquare, targetSquare) => {
    setEditFen(prev => movePieceInFen(prev, sourceSquare, targetSquare));
    return true;
  }, []);

  // Click a board square — place the selected palette piece (or do nothing)
  const handleEditSquareClick = useCallback((square) => {
    if (!placePiece) return;
    setEditFen(prev => {
      const parts = prev.split(' ');
      const board = fenToBoard(prev);
      board[square] = placePiece;
      parts[0] = boardToFenPosition(board);
      return parts.join(' ');
    });
  }, [placePiece]);

  // Right-click a square to remove its piece
  const handleEditSquareRightClick = useCallback((square) => {
    setEditFen(prev => {
      const parts = prev.split(' ');
      const board = fenToBoard(prev);
      delete board[square];
      parts[0] = boardToFenPosition(board);
      return parts.join(' ');
    });
  }, []);

  const handleEditTurnChange = useCallback((turn) => {
    setEditTurn(turn);
    setEditFen(prev => applyFenTurn(prev, turn));
  }, []);

  const handleUpdatePuzzle = useCallback(async () => {
    setEditSaving(true);
    try {
      const uciLine = editSolutionUciLine.trim() ? editSolutionUciLine.trim().split(/\s+/) : null;
      await Promise.all([
        api.updatePuzzleFen(puzzle.id, editFen, editTurn),
        api.updatePuzzleSolution(puzzle.id, {
          solution_san: editSolutionSan,
          solution_uci: editSolutionUci,
          solution_line: editSolutionLine || null,
          solution_uci_line: uciLine,
        }),
      ]);
      setPuzzle(p => ({
        ...p,
        fen: editFen,
        turn: editTurn,
        solution_san: editSolutionSan,
        solution_uci: editSolutionUci,
        solution_line: editSolutionLine || null,
        solution_uci_line: uciLine,
      }));
      setSolutionMoves(uciLine ?? [editSolutionUci]);
      setGame(new Chess(editFen));
      setEditMode(false);
    } catch (e) {
      alert('Save failed: ' + e.message);
    } finally {
      setEditSaving(false);
    }
  }, [puzzle, editFen, editTurn, editSolutionSan, editSolutionUci, editSolutionLine, editSolutionUciLine]);

  if (!state || puzzleLoading) {
    return <div style={{ textAlign: 'center', marginTop: 80 }}>Loading...</div>;
  }

  if (!state.has_active_batch) {
    return (
      <div style={{ textAlign: 'center', marginTop: 80 }}>
        <h2>No active batch</h2>
        <p style={{ color: '#888' }}>Ask Raj to create a batch for you.</p>
        <button onClick={() => navigate('/')} style={btnStyle}>
          Back
        </button>
      </div>
    );
  }

  if (!puzzleLoading && !puzzle) {
    // Circle complete — navigate to results screen
    navigate(`/results/${pid}`, { replace: true });
    return null;
  }

  const boardOrientation = puzzle.turn === 'w' ? 'white' : 'black';
  const bgColor = solveStatus === 'correct' ? '#14532d' : solveStatus === 'wrong' ? '#450a0a' : '#1a1a1a';
  const editBoardWidth = Math.min(480, typeof window !== 'undefined' ? window.innerWidth - 32 : 480);

  return (
    <div
      data-testid="training-session"
      style={{
        maxWidth: 520,
        margin: '0 auto',
        padding: '20px 16px',
        background: bgColor,
        minHeight: '100vh',
        transition: 'background 0.3s',
      }}
    >
      {/* Animations */}
      <div data-testid="confetti-overlay">
        <ConfettiOverlay active={showConfetti} />
      </div>
      <XpPopup xp={xpEarned} />

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <button onClick={() => navigate('/')} style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', fontSize: '0.85rem' }}>
          ← {PROFILE_NAMES[pid]}
        </button>
        <span style={{ color: '#facc15', fontWeight: 700, fontSize: '0.9rem' }}>⚡ {totalXp} XP</span>
        <SessionTimer
          sessionStartedAt={session?.started_at}
          onExpired={loadNextPuzzle}
        />
      </div>

      {/* Puzzle info */}
      <div style={{ textAlign: 'center', marginBottom: 8, color: '#aaa', fontSize: '0.85rem', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10 }}>
        <span>Circle {state.current_circle} &nbsp;|&nbsp; Puzzle {puzzle.puzzle_number}
        &nbsp;|&nbsp; {puzzle.turn === 'w' ? 'White' : 'Black'} to move</span>
        {state?.is_randomized_circle && (
          <span style={{ background: '#b45309', color: '#fef3c7', borderRadius: 6, padding: '2px 8px', fontSize: '0.78rem', fontWeight: 700 }}>⚡ Challenge Mode</span>
        )}
        {canEdit && !editMode && (
          <>
            <button onClick={handlePrev} disabled={browseIndex <= 0} style={editBtnStyle}>← Prev</button>
            <span style={{ color: '#666', fontSize: '0.78rem' }}>{browseIndex + 1} / {puzzleIds.length}</span>
            <button onClick={handleNext} disabled={browseIndex >= puzzleIds.length - 1} style={editBtnStyle}>Next →</button>
            <button onClick={handleEnterEdit} style={editBtnStyle}>Edit</button>
            <button
              onClick={() => setShowAnswer(v => !v)}
              style={{ ...editBtnStyle, background: showAnswer ? '#3b1a00' : undefined }}
            >
              {showAnswer ? 'Hide' : 'Answer'}
            </button>
          </>
        )}
      </div>

      {/* Stopwatch */}
      <Stopwatch active={stopwatchActive} onStop={handleStopwatchStop} tickMs={stopwatchTickMs(state.current_circle)} style={{ marginBottom: 8 }} />

      {/* Multi-move progress indicator — only shown after first intermediate correct move */}
      {moveIndex > 0 && solutionMoves.length > 1 && !solveStatus && (
        <div
          data-testid="move-progress"
          style={{ textAlign: 'center', marginBottom: 6, color: '#facc15', fontSize: '0.85rem', fontWeight: 600 }}
        >
          Move {moveIndex + 1} of {solutionMoves.length}
        </div>
      )}

      {editMode ? (
        /* ── Edit mode (Raj + test profile) ── */
        <div>
          <div data-testid="chessboard-container">
            <Chessboard
              position={editFen}
              onPieceDrop={handleEditPieceDrop}
              onSquareClick={handleEditSquareClick}
              onSquareRightClick={handleEditSquareRightClick}
              boardOrientation={editTurn === 'w' ? 'white' : 'black'}
              arePiecesDraggable={true}
              boardWidth={editBoardWidth}
              customSquareStyles={placePiece ? { cursor: 'crosshair' } : {}}
            />
          </div>
          <div style={{ marginTop: 10 }}>
            <div style={{ color: '#888', fontSize: '0.75rem', marginBottom: 4 }}>FEN (editable)</div>
            <textarea
              value={editFen}
              onChange={e => setEditFen(e.target.value)}
              rows={3}
              style={{ width: '100%', background: '#111', color: '#e2e8f0', border: '1px solid #444', borderRadius: 6, padding: '6px 8px', fontSize: '0.75rem', fontFamily: 'monospace', resize: 'vertical', boxSizing: 'border-box' }}
            />
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button onClick={() => handleEditTurnChange('w')} style={{ ...turnBtnStyle, background: editTurn === 'w' ? '#7c3aed' : '#2a2a2a' }}>White to move</button>
            <button onClick={() => handleEditTurnChange('b')} style={{ ...turnBtnStyle, background: editTurn === 'b' ? '#7c3aed' : '#2a2a2a' }}>Black to move</button>
          </div>
          {/* Solution fields */}
          <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {[
              ['Solution SAN (first move)', editSolutionSan, setEditSolutionSan],
              ['Solution UCI (first move)', editSolutionUci, setEditSolutionUci],
              ['Solution line (SAN prose)', editSolutionLine, setEditSolutionLine],
              ['UCI line (space-separated)', editSolutionUciLine, setEditSolutionUciLine],
            ].map(([label, value, setter]) => (
              <div key={label}>
                <div style={{ color: '#888', fontSize: '0.72rem', marginBottom: 2 }}>{label}</div>
                <input
                  value={value}
                  onChange={e => setter(e.target.value)}
                  style={{ width: '100%', background: '#111', color: '#e2e8f0', border: '1px solid #444', borderRadius: 6, padding: '5px 8px', fontSize: '0.8rem', fontFamily: 'monospace', boxSizing: 'border-box' }}
                />
              </div>
            ))}
          </div>
          {/* Piece palette — click to select, then click a square to place */}
          {[
            ['wK','wQ','wR','wB','wN','wP'],
            ['bK','bQ','bR','bB','bN','bP'],
          ].map((row, ri) => (
            <div key={ri} style={{ display: 'flex', justifyContent: 'center', gap: 4, marginTop: 8 }}>
              {row.map(code => {
                const color = code[0].toLowerCase();
                const type = code[1].toLowerCase();
                const active = placePiece?.color === color && placePiece?.type === type;
                return (
                  <div
                    key={code}
                    onClick={() => setPlacePiece(active ? null : { type, color })}
                    style={{
                      width: editBoardWidth / 8,
                      height: editBoardWidth / 8,
                      cursor: 'pointer',
                      border: active ? '2px solid #facc15' : '2px solid transparent',
                      borderRadius: 4,
                      background: active ? '#3b2e00' : color === 'w' ? '#f0d9b5' : '#b58863',
                      color: '#1a1a1a',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: editBoardWidth / 10,
                      userSelect: 'none',
                    }}
                  >
                    {PIECE_SYMBOLS[code]}
                  </div>
                );
              })}
            </div>
          ))}
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button onClick={handleUpdatePuzzle} disabled={editSaving} style={{ ...btnStyle, flex: 1 }}>
              {editSaving ? 'Saving…' : 'Update'}
            </button>
            <button onClick={handleCancelEdit} style={{ ...btnStyle, flex: 1, background: '#2a2a2a' }}>Cancel</button>
          </div>
        </div>
      ) : (
        /* ── Normal play mode ── */
        <>
          <div data-testid="chessboard-container">
            <Chessboard
              position={game.fen()}
              onPieceDrop={handlePieceDrop}
              boardOrientation={boardOrientation}
              customArrows={arrows}
              arePiecesDraggable={!solveStatus}
              boardWidth={Math.min(480, typeof window !== 'undefined' ? window.innerWidth - 32 : 480)}
            />
          </div>

          {/* Feedback */}
          {solveStatus === 'correct' && (
            <div data-testid="feedback-correct" style={{ textAlign: 'center', marginTop: 12, color: '#4ade80', fontSize: '1.2rem', fontWeight: 700 }}>
              Correct!
            </div>
          )}
          {solveStatus === 'wrong' && (
            <div data-testid="feedback-wrong" style={{ textAlign: 'center', marginTop: 12, color: '#f87171', fontSize: '1.2rem', fontWeight: 700 }}>
              Wrong — {puzzle.solution_san} was right
            </div>
          )}
          {canEdit && showAnswer && (
            <div style={{
              marginTop: 14,
              background: '#111827',
              border: '1px solid #374151',
              borderRadius: 8,
              padding: '10px 14px',
            }}>
              <div style={{ color: '#9ca3af', fontSize: '0.72rem', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Solution
              </div>
              <div style={{ color: '#f9fafb', fontSize: '0.95rem', fontWeight: 600, marginBottom: 6 }}>
                {puzzle.solution_line || puzzle.solution_san}
              </div>
              {puzzle.solution_uci_line && puzzle.solution_uci_line.length > 1 && (
                <div style={{ color: '#6b7280', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                  UCI: {puzzle.solution_uci_line.join(' ')}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

const btnStyle = {
  background: '#7c3aed',
  border: 'none',
  borderRadius: 8,
  padding: '10px 24px',
  color: '#fff',
  cursor: 'pointer',
  fontSize: '1rem',
  marginTop: 16,
};

const editBtnStyle = {
  background: '#1e3a5f',
  border: '1px solid #2d5a8e',
  borderRadius: 5,
  padding: '2px 10px',
  color: '#7eb8f7',
  cursor: 'pointer',
  fontSize: '0.78rem',
};

const turnBtnStyle = {
  flex: 1,
  border: 'none',
  borderRadius: 6,
  padding: '8px 0',
  color: '#fff',
  cursor: 'pointer',
  fontSize: '0.85rem',
};

export default TrainingSession;
