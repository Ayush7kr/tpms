# Requirements

Each requirement from the [project brief](project-brief.pdf), whether the portal meets it, and where.

**Status**: **Met**, **Partly met** (the gap is described), or **Not met**.

## Summary

| | Count |
| --- | ---: |
| Met | 37 |
| Partly met | 7 |
| Not met | 1 |

The gaps are listed together under [Open items](#open-items) at the end.

## Authentication

| Requirement | Status | Where |
| --- | --- | --- |
| Email-based login | Met | Sign-in uses email and password (`apps/accounts/views.py`) |
| Email verification | Partly met | Accounts are created by the administrator or a coordinator with a college email, so there is no self-registration to verify. No verification email is sent. |
| Secure password storage | Met | Django PBKDF2 hashing; tested in `tests/test_auth.py` |
| Role-based access control | Met | Role decorators and branch scoping; see [PERMISSIONS.md](PERMISSIONS.md) |

## Administrator

| Requirement | Status | Where |
| --- | --- | --- |
| Add, edit, delete placement officers, coordinators, principal | Met | **Users**. Self-deactivation, self-demotion and deleting the last admin are blocked. |
| Manage departments | Met | **Departments**. A branch with students can't be deleted. |
| Assign coordinators to departments | Met | **Coordinator assignments** |
| View placement statistics | Met | **Placement report** and the overview's students-by-branch table |
| Dashboard counts: users, departments, students, current job openings, placed students | Partly met | Users, departments, students and placed students are shown. Open drives aren't on the admin overview (they are in the placement report), and student counts are for all years, not split by academic year. |
| Dashboard notifications | Met | Bell in the top bar and the **Notifications** page |

## Placement officer

| Requirement | Status | Where |
| --- | --- | --- |
| Manage companies | Met | **Companies**: add, edit, view drives per company |
| Post job openings with eligibility criteria (% marks, degree, etc.) | Met | **Post a drive**: CGPA, 10th, 12th, backlogs, branches, batches, degrees |
| Post selection process updates | Met | **Update** on each applicant; the student is notified |
| Upload study materials (PDFs, videos, links), job-wise | Met | **Study material → Add**, optionally linked to a drive |
| View and track applications | Met | **Applications** list and each drive's applicant list |
| Reports | Met | **Placement report** |
| Dashboard counts: students, open drives, placed and unplaced, min / avg / max package | Partly met | All shown on the overview, but not split by academic year |
| Dashboard notifications | Met | Bell and **Notifications** page |

## Department coordinator

| Requirement | Status | Where |
| --- | --- | --- |
| Upload student data department-wise (Excel / CSV or manual) | Met | **Import students** (CSV or `.xlsx`) and **Add student** |
| Post, approve or reject job openings for their department | Met | **Drive approvals**; coordinators can also post drives for their own branches |
| Upload department-wise, job-wise study materials | Met | **Study material → Add**, limited to their branches, optionally linked to a drive |
| Review and verify student applications | Met | **Verify applicants**: verified or mismatch flagged, with notes; flagging notifies the student |
| Post or update selection process results | Met | Round updates for their own branches' applicants |
| Access department-specific reports | Partly met | The coordinator overview shows their branches' placement and package figures. The placement and salary report pages show the whole college, not only their branches. |
| Dashboard counts: students, placed and unplaced, min / avg / max package | Partly met | Shown for their branches; not split by academic year |
| Dashboard notifications | Met | Bell and **Notifications** page |

## Principal

| Requirement | Status | Where |
| --- | --- | --- |
| Monitor the overall system and activities | Met | **Overview**, **Applications** (read-only), **Recruiters** |
| View all department-level reports and analytics | Met | **Overview** charts and branch table, **Salary report**, **Student records** with CSV export |
| Dashboard counts: students, open drives, placed and unplaced, min / avg / max package | Partly met | All shown; not split by academic year |
| Dashboard notifications | Met | Bell and **Notifications** page |

## Student

| Requirement | Status | Where |
| --- | --- | --- |
| View job openings filtered by eligibility | Met | **Open drives** with an *Eligible* filter and the per-cut-off comparison |
| Apply for eligible jobs with a single click | Met | **Apply** (with a confirmation prompt) |
| Track applied companies and statuses | Met | **My applications** with round progress |
| Receive job-related notifications and selection updates | Met | New drives, every round change, offers, flagged marks |
| View and download study materials | Met | **Study material**: college-wide and their branch's material |

## Reports and analytics

| Requirement | Status | Where |
| --- | --- | --- |
| Real-time statistics and visualisation | Met | Chart.js charts on the principal overview and placement report, computed on each page load |
| Company-wise participation records | Met | **Recruiters** (drives and hires per company) and each company's page |
| Drive-wise statistics | Met | Applicant list and rounds on each drive page; **Applications** filtered by company |
| Department-wise statistics | Met | Branch tables on the principal, officer and admin overviews |
| Eligibility filter: 10th percentage | Met | **Student records** filter |
| Eligibility filter: 12th percentage | Met | **Student records** filter |
| Eligibility filter: graduation percentage | Partly met | Filtered by CGPA on a 10-point scale, which is what the records store |
| Eligibility filter: post-graduation percentage | Not met | There is no post-graduation field |
| Placed vs unplaced analytics | Met | Placed against enrolled per branch, placement rate |
| Min / max / average salary reports | Met | **Salary report** |

## Beyond the brief

Built in addition to the requirements:

- Per-cut-off explanation for students, showing exactly which figure misses
- Branch approval step before a drive reaches a branch's students
- Automatic placement status from offers, keeping the better offer when a student has two
- Withdraw and re-apply while a drive is open
- Private resumes, served only through a permission check
- Activity log of important actions
- Career assistant for students (Gemini or built-in guidance)
- Works offline and on phones

## Open items

1. **Year-wise dashboard counts.** Dashboards count all students. Filtering by `TPMS_CURRENT_ACADEMIC_YEAR` or by batch would meet the brief.
2. **Open drives on the admin overview.** Add an open-drives tile.
3. **Coordinator-scoped reports.** Limit the placement and salary report pages to the coordinator's branches.
4. **Post-graduation marks.** Add a post-graduation percentage to student records, the import format, the drive cut-offs and the report filters.
5. **Graduation percentage.** Store or derive a percentage alongside CGPA if the college reports in percentages.
6. **Email verification.** Optionally send a verification or welcome email when an account is created.
