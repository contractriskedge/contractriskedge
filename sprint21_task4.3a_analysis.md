================================================================================
  SPRINT 21 TASK 4.3A — Assignment Concurrency Defect Root-Cause Analysis
  Completed: June 4, 2026
================================================================================

A. ROOT CAUSE SUMMARY
───────────────────────────────────────────────────────────────────────────────

  Defect:      Concurrent POST /reviews/{id}/assign with same assignee_id
               creates duplicate rows in review_assignments.

  Evidence:    5 concurrent requests → 5 HTTP 200 → 5 assignment records
               for the same (review_id, assignee_id) pair.

  Root Cause:  Classic TOCTOU (Time-of-Check, Time-of-Use) race condition.

               Layer        | Problem
               ─────────────┼────────────────────────────────────────────────
               Database     | No unique constraint on (review_id, assignee_id)
                            | or on review_id alone in review_assignments.
                            | PK is assignment_id (UUID) — always unique.
               ─────────────┼────────────────────────────────────────────────
               Repository   | Blind INSERT with no pre-check, no ON CONFLICT,
                            | no SELECT FOR UPDATE, no advisory lock.
               ─────────────┼────────────────────────────────────────────────
               Service      | No check for existing assignment before calling
                            | repository.assign_reviewer(). Reads review,
                            | checks mutability, then inserts — all without
                            | any locking mechanism.
               ─────────────┼────────────────────────────────────────────────
               Lock Guard   | assert_can_reassign() only checks state
                            | immutability (terminal states). Does nothing
                            | to prevent duplicate assignments.
               ─────────────┼────────────────────────────────────────────────
               Transactions | Each request runs in its own transaction.
                            | Uncommitted inserts from concurrent requests
                            | are invisible to each other, so all 5 pass
                            | the "no existing assignment" check.

  Race Window: Between service.py line ~773 (get_review) and
               repository.py line ~451 (session.add + session.flush).
               Approximately 5-15ms of unprotected execution.

B. FIX OPTIONS
───────────────────────────────────────────────────────────────────────────────

  OPTION 1: Database Unique Constraint Only
  ─────────────────────────────────────────────────────────────────────────────
  Add a unique constraint on (review_id, assignee_id) in the
  review_assignments table. The 5th concurrent INSERT will fail with
  a PostgreSQL unique violation error.

  Implementation:
    ALTER TABLE review_assignments
    ADD CONSTRAINT uq_review_assignee UNIQUE (review_id, assignee_id);

  Then catch the integrity error in the service layer and return a
  proper 409 Conflict response.

  Complexity:  LOW  (1 ALTER TABLE + 1 except block)
  Risk:        LOW  (no data migration needed; existing data is clean)
  Reliability: HIGH (database-level enforcement is absolute)
  Production:  ✅ RECOMMENDED as the minimum fix

  ─────────────────────────────────────────────────────────────────────────────
  Caveat: This alone still allows concurrent requests to hit the DB before
  the constraint violation is detected. The error surfaces at COMMIT time,
  which means 4 of 5 requests will have already done work (status updates,
  etc.) before the 5th fails. The application must handle the rollback
  correctly.
  ─────────────────────────────────────────────────────────────────────────────


  OPTION 2: Service-Layer Duplicate Check Only
  ─────────────────────────────────────────────────────────────────────────────
  Add a SELECT query before INSERT in assign_reviewer() to check for
  existing assignments with the same (review_id, assignee_id).

  Implementation:
    existing = await self.session.execute(
        select(ReviewAssignment).where(
            ReviewAssignment.review_id == review_id,
            ReviewAssignment.assignee_id == assignee_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError("Reviewer already assigned to this review")

  Complexity:  LOW  (add ~10 lines to service.py)
  Risk:        HIGH (STILL VULNERABLE to TOCTOU — concurrent requests
               will both see no existing row and both proceed to INSERT)
  Reliability: LOW  (only works if requests are serialized, which they
               are not in async Python)
  Production:  ❌ NOT RECOMMENDED as standalone fix

  ─────────────────────────────────────────────────────────────────────────────
  Note: Option 2 alone is the current behavior that caused the bug. The
  check passes for all concurrent requests because they all read the DB
  before any of them commits.
  ─────────────────────────────────────────────────────────────────────────────


  OPTION 3: Database Constraint + Service-Layer Idempotent Handling
  ─────────────────────────────────────────────────────────────────────────────
  Add the unique constraint (Option 1) AND add a try/except around the
  INSERT to catch IntegrityError and return a clean 409 Conflict response
  with a meaningful error message.

  Additionally, use SELECT FOR UPDATE on the review row before the
  assignment check to serialize concurrent requests at the database level.

  Implementation:
    1. ALTER TABLE review_assignments
       ADD CONSTRAINT uq_review_assignee UNIQUE (review_id, assignee_id);

    2. In service.py assign_reviewer(), before any checks:
         review = await self.session.execute(
             select(ContractReview).where(ContractReview.review_id == review_id)
             .with_for_update()
         ).scalar_one_or_none()

    3. In repository.py assign_reviewer(), wrap INSERT in try/except:
         try:
             self.session.add(assignment)
             await self.session.flush()
         except IntegrityError:
             await self.session.rollback()
             raise ValueError("Reviewer already assigned to this review")

    4. In router.py, catch ValueError and return 409:
         except ValueError as e:
             if "already assigned" in str(e):
                 raise HTTPException(status_code=409, detail=str(e))

  Complexity:  MEDIUM (3 files, ~20 lines total)
  Risk:        LOW  (SELECT FOR UPDATE serializes; constraint is safety net)
  Reliability: VERY HIGH (defense in depth — application + database)
  Production:  ✅ RECOMMENDED as the complete fix

C. RECOMMENDATION
───────────────────────────────────────────────────────────────────────────────

  Implement Option 3 — Database Constraint + Service-Layer Idempotent Handling.

  Rationale:
    - The unique constraint is the absolute guarantee against duplicates
      at the database level (Option 1's value).
    - SELECT FOR UPDATE serializes concurrent requests at the transaction
      level, preventing the wasted work of 4 failed inserts.
    - The try/except IntegrityError handler ensures the API returns a clean
      409 Conflict response instead of a 500 Internal Server Error.
    - This is defense in depth: even if the application code has a bug,
      the database won't allow duplicates.

  Migration SQL:
    ALTER TABLE review_assignments
    ADD CONSTRAINT uq_review_assignee UNIQUE (review_id, assignee_id);

  This will also serve as a useful unique constraint for the application
  logic that assumes one reviewer per review assignment.

D. AFFECTED FILES
───────────────────────────────────────────────────────────────────────────────

  File                          | Change
  ──────────────────────────────┼─────────────────────────────────────────────
  backend/alembic/versions/     | NEW — migration to add unique constraint
  backend/app/domains/review/   | Add try/except IntegrityError around INSERT
    repository.py               |
  backend/app/domains/review/   | Add SELECT FOR UPDATE before assignment
    service.py                  | Add IntegrityError import
  backend/app/domains/review/   | Add 409 handler for "already assigned"
    router.py                   |

================================================================================
