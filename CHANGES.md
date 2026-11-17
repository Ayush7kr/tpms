# Changes

## Bugs fixed

**Security**
- The demo role switcher (`/auth/switch/ADMIN/`) let anyone, even someone not logged in, become admin by opening a link. It now works only when `DEMO_MODE` is on, and only through a POST button.
- Resumes were publicly downloadable from `/media/resumes/...` without logging in. They are now served only through the permission-checked download view.
- "Activate/deactivate user" ran on a plain GET link. It is now a POST form.
- Students could open institution-wide placement and salary reports. These are staff-only now.
- An admin could remove their own admin role or deactivate themselves from the edit form and lock everyone out.
- `SECRET_KEY`, `DEBUG` and `ALLOWED_HOSTS` were hard-coded and `.env` was never loaded. Settings now come from the environment / `.env`.

**Features that didn't work**
- Role-wide notifications (like "new drive posted") could never be marked as read, so the bell badge never cleared. Read state is now tracked per user.
- Students never saw college-wide study material. The filter `department__in=[None, dept]` never matches empty values in SQL.
- The "allowed degrees" setting on a drive was never checked.
- After withdrawing, a student could never apply to that drive again. They now get an "Apply again" button while the drive is open.
- Revoking one offer marked the student unplaced even if they held another offer. A lower second offer also overwrote a higher first one.
- The AI assistant used `gemini-1.5-flash`, which Google has retired, so every live call failed. It also sent the first 10 messages of a conversation instead of the last 10, and sent the student's new message twice. Rewritten to use the REST API with a configurable model.
- Error messages appeared unstyled (Django's `error` tag has no Bootstrap `alert-error` class).
- The custom 403/404/500 pages existed but were never wired up.
- A student account without an academic record crashed most student pages. The admin could also create such accounts. Students now get an explanation page, and the admin is pointed to the coordinator's student form.
- The coordinator dashboard showed packages like "11.2000000000000 LPA".
- Saving the edit-drive form could round the package (14.75 to 14.8).
- The CSV export ignored the 10th %, 12th % and search filters shown on screen.
- A model change had no migration (`makemigrations` reported pending changes).

**Validation added**
- Drive deadline must be in the future, and the drive date can't come before it. Deadlines are stored timezone-aware.
- Cut-offs: CGPA 0-10, marks 0-100, backlogs not negative. Same ranges on student records.
- LinkedIn/GitHub links must be real URLs. Resumes must be PDFs under 5 MB.
- Approval decisions, verification statuses and placement statuses are checked against the allowed values.

**New**
- Drive edit form can now change cut-offs and eligible branches.
- Students get a notification when they move to a new round, or when a coordinator flags their marks.

## Interface

- New design system in `static/css/style.css`: ink navy and marigold palette, Schibsted Grotesk and Public Sans, one consistent set of cards, tables, badges and forms.
- The key change on the student side: every drive shows the student's own CGPA, 10th, 12th and backlogs next to the drive's cut-off, with the missed ones in red.
- Rewritten pages: landing, login, layout and sidebar, student home, open drives, my applications, drive detail, error pages. Every other page restyled and its copy rewritten in plain language.
- The landing page shows live numbers from the database instead of made-up ones (it used to claim 94.2% placement and 1,250+ students).
- Bootstrap, icons, Chart.js and fonts are bundled locally, so the app works offline.
- Charts use the new palette and whole-number axes for student counts.
- Works on phones: the sidebar becomes a drawer, cut-off grids reflow.

## Tests

- 14 new regression tests in `tests/test_fixes.py` covering the fixes above (77 tests total, all passing).
- Tests that used fixed dates in December 2026 now use relative dates, so they don't start failing next year.
