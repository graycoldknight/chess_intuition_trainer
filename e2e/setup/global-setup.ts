/**
 * Global setup: creates a throwaway "Test" profile (ID 99) with a fresh batch.
 * Delegates to backend/test_setup.py so data is immediately visible to the API.
 */

import { execSync } from 'child_process';

const BACKEND = '/home/raj/projects/chess_intuition_trainer/backend';

export default async function globalSetup() {
  execSync(`cd "${BACKEND}" && python3 test_setup.py create`, { stdio: 'inherit' });
}
