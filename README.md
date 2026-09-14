# Library

React frontend and FastAPI backend for a personal library catalog, with accounts, book management, borrowing, and an optional AI librarian.

## Local setup

Requires Node.js 22.12+ and uv. Python 3.12 is provisioned by uv.

```sh
./scripts/setup.sh
./scripts/dev.sh
```

Open http://127.0.0.1:5173. API documentation: http://127.0.0.1:8000/docs.
Register an account, then add books to populate the empty catalog. Stop both servers with Ctrl+C.

The setup script installs locked dependencies, builds the frontend, creates missing environment files, and preserves existing configuration. Local library data is stored in `backend/library.db`. Tables are created on backend startup.

## Configuration

`backend/.env` contains secrets and provider settings; `.env.local` overrides it with the local SQLite URL. Environment variables take precedence over both files. Neither file should be committed.

To use PostgreSQL, set `DATABASE_URL` to a `postgresql+psycopg://...` URL in `.env.local`, or remove its SQLite override to use the existing `DATABASE_*` settings in `.env`. Existing PostgreSQL data is not copied into SQLite. Startup runs an idempotent additive upgrade for the original schema, preserving existing records. It refuses to apply the single-copy constraint if duplicate active loans exist; return those duplicates first. Back up the database before upgrading. Alembic is not currently used by the launcher.

The AI librarian requires a valid `GROQ_API_KEY` in `backend/.env` and network access. Use New chat in the librarian sidebar to start a separate conversation, or select a previous conversation to read and continue it. History persists across reloads and is scoped by authenticated user. Older sessions appear only when they have a matching stored user ID. Core library features work without an AI key. AI sessions are stored separately in `backend/agent_sessions.db`.

The Vite development server proxies API routes to port 8000. For a separately hosted production frontend, set `VITE_API_URL` at build time and configure the backend's allowed origins in `backend/app/main.py`. The local scripts are development launchers, not a production deployment.

## Verification

```sh
backend/.venv/bin/python scripts/smoke_test.py
backend/.venv/bin/python scripts/chat_history_test.py
backend/.venv/bin/python scripts/library_features_test.py
backend/.venv/bin/python scripts/migration_test.py
npm --prefix frontend run build
npm --prefix frontend audit
```

The smoke test uses a disposable database and checks registration, duplicate-email handling, login, search, book CRUD, borrowing, returns, and authentication. It does not call the paid AI provider.

## Library features and permissions

Each catalog entry represents one physical copy. Loans last 14 days; a database uniqueness constraint prevents two readers borrowing the same copy. Books on loan must be returned before deletion. My Library shows contributions, loans, overdue flags, and private reading shelves. Book detail pages support descriptions, ISBNs, publication years, cover-image URLs, and editing.

New accounts are readers: they can contribute and edit their own books, borrow available books, return their own loans, and manage their reading shelves. Librarians can edit all books, view members and active loans, and record returns. To grant librarian access to an existing account:

```sh
backend/.venv/bin/python scripts/set_role.py reader@example.com librarian
```

Use `reader` instead of `librarian` to revoke the role. Reload the app after changing roles. Role assignment is available only through this local administrator command.

Chat history supports title search, rename, deletion, and retrying a failed message. The AI can look up the signed-in reader's loans and link to book details. Borrow, return, and delete actions require confirmation through the book page; the AI has no tools that bypass those confirmations. Provider calls are not included in automated tests.

## Reservations, history, and renewals

Loan history now preserves returned loans, including title/author snapshots if a copy is later removed. Returns made before this upgrade cannot be reconstructed. Renewals extend the due date by 14 days, at most twice, and are refused when overdue or when another reader is waiting.

Reservations are per physical copy and ordered by when readers join. A returned copy is held for the next reader for 48 hours. My Library shows queue position and pickup readiness; open the copy to claim it. Cancelling or expiry advances the queue. Maintenance checks expiry every minute while the app runs. There is no promised availability date while a prior borrower still has the copy.

The catalog groups editions by normalized ISBN, or by normalized title/author when ISBN is absent. Each copy keeps its accession ID, provider, and circulation records. Sorting, availability filters, and pagination work at title level; open the detail page to choose a copy. ISBN lookup uses the [Open Library Books API](https://openlibrary.org/dev/docs/api/books), supports ISBN-10/13, and fills reviewable fields without saving. Keyboard-style barcode readers can type into the ISBN field; camera scanning is not included.

## Reminders and scheduled backups

My Library shows overdue and next-three-day reminders automatically. Optional email reminders require `SMTP_HOST`, `SMTP_FROM`, and the remaining SMTP settings shown in `.env.example`. Each reader must opt in through My Library. Delivery is attempted at most once per loan/due-date/day; uncertain SMTP failures are logged and not automatically resent that day to avoid duplicate mail. No live email delivery was performed during setup.

The single-worker launcher starts maintenance automatically: reservation expiry every minute and verified SQLite backups at startup and once per UTC day while the app runs. Backups live in `backend/backups/` and are retained until you remove them. To back up manually:

```sh
backend/.venv/bin/python scripts/backup_db.py
```

Each backup folder contains SQLite snapshots and a checksum manifest. Both library data and AI sessions are included when present; each database snapshot is consistent independently. For a coordinated recovery point across both databases, stop the app and run the backup command.

Restore into a new, empty directory (the command verifies checksums and database integrity):

```sh
backend/.venv/bin/python scripts/restore_db.py backend/backups/BACKUP_FOLDER --destination /tmp/library-recovery
```

Inspect the recovered files, stop the app, then copy the recovered `library.db` and `agent_sessions.db` into `backend/` (preserving the current files elsewhere first). Restart with `./scripts/dev.sh`. The restore command deliberately refuses to overwrite an existing directory's contents. You can also point `DATABASE_URL` at the recovered library file; AI sessions still use `backend/agent_sessions.db`.

## AI retry behavior

Each chat submission carries a request ID. Replays return the saved response; overlapping requests with the same ID are rejected. Book creation is recorded atomically with its result, so a provider failure after creation does not duplicate that book on retry. Confirmed actions are displayed separately from the AI reply. In this flow, adding the same title/author twice within one message is treated as one action; use separate messages to add additional copies. The single-worker launcher makes interrupted requests retryable after restart. Do not run multiple backend workers without replacing this startup recovery rule and coordinating maintenance.

Additional checks:

```sh
backend/.venv/bin/python scripts/phase2_test.py
backend/.venv/bin/python scripts/ai_retry_test.py
```
