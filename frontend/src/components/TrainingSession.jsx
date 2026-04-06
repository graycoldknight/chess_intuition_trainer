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
const AUTO_ADVANCE_CORRECT_MS = 1000;
const AUTO_ADVANCE_WRONG_MS = 2000;

function TrainingSession() {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const pid = parseInt(profileId, 10);

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
  const solveTimeRef = useRef(0);
  const advancing = useRef(false);

  // Multi-move state
  const [solutionMoves, setSolutionMoves] = useState([]); // ['f3f6', 'h6g7', 'f6b6']
  const [moveIndex, setMoveIndex] = useState(0);

  // Load state + start session on mount
  useEffect(() => {
    (async () => {
      const trainingState = await api.getTrainingState(pid);
      setState(trainingState);

      if (trainingState.has_active_batch) {
        setBatchId(trainingState.batch_id);

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

  const loadNextPuzzle = useCallback(async () => {
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

    const p = resp.puzzle;
    setPuzzle(p);
    const g = new Chess(p.fen);
    setGame(g);
    // Resolve solution moves: use solution_uci_line if available, else fall back to [solution_uci]
    setSolutionMoves(p.solution_uci_line ?? [p.solution_uci]);
    setMoveIndex(0);
    setStopwatchActive(true);
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
            saveSessionToStorage({
              profileId: pid,
              batchId,
              circle: state?.current_circle ?? 1,
              puzzleIndex: puzzle.puzzle_number,
            });
          }).catch(console.error);

          advancing.current = true;
          setTimeout(loadNextPuzzle, AUTO_ADVANCE_CORRECT_MS);
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
        setTimeout(loadNextPuzzle, AUTO_ADVANCE_WRONG_MS);
        return false;
      }
    },
    [puzzle, solveStatus, batchId, state, pid, loadNextPuzzle, solutionMoves, moveIndex, game]
  );

  const handleStopwatchStop = useCallback((ms) => {
    solveTimeRef.current = ms;
  }, []);

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
        <SessionTimer
          sessionStartedAt={session?.started_at}
          onExpired={loadNextPuzzle}
        />
      </div>

      {/* Puzzle info */}
      <div style={{ textAlign: 'center', marginBottom: 8, color: '#aaa', fontSize: '0.85rem' }}>
        Circle {state.current_circle} &nbsp;|&nbsp; Puzzle {puzzle.puzzle_number}
        &nbsp;|&nbsp; {puzzle.turn === 'w' ? 'White' : 'Black'} to move
      </div>

      {/* Stopwatch */}
      <Stopwatch active={stopwatchActive} onStop={handleStopwatchStop} style={{ marginBottom: 8 }} />

      {/* Multi-move progress indicator — only shown after first intermediate correct move */}
      {moveIndex > 0 && solutionMoves.length > 1 && !solveStatus && (
        <div
          data-testid="move-progress"
          style={{ textAlign: 'center', marginBottom: 6, color: '#facc15', fontSize: '0.85rem', fontWeight: 600 }}
        >
          Move {moveIndex + 1} of {solutionMoves.length}
        </div>
      )}

      {/* Board */}
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

export default TrainingSession;
