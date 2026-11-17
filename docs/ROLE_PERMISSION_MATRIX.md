# TPMS — Role & Permission Matrix (RBAC Specification)

This document establishes the definitive Role-Based Access Control (RBAC) authorization matrix for the Training and Placement Management System (TPMS).

---

## 1. System Roles Summary
1. **ADMIN** (`ADMIN`): Super-administrative controller; manages user credentials, departments, and assistant allocations.
2. **PRINCIPAL** (`PRINCIPAL`): Executive viewer; monitors institutional macro trends, department comparisons, and placement metrics.
3. **TnP OFFICER** (`TNP_OFFICER`): Central corporate director; oversees company relationships, posts campus drives, publishes global preparation resources, and orchestrates interview rounds.
4. **TnP ASSISTANT** (`TNP_ASSISTANT`): Department-scoped operational coordinator; onboards student records for their department via manual entry or bulk CSV/Excel, approves company drives for their branch, verifies candidate applications, and posts localized prep materials.
5. **STUDENT** (`STUDENT`): Candidate self-service user; maintains academic profile and resume, explores active drives, checks programmatic eligibility, applies with 1-click, tracks interview stages, and accesses prep resources.

---

## 2. Granular Permission Matrix

| Capability / Resource Action | Admin | Principal | TnP Officer | TnP Assistant | Student | Enforcement Layer |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Authentication & Profile** |
| Access Public Landing & Login | Yes | Yes | Yes | Yes | Yes | Public Route |
| Quick Switch Demo Persona | Yes | Yes | Yes | Yes | Yes | POST Only (`DEMO_MODE=True`) |
| Update Own Password & Basic Profile | Yes | Yes | Yes | Yes | Yes | Session User Check |
| **User & Staff Governance** |
| Add / Edit Staff Account | **Yes** | No | No | No | No | `@role_required(['ADMIN'])` |
| Toggle Staff Active State | **Yes** | No | No | No | No | `@role_required(['ADMIN'])` (POST Only, Self-Protected) |
| Reset Staff Password | **Yes** | No | No | No | No | `@role_required(['ADMIN'])` |
| **Department Management** |
| Create / Edit / Deactivate Department | **Yes** | View Only | View Only | View Only | View Only | `@role_required(['ADMIN'])` |
| Assign Department to TnP Assistant | **Yes** | No | No | No | No | `@role_required(['ADMIN'])` |
| **Student Roster Management** |
| Add Single Student Manually | No | No | View Only | **Yes (Assigned Dept)** | No | `@role_required(['TNP_ASSISTANT'])` + Dept Check |
| Bulk Import Students (CSV / Excel) | No | No | No | **Yes (Assigned Dept)** | No | `@role_required(['TNP_ASSISTANT'])` + Atomic Ingestion |
| Edit Student Academic Information | No | No | View Only | **Yes (Assigned Dept)** | No | `@role_required(['TNP_ASSISTANT'])` + Dept Check |
| Update Student Resume & Skills | No | No | No | No | **Yes (Own Profile)** | `@role_required(['STUDENT'])` + ID Match |
| Download Student Resume PDF | View (All) | View (All) | **Yes** | **Yes (Assigned Dept)** | **Yes (Own Resume)** | `students:download_resume` View Check (Media Direct URL 404) |
| View Student Full Profiles | View (All) | View (All) | View (All) | **View (Assigned Dept)** | View (Own Only) | Multi-tenant ORM Filter |
| **Corporate Directory** |
| Add / Edit / Deactivate Company | No | View Only | **Yes** | View Only | View (Public Info) | `@role_required(['TNP_OFFICER'])` |
| Manage Recruiter POC Contacts | No | View Only | **Yes** | View Only | No | `@role_required(['TNP_OFFICER'])` |
| **Job Openings & Placement Drives** |
| Create / Edit Job Opening | No | View Only | **Yes** | No | No | `@role_required(['TNP_OFFICER'])` |
| Set Eligibility Cut-Offs (% & CGPA) | No | View Only | **Yes** | No | No | `@role_required(['TNP_OFFICER'])` |
| Approve / Reject Job for Department | No | No | No | **Yes (Assigned Dept)** | No | `@role_required(['TNP_ASSISTANT'])` + Dept Scope |
| Close / Cancel Job Opening | No | No | **Yes** | No | No | `@role_required(['TNP_OFFICER'])` |
| **Eligibility & Application Pipeline** |
| View Active Jobs with Live Eligibility | No | No | View All | View (Approved) | **Yes (Real-Time Cutoff)** | Eligibility Service Engine |
| Submit 1-Click Job Application | No | No | No | No | **Yes (If Eligible)** | `@role_required(['STUDENT'])` + Cut-Off Check |
| Verify Candidate Marks & Documents | No | No | No | **Yes (Assigned Dept)** | No | `@role_required(['TNP_ASSISTANT'])` + Dept Scope |
| Advance Candidate Recruitment Round | No | No | **Yes** | **Yes (Assigned Dept)** | No | `@role_required(['TNP_OFFICER', 'TNP_ASSISTANT'])` |
| Mark Student Placed & Record CTC | No | No | **Yes** | **Yes (Assigned Dept)** | No | Service-level Status Sync |
| **Preparation & Study Materials** |
| Upload Global Study Material | No | No | **Yes** | No | No | `@role_required(['TNP_OFFICER'])` |
| Upload Dept-Specific Material | No | No | **Yes** | **Yes (Assigned Dept)** | No | `@role_required(['TNP_OFFICER', 'TNP_ASSISTANT'])` |
| Download / View Study Resources | No | View Only | View Only | View Only | **Yes** | Queryset filter active resources |
| **AI Career & Placement Assistant** |
| Access AI Career Assistant Interface | No | No | No | No | **Yes (Student Portal)** | `@role_required(['STUDENT'])` |
| Query AI Assistant / Generate Roadmap | No | No | No | No | **Yes (Rate Limited)** | `@student_required` + AJAX POST |
| Manage Mentorship Threads & History | No | No | No | No | **Yes (Own Threads Only)** | `@student_required` + Student Ownership |
| **Analytics, Reports & Audit** |
| View Executive Placement Dashboards | **Yes** | **Yes** | **Yes** | **Yes (Dept Only)** | No | Queryset scope & View Decorator |
| Export Placement Data (CSV / Excel) | **Yes** | **Yes** | **Yes** | **Yes (Dept Only)** | No | Service Layer Exporter |
| Inspect System Audit Log | **Yes** | View Only | No | No | No | `@role_required(['ADMIN'])` |

---

## 3. Enforcement Implementation Standards

### 3.1 Python View Decorator Architecture
```python
# accounts/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied

def login_required_custom(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in to access this resource.")
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role not in allowed_roles:
                messages.error(request, "Access Denied: You do not have permission for this module.")
                return redirect(request.user.get_dashboard_url())
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
```

### 3.2 Department Isolation Query Helper
```python
def get_assistant_department_ids(user):
    """
    Returns the list of Department primary keys assigned to a TnP Assistant.
    If the user is an Admin, Principal, or TPO, returns all department IDs.
    """
    if user.role in ['ADMIN', 'PRINCIPAL', 'TNP_OFFICER']:
        return list(Department.objects.values_list('id', flat=True))
    elif user.role == 'TNP_ASSISTANT':
        return list(user.assistant_departments.values_list('department_id', flat=True))
    return []
```
