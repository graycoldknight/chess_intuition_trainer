/**
 * Global teardown: removes the Test profile (ID 99) and all related rows.
 * Delegates to backend/test_setup.py so cleanup uses the same ORM as setup.
 */

import { execSync } from 'child_process';

const BACKEND = '/home/raj/projects/chess_intuition_trainer/backend';

export default async function globalTeardown() {
  execSync(`cd "${BACKEND}" && python3 test_setup.py destroy`, { stdio: 'inherit' });
}
