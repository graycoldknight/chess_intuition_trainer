import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Chessboard } from 'react-chessboard';
import { Chess } from 'chess.js';
import Stopwatch from './Stopwatch';
import SessionTimer from './SessionTimer';
import * as api from '../services/api';

const PROFILE_NAMES = { 1: 'Rishi', 2: 'Raghav', 3: 'Raj' };
const AUTO_ADVANCE_CORRECT_MS = 1000;
const AUTO_ADVANCE_WRONG_MS = 2000;

function TrainingSession() {
  const { profileId } = useParams();
  const navigate = useNavigate();
  const pid = parseInt(profileId, 10);

  const [puzzle, setPuzzle] = useState(null);
  const [game, setGame] = useState(new Chess());
  const [state, setState] = useState(null); // training state
  const [session, setSession] = useState(null);
  const [batchId, setBatchId] = useState(null);

  // Solve feedback
  const [solveStatus, setSolveStatus] = useState(null); // 'correct' | 'wrong' | null
  const [arrows, setArrows] = useState([]);
  const [stopwatchActive, setStopwatchActive] = useState(false);
  const solveTimeRef = useRef(0);
  const advancing = useRef(false);

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
      }
    })();
  }, [pid]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadNextPuzzle = useCallback(async () => {
    advancing.current = false;
    setSolveStatus(null);
    setArrows([]);

    const resp = await api.getNextPuzzle(pid);
    if (!resp.puzzle) {
      setPuzzle(null);
      setStopwatchActive(false);
      return;
    }

    const p = resp.puzzle;
    setPuzzle(p);
    const g = new Chess(p.fen);
    setGame(g);
    setStopwatchActive(true);
  }, [pid]);

  const handlePieceDrop = useCallback(
    (sourceSquare, targetSquare) => {
      if (!puzzle || solveStatus || advancing.current) return false;

      const userUci = sourceSquare + targetSquare;

      if (userUci === puzzle.solution_uci) {
        // Correct
        setStopwatchActive(false);
        setSolveStatus('correct');
        setArrows([[sourceSquare, targetSquare, 'green']]);

        // Apply move visually
        const g = new Chess(puzzle.fen);
        try {
          g.move({ from: sourceSquare, to: targetSquare, promotion: 'q' });
          setGame(new Chess(g.fen()));
        } catch (_) {}

        // Record
        api.recordAttempt({
          profile_id: pid,
          puzzle_id: puzzle.id,
          batch_id: batchId,
          circle: state?.current_circle ?? 1,
          success: true,
          time_taken_ms: solveTimeRef.current,
          user_move: userUci,
        }).catch(console.error);

        // Auto-advance
        advancing.current = true;
        setTimeout(loadNextPuzzle, AUTO_ADVANCE_CORRECT_MS);
        return true;
      } else {
        // Wrong
        setStopwatchActive(false);
        setSolveStatus('wrong');

        // Show correct move arrow
        const [from, to] = [
          puzzle.solution_uci.slice(0, 2),
          puzzle.solution_uci.slice(2, 4),
        ];
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
    [puzzle, solveStatus, batchId, state, pid, loadNextPuzzle]
  );

  const handleStopwatchStop = useCallback((ms) => {
    solveTimeRef.current = ms;
  }, []);

  if (!state) {
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

  if (!puzzle) {
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
