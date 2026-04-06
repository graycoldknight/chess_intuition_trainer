const BASE_URL = 'http://localhost:8000';

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// Profiles
export const getProfiles = () => request('/api/profiles');

// Dashboard
export const getDashboard = (profileId) => request(`/api/dashboard/${profileId}`);

// Training
export const getTrainingState = (profileId) =>
  request(`/api/training/state/${profileId}`);

export const getNextPuzzle = (profileId) =>
  request(`/api/training/next-puzzle/${profileId}`);

export const recordAttempt = (data) =>
  request('/api/training/attempt', { method: 'POST', body: JSON.stringify(data) });

export const startSession = (profileId) =>
  request(`/api/training/start-session/${profileId}`, { method: 'POST' });

export const endSession = (sessionId) =>
  request(`/api/training/end-session/${sessionId}`, { method: 'POST' });

export const createBatch = (profileId, chapterId) =>
  request('/api/training/create-batch', {
    method: 'POST',
    body: JSON.stringify({ profile_id: profileId, chapter_id: chapterId }),
  });

// Gamification
export const getLeaderboard = () => request('/api/leaderboard');
export const getBadges = (profileId) => request(`/api/badges/${profileId}`);

// Parent panel
export const getChapters = () => request('/api/chapters');
export const getPendingGraduations = () => request('/api/graduations/pending');
export const approveGraduation = (batchId) =>
  request(`/api/training/approve-graduation/${batchId}`, { method: 'POST' });
export const getUnverifiedPuzzles = (chapterId) =>
  request(`/api/puzzles/unverified/${chapterId}`);

// Puzzle browsing (test profile 99)
export const getPuzzleById = (puzzleId) =>
  request(`/api/puzzles/${puzzleId}`);

// Puzzle editing (test profile 99)
export const updatePuzzleFen = (puzzleId, fen, turn) =>
  request(`/api/puzzles/${puzzleId}/fen`, {
    method: 'PUT',
    body: JSON.stringify({ fen, turn }),
  });

export const updatePuzzleSolution = (puzzleId, { solution_san, solution_uci, solution_line, solution_uci_line }) =>
  request(`/api/puzzles/${puzzleId}/solution`, {
    method: 'PUT',
    body: JSON.stringify({ solution_san, solution_uci, solution_line, solution_uci_line }),
  });
