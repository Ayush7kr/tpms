# User guide

How each role uses the portal, screen by screen. Screenshots use the demo data from `python manage.py seed_tpms_data`.

- [Signing in](#signing-in)
- [Students](#students)
- [Placement officer](#placement-officer)
- [Department coordinator](#department-coordinator)
- [Principal](#principal)
- [Administrator](#administrator)
- [Everyone: notifications and password](#everyone-notifications-and-password)

---

## Signing in

The public home page lists the drives that are open right now, with live placement numbers from the database.

![Public home page](screenshots/landing.png)

Everyone signs in with their college email and password at **Sign in**. The portal sends each person to their own workspace based on their role. In demo mode, the sign-in page also has one-click buttons for each role.

![Sign-in page](screenshots/login.png)

Students don't register themselves: their department coordinator creates their account, either one at a time or by importing a spreadsheet. Staff accounts are created by the administrator.

---

## Students

### Home

The home page answers "what can I apply to right now?" The dark tile counts drives the student is eligible for, that are still open, and that they haven't applied to yet. Those drives are listed below it, with the student's current applications and the latest study material on the right.

![Student home](screenshots/student-home.png)

### Open drives

Every published drive appears here with the student's own numbers next to the drive's cut-offs: CGPA, 10th, 12th and active backlogs. A cut-off the student misses is shown in red, so they can see exactly what is holding them back. Branch, batch and degree restrictions appear as a short list under the grid when they apply.

The **Apply** button only appears when the student meets every cut-off, the deadline hasn't passed, and their coordinator has approved the drive for their branch. Use the filter at the top to show all drives, only eligible ones, or only ones already applied to.

![Open drives with cut-off comparison](screenshots/student-drives-cutoffs.png)

Opening a drive shows its full description, dates, bond terms and the same cut-off comparison.

![Drive detail for a student](screenshots/student-drive-detail.png)

### My applications

Each application shows where it stands: applied, shortlisted, online test, technical interview, HR interview, offer. It also shows whether the coordinator has verified the student's marks, and any notes from the placement office.

A student can **withdraw** while an application is still at the "applied" stage. If the drive is still open afterwards, an **Apply again** button appears.

![Application tracking](screenshots/student-applications.png)

### Profile and resume

Marks are read-only for students; the coordinator maintains them. Students upload their resume (PDF, up to 5 MB), list their skills, and add LinkedIn and GitHub links. Recruiters see these with each application.

![Profile and resume](screenshots/student-profile.png)

### Career assistant

A chat assistant that knows the student's record, skills and the drives open to them. Students can ask how to prepare for a particular company, what to add to their resume, or for a study plan. The shortcut buttons above the message box fill in common questions.

With a Gemini API key configured, answers come from Google's model. Without one, the assistant answers from built-in guidance and says so at the end of each reply.

![Career assistant](screenshots/career-assistant.png)

---

## Placement officer

### Overview

Counts for students, open drives, placed students and applications, the lowest, average and highest package so far, recent drives, and placement by branch.

![Placement officer overview](screenshots/officer-overview.png)

### Posting a drive

**Post a drive** asks for the company, role, package, location, bond terms, description, deadline and drive date, then the cut-offs: minimum CGPA, 10th and 12th percentages, maximum active backlogs, eligible branches, batches and degrees.

The deadline must be in the future and the drive date can't come before it. Once posted, every student is notified, and each selected branch's coordinator has to approve the drive before that branch's students can apply.

![Post a drive](screenshots/officer-post-drive.png)

A drive can be edited later, including its cut-offs and branches. Adding a branch creates a new approval request for that branch's coordinator.

### A drive and its applicants

The drive page lists cut-offs, branch approvals and every applicant. **Update** moves an applicant to the next round. Choosing **Offer made** marks the student as placed with that package. The student is notified at each change.

![Drive detail with applicants](screenshots/officer-drive-detail.png)

### All applications

Every application across all drives, filterable by company and round.

![All applications](screenshots/officer-applications.png)

### Companies

The company directory: sector, salary band, the recruiter to contact, and the drives each company has run.

![Companies](screenshots/officer-companies.png)

The officer can also publish to the **study library**: PDFs, video links or web links, tagged by topic and optionally linked to a specific drive.

---

## Department coordinator

A coordinator is assigned one or more branches by the administrator, and only ever sees students and applications from those branches.

### Overview

Students and placements in the coordinator's branches, drives waiting for approval, applicants waiting for verification, and package figures for the branch.

![Coordinator overview](screenshots/coordinator-overview.png)

### Students

The branch roster with marks, backlogs and placement status. **Add student** creates one student; **Import students** adds many at once.

![Student roster](screenshots/coordinator-students.png)

### Importing students

Upload a CSV or Excel (.xlsx) file with the columns listed on the page; **Download template** gives a ready-made CSV. Each valid row becomes a student account with the default password `apex@123`. Rows whose email, roll number or PRN already exist are skipped, and rows with invalid marks are reported with the row number so they can be fixed and re-uploaded.

![Import students](screenshots/coordinator-import.png)

### Drive approvals

Every drive posted for the coordinator's branches appears here. A drive only reaches the branch's students once it is approved, and it can be rejected later if needed.

![Drive approvals](screenshots/coordinator-approvals.png)

### Verifying applicants

The coordinator checks each applicant's marks against college records and marks the application **Verified** or **Mismatch flagged**, with an optional note. Flagging notifies the student. Coordinators can also open the applicant's resume here, and move their own branch's students through rounds from the drive page.

![Verify applicants](screenshots/coordinator-verify.png)

---

## Principal

### Placement overview

The placement rate, average and highest package, a chart of placed against enrolled students per branch, the split across salary bands, and a per-branch table.

![Principal overview](screenshots/principal-overview.png)

### Salary report

Lowest, average and highest package across placed students, how many fall in each salary band, and the average package per branch.

![Salary report](screenshots/principal-salary.png)

### Student records

Filter students by branch, batch, placement status, minimum CGPA, minimum 10th or 12th percentage, or a name or roll-number search. **Export CSV** downloads exactly the filtered list.

![Student records](screenshots/principal-records.png)

The principal also sees the recruiter summary (drives and hires per company) and the full applications list, read-only.

---

## Administrator

### Overview

Users, departments, students and placements, students by branch, and the newest accounts.

![Administrator overview](screenshots/admin-overview.png)

### Users

All accounts with their role and status. **Add staff** creates principal, placement officer or coordinator accounts (students are added by coordinators, because they need an academic record). Deactivating an account blocks sign-in but keeps its records. Admins can't deactivate or demote themselves, and the last admin can't be deleted.

![Users](screenshots/admin-users.png)

### Departments and coordinator assignments

Add or edit branches (a branch with students can't be deleted). Assign coordinators to branches; a coordinator can look after several.

![Coordinator assignments](screenshots/admin-assignments.png)

### Activity log

Sign-ins, account and department changes, imports, drive posts and edits, approvals, applications and round changes, with who did it and when.

![Activity log](screenshots/admin-activity-log.png)

---

## Everyone: notifications and password

The bell in the top bar shows unread notifications. Some are personal (your application moved to a new round) and some go to a whole role (a new drive was posted). **Mark all as read** clears both.

**Change password** in the sidebar needs the current password and a new one of at least 8 characters.
