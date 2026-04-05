/**
 * sessionStorage.js
 * Utilities for persisting training session state to localStorage
 * so users can resume where they left off on the same day.
 */

export const SESSION_STORAGE_KEY = 'chess_trainer_session';

function today() {
  return new Date().toISOString().slice(0, 10); // "YYYY-MM-DD"
}

/**
 * Save session state for a profile.
 * @param {{ profileId: number, batchId: number, circle: number, puzzleIndex: number, date: string }} state
 */
export function saveSessionToStorage(state) {
  const existing = _loadRaw();
  existing[String(state.profileId)] = { ...state, date: state.date ?? today() };
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(existing));
}

/**
 * Load session state for a profile.
 * Returns null if no state exists, belongs to a different profile, or is from a different day.
 * @param {number} profileId
 * @returns {{ profileId, batchId, circle, puzzleIndex, date } | null}
 */
export function loadSessionFromStorage(profileId) {
  const all = _loadRaw();
  const entry = all[String(profileId)];
  if (!entry) return null;
  if (entry.date !== today()) return null;
  return entry;
}

/**
 * Remove saved session for a profile.
 * @param {number} profileId
 */
export function clearSessionFromStorage(profileId) {
  const all = _loadRaw();
  delete all[String(profileId)];
  localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(all));
}

function _loadRaw() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}
