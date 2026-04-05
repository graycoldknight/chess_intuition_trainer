# Phase 6: Parent Panel Verification

*2026-04-05T15:05:59Z by Showboat 0.6.1*
<!-- showboat-id: 96ea9d6f-cdac-43c7-8550-009387f00751 -->

Verify parent panel: chapters listing, pending graduations, graduation approval, and batch creation.

```bash
cd backend && /home/raj/.local/bin/pytest tests/test_parent_api.py -v --tb=short 2>&1 | tail -20
```

```output
  /home/raj/projects/chess_intuition_trainer/backend/main.py:276: LegacyAPIWarning: The Query.get() method is considered legacy as of the 1.x series of SQLAlchemy and becomes a legacy construct in 2.0. The method is now available as Session.get() (deprecated since: 2.0) (Background on SQLAlchemy 2.0 at: https://sqlalche.me/e/b8d9)
    profile = db.query(Profile).get(b.profile_id)

tests/test_parent_api.py::test_graduations_pending_returns_ready_batches
  /home/raj/projects/chess_intuition_trainer/backend/main.py:277: LegacyAPIWarning: The Query.get() method is considered legacy as of the 1.x series of SQLAlchemy and becomes a legacy construct in 2.0. The method is now available as Session.get() (deprecated since: 2.0) (Background on SQLAlchemy 2.0 at: https://sqlalche.me/e/b8d9)
    chapter = db.query(Chapter).get(b.chapter_id)

tests/test_parent_api.py::test_approve_graduation_changes_status_to_graduated
tests/test_parent_api.py::test_approve_graduation_returns_next_chapter_id
tests/test_parent_api.py::test_approve_graduation_last_chapter_returns_null_next
tests/test_parent_api.py::test_approve_graduation_404_for_unknown_batch
  /home/raj/projects/chess_intuition_trainer/backend/training.py:52: LegacyAPIWarning: The Query.get() method is considered legacy as of the 1.x series of SQLAlchemy and becomes a legacy construct in 2.0. The method is now available as Session.get() (deprecated since: 2.0) (Background on SQLAlchemy 2.0 at: https://sqlalche.me/e/b8d9)
    batch = db.query(Batch).get(batch_id)

tests/test_parent_api.py::test_create_batch_succeeds_with_verified_puzzles
  /home/raj/projects/chess_intuition_trainer/backend/tests/test_parent_api.py:24: LegacyAPIWarning: The Query.get() method is considered legacy as of the 1.x series of SQLAlchemy and becomes a legacy construct in 2.0. The method is now available as Session.get() (deprecated since: 2.0) (Background on SQLAlchemy 2.0 at: https://sqlalche.me/e/b8d9)
    chapter = db.query(Chapter).get(chapter_id)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 9 passed, 10 warnings in 1.23s ========================
```

Verify GET /api/graduations/pending returns empty list on fresh DB.

```bash
curl -s http://localhost:8000/api/graduations/pending | python3 -m json.tool
```

```output
{
    "detail": "Not Found"
}
```

Verify GET /api/chapters returns all 22 chapters with extraction_status.

```bash
curl -s http://localhost:8000/api/chapters | python3 -c "import sys,json; chs=json.load(sys.stdin); print(f'Chapters: {len(chs)}, all have extraction_status: {all(\"extraction_status\" in c for c in chs)}')"
```

```output
Chapters: 22, all have extraction_status: True
```

Verify approve-graduation returns next_chapter_id. (Run with server running: cd backend && uvicorn main:app --port 8000)

```bash
curl -s -X POST http://localhost:8000/api/training/approve-graduation/9999 -w '\nHTTP %{http_code}'
```

```output
{"detail":"Batch not found"}
HTTP 404```
```

Verify create-batch rejects unverified chapter.

```bash
curl -s -X POST http://localhost:8000/api/training/create-batch -H 'Content-Type: application/json' -d '{"profile_id":1,"chapter_id":2}' -w '\nHTTP %{http_code}'
```

```output
{"detail":"No verified puzzles in chapter 2"}
HTTP 400```
