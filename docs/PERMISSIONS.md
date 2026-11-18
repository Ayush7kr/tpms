# Roles and permissions

Who can open what. This table was produced by signing in as each demo role and requesting every URL in the project, so it reflects what the code actually does, not just what it intends.

## Roles

| Role | Code | Who |
| --- | --- | --- |
| Administrator | `ADMIN` | Runs the portal: accounts, departments, coordinator assignments |
| Principal | `PRINCIPAL` | Read-only oversight and reports |
| Placement officer | `TNP_OFFICER` | Runs drives and the company directory for the whole college |
| Department coordinator | `TNP_ASSISTANT` | Looks after the students and drive approvals of the branches assigned to them |
| Student | `STUDENT` | Applies to drives |

## Access by page

✓ allowed, — not allowed (redirected to the user's own home page, or 403 for a specific record).
"Own branches" means only the branches assigned to that coordinator. "Own" means only the student's own record.

| Area | Page | Admin | Principal | Officer | Coordinator | Student |
| --- | --- | :---: | :---: | :---: | :---: | :---: |
| **Everyone** | Public home page | ✓ | ✓ | ✓ | ✓ | ✓ |
| | Notifications, change password | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Administrator** | Overview, users, departments, coordinator assignments, activity log | ✓ | — | — | — | — |
| **Principal** | Overview, student records, recruiters, CSV export | ✓ | ✓ | — | — | — |
| **Reports** | Placement report, salary report | ✓ | ✓ | ✓ | ✓ | — |
| **Drives** | Drive list and drive page | ✓ | ✓ | ✓ | ✓ | ✓ |
| | Applicant list on a drive page | ✓ | ✓ | ✓ | Own branches | — |
| | Post a drive | ✓ | — | ✓ | Own branches | — |
| | Edit a drive | ✓ | — | ✓ | — | — |
| | Officer overview | ✓ | — | ✓ | — | — |
| **Applications** | All applications list | ✓ | ✓ (read-only) | ✓ | — | — |
| | Move an applicant to another round | ✓ | — | ✓ | Own branches | — |
| | Apply, withdraw | — | — | — | — | ✓ |
| **Students** | Coordinator overview, roster, add and edit student | ✓ | — | — | Own branches | — |
| | Drive approvals, verify applicants | ✓ | — | — | Own branches | — |
| | Import students, download template | ✓ | — | — | Own branches | — |
| | A student's profile page | ✓ | ✓ | ✓ | Own branches | Own |
| | A student's resume | ✓ | ✓ | ✓ | Own branches | Own |
| **Companies** | Company list and company page | ✓ | ✓ | ✓ | ✓ | ✓ |
| | Add or edit a company | ✓ | — | ✓ | — | — |
| **Study library** | Browse | ✓ | ✓ | ✓ | ✓ | College-wide and own branch |
| | Add material | ✓ | — | ✓ | Own branches | — |
| **Student pages** | Home, open drives, my applications, profile, career assistant | — | — | — | — | ✓ |

Notes:

- **The seeded administrator is a superuser**, and superusers pass every role check. The admin can open student pages too, but sees a "no academic record" page there because admins have no student profile.
- **Posting as a coordinator**: the drive is limited to the coordinator's own branches (any other branch ticked in the form is dropped) and is approved for those branches straight away. Drives posted by the officer start as pending for every branch.
- **Principal** sees the applications list without the update buttons.
- **The demo role switcher** (`/auth/switch/<role>/`) works only when `DEMO_MODE` is on and only as a POST from the sign-in page or sidebar. With `DEMO_MODE` off it returns 404.

## How it's enforced

**Role decorators** in `apps/accounts/decorators.py` wrap every view:

```python
@role_required(['TNP_OFFICER', 'TNP_ASSISTANT', 'ADMIN'])
def update_stage_view(request, app_id):
    ...
```

A user without one of the listed roles is redirected to their own home page with a message. Shortcuts exist for the common cases: `admin_required`, `principal_required` (principal or admin), `tpo_required` (officer or admin), `assistant_required` (coordinator or admin) and `student_required` (students only).

**Branch scoping** for coordinators happens inside the views. `get_assistant_departments(user)` returns the branches assigned to a coordinator (or every branch for central staff), and each coordinator query filters on it:

```python
assigned = get_assistant_departments(request.user)
if application.student.department not in assigned:
    return HttpResponseForbidden(...)
```

**Students' own records**: student profile pages and resume downloads compare the requested student with the signed-in user and return 403 for anyone else's.

**Files**: resumes are never served from `/media/`. Requests for `/media/resumes/...` return 404, and the download view applies the rules above before streaming the file.

**Forms**: every action that changes data is a POST protected by Django's CSRF token.

These rules are covered by `tests/test_permissions.py`, `tests/test_department_scoping.py`, `tests/test_security_audit.py` and `tests/test_fixes.py`.
