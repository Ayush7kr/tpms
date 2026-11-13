# TPMS — Phase 3 Implementation Plan: Functional Completion, UI/UX Refinement, and Integration Testing

**Institution:** Apex Institute of Technology  
**Project:** Training and Placement Management System (TPMS)  
**Author:** Senior Django Developer, Frontend Engineer & QA Architect  
**Date:** November 2026  
**Status:** Approved for Implementation  

---

## 1. Executive Objectives

Following the Phase 2 codebase audit, Phase 3 focuses on completing all remaining functional requirements, hardening business logic edges, optimizing data performance, and ensuring consistent enterprise UI/UX across all five role portals (Admin, Principal, TPO, TnP Assistant, Student).

The primary objectives are:
1. **Functional Completeness:** Close all functional gaps identified against `The Training and Placement Management System.pdf`.
2. **Business Workflow Integrity:** Support full edge cases including application withdrawal, drive cancellation notifications, expired deadline protection, inactive account session eviction, and invalid round transitions.
3. **UI/UX Consistency:** Ensure responsive layouts, professional confirmation dialogs, readable paginated data tables, search/filter bars, and accessible status badges.
4. **Data Integrity & Performance:** Eliminate N+1 queries using `select_related`/`prefetch_related`, implement pagination across large rosters, and guarantee atomic transactions.
5. **Integration Testing:** Expand automated test coverage from 37 tests to 50+ tests covering browser-critical workflows.

---

## 2. Comprehensive Functional Gap Analysis

A rigorous comparison was conducted between the specification document (`The Training and Placement Management System.pdf`) and the existing codebase:

| Item ID | Requirement / Workflow | Current State | Identified Gap / Missing Element | Priority | Planned Resolution |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **GAP-01** | **Application Withdrawal / Opt-Out** | Student can only apply. | Students have no mechanism to withdraw an application before shortlisting if circumstances change. | **HIGH** | Add `WITHDRAWN` to `ApplicationStage`. Add `withdraw_application_view` in `apps/applications/views.py` with confirmation modal in UI. |
| **GAP-02** | **Drive Cancellation Lifecycle** | TPO can edit status to `CANCELLED`. | Applicants are not notified of cancellation, and applications remain in active stages without cancellation banners. | **HIGH** | Trigger cancellation broadcast alert; display cancellation alerts on applicant cards; prevent stage updates on cancelled drives. |
| **GAP-03** | **Invalid Stage Transition Guards** | Any stage can be selected. | No validation prevents moving a `WITHDRAWN` or `OFFERED` application into preliminary rounds, or revoking placement status if offer changes. | **HIGH** | Implement transition rules in `update_stage_view`; sync `placement_status` if offer is reversed. |
| **GAP-04** | **Admin User & Department Deletion** | Admin can only edit / toggle status. | PDF specifies "Add/edit/delete TnP Officer, TnP Assistants, Principal. Manage departments." | **HIGH** | Implement `user_delete_view` (with self-delete guard) and `department_delete_view` (with student/drive integrity guard). |
| **GAP-05** | **Company Detail & Placement History** | Only Company List, Create, Edit. | TPO and Principal cannot view a company's past placement drive history and placed alumni list. | **MEDIUM** | Implement `company_detail_view` with active/past drive roster and hiring statistics. |
| **GAP-06** | **Session Eviction for Deactivated Accounts** | Inactive users blocked at login. | Already-authenticated sessions for deactivated accounts persist until cookie expiry. | **HIGH** | Update `@login_required_custom` and `@role_required` to verify `request.user.is_active` on every request. |
| **GAP-07** | **Pagination on Large Datasets** | Tables load entire querysets. | Roster, application pipeline, drive lists, and audit logs will experience performance degradation at institutional scale. | **MEDIUM** | Implement Django `Paginator` (10-25 items/page) with reusable pagination template controls. |
| **GAP-08** | **Academic Year / Batch Filter on Reports** | Filter by Department & CGPA. | Principal & TPO cannot filter placement metrics by graduating batch year (e.g. 2025, 2026). | **MEDIUM** | Add `batch_year` filter to `department_reports_view` and `placement_stats_view`. |
| **GAP-09** | **UI Confirmation Dialogs & Flash Feedback** | Actions execute on direct click. | Deletions, withdrawals, and drive cancellations need confirmation modals to prevent accidental data loss. | **MEDIUM** | Add custom Bootstrap 5 modal confirmation dialogs for destructive actions. |

---

## 3. Prioritized Implementation Roadmap

### Phase 3.1: Application Lifecycle & Transition Hardening
- Add `ApplicationStage.WITHDRAWN` choice.
- Implement `withdraw_application_view(request, application_id)` in `apps/applications/views.py`.
- Add withdrawal button and modal to `templates/student_panel/my_applications.html`.
- Add validation in `update_stage_view` preventing stage updates on `WITHDRAWN` or `CANCELLED` drives.
- Automatically synchronize `StudentProfile.placement_status = 'UNPLACED'` if an `OFFERED` status is reversed.

### Phase 3.2: Administrative Governance Completeness
- Implement `user_delete_view(request, user_id)` in `apps/accounts/admin_views.py`.
  - Safety rule 1: Admin cannot delete their own account.
  - Safety rule 2: System must retain at least one active Administrator.
- Implement `department_delete_view(request, dept_id)` in `apps/accounts/admin_views.py`.
  - Integrity rule: Department cannot be deleted if it has registered students or placement drives (recommends deactivation instead).
- Add delete buttons with modal confirmation in `users_list.html` and `departments_list.html`.

### Phase 3.3: Corporate Relationship & Detail View
- Implement `company_detail_view(request, company_id)` in `apps/companies/views.py`.
- Register URL `companies:detail` in `apps/companies/urls.py`.
- Create template `templates/companies/company_detail.html` displaying company profile, contact card, active drives, past drives, and hired candidates.

### Phase 3.4: Session & Security Boundary Enforcement
- Update `apps/accounts/decorators.py` to check `request.user.is_active` on every request; immediately log out and redirect deactivated sessions.
- Update `apps/placements/views.py` (`job_edit_view`): when status changes to `CANCELLED`, send notifications to all registered applicants.

### Phase 3.5: Pagination & Performance Optimization
- Add Django `Paginator` across:
  - `apps/departments/assistant_views.py` (`student_roster_view`)
  - `apps/applications/views.py` (`central_tracker_view`)
  - `apps/placements/views.py` (`drives_list_view`)
  - `apps/accounts/admin_views.py` (`users_list_view`, `audit_logs_view`)
  - `apps/accounts/principal_views.py` (`department_reports_view`)
- Create reusable snippet `templates/includes/pagination.html`.

### Phase 3.6: Principal & TPO Analytics Refinements
- Add `batch_year` filter and `placement_status` filter to `department_reports_view`.
- Enable filtered CSV export retaining search parameters.

### Phase 3.7: Automated Integration Testing Suite Expansion
- Expand automated tests in `tests/test_workflows.py`, `tests/test_permissions.py`, and `tests/test_security_audit.py` to cover:
  - Application withdrawal workflow.
  - Session eviction for deactivated accounts.
  - User deletion and department deletion constraints.
  - Reversal of placement status when offer is revoked.
  - Company detail view rendering and drive history.
  - Pagination boundary testing.

---

## 4. Verification & Quality Gates

Each milestone requires verification via:
1. `python manage.py check` (0 issues).
2. `python manage.py test tests` (100% pass rate).
3. Browser-level simulated navigation and form submission tests.
4. Comprehensive audit log verification.
