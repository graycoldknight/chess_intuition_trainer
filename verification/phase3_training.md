# Phase 3: Training Loop Verification

## Note
Verify batch creation, puzzle serving, attempt recording, and circle progression.

## Checks

### Backend unit tests (training state machine)
```bash
cd backend && python3 -m pytest tests/test_training.py tests/test_training_api.py -v
```
**Expected:** 31 passed

### Frontend tests (TrainingSession + Stopwatch + SessionTimer)
```bash
cd frontend && npm test
```
**Expected:** 15 passed

### Full backend suite (regression)
```bash
cd backend && python3 -m pytest tests/ -q
```
**Expected:** 78 passed

### Create a batch for Rishi (profile_id=1) from Chapter 1
*Requires: backend running (`uvicorn main:app`) and verified puzzles in chapter 1 (from Phase 2)*
```bash
curl -s -X POST http://localhost:8000/api/training/create-batch \
  -H 'Content-Type: application/json' \
  -d '{"profile_id":1,"chapter_id":1}' | python3 -m json.tool
```

### Get training state
```bash
curl -s http://localhost:8000/api/training/state/1 | python3 -m json.tool
```

### Get next puzzle
```bash
curl -s http://localhost:8000/api/training/next-puzzle/1 | python3 -m json.tool
```

### Record a correct attempt
```bash
curl -s -X POST http://localhost:8000/api/training/attempt \
  -H 'Content-Type: application/json' \
  -d '{"profile_id":1,"puzzle_id":1,"batch_id":1,"circle":1,"success":true,"time_taken_ms":8500,"user_move":"g8f6"}' \
  | python3 -m json.tool
```

### Verify puzzle_mastery row was created
```bash
cd backend && python3 -c "
from database import SessionLocal
from models import PuzzleMastery
db = SessionLocal()
m = db.query(PuzzleMastery).first()
if m:
    print(f'attempts={m.total_attempts}, correct={m.total_correct}, best_ms={m.best_time_ms}')
else:
    print('No mastery records yet')
"
```
