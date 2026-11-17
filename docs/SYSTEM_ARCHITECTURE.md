# TPMS — System Architecture & Technical Design

## 1. Architectural Style & Design Principles
The Training and Placement Management System (TPMS) follows a **Modular Monolith** architecture built on Python/Django. This architectural pattern was chosen to satisfy the requirements of rapid response times, zero-latency transaction isolation, unified database schema enforcement, and maintenance simplicity without the overhead of microservices.

```
+-------------------------------------------------------------------------------+
|                             CLIENT / BROWSER TIER                             |
|  - Modern SaaS Responsive Interface (Bootstrap 5.3 + Custom CSS)              |
|  - Dynamic Visual Analytics (Chart.js via Canvas)                             |
|  - Vanilla JS Interactivity (Modal Dialogs, CSV Pre-view, File Drag-and-Drop) |
+---------------------------------------+---------------------------------------+
                                        | HTTPS Requests (GET / POST)
                                        | CSRF Token Verification
+---------------------------------------v---------------------------------------+
|                       DJANGO APPLICATION LAYER (CORE RUNTIME)                 |
|                                                                               |
|  [ MIDDLEWARE PIPELINE ]                                                      |
|   ├── SecurityMiddleware & SessionMiddleware                                  |
|   ├── AuthenticationMiddleware & CSRFProtectionMiddleware                     |
|   └── RoleAndDepartmentAccessMiddleware / Decorators                          |
|                                                                               |
|  [ URL DISPATCHER & MODULAR APPS ]                                            |
|   ├── accounts         : Custom User, Auth Views, Session Lifecycle           |
|   ├── core             : Landing Page, Global Layouts, Error Handlers         |
|   ├── departments      : Department Model & Assistant Scoping                 |
|   ├── students         : Profiles, Academics, CSV/Excel Ingestion Engine      |
|   ├── companies        : Corporate Partners & Recruiters Directory            |
|   ├── placements       : Drives, Job Openings, Cut-Off Eligibility Engine     |
|   ├── applications     : 1-Click Apply, Assistant Verification, Stage Stepper |
|   ├── study_materials  : Preparation Kit (PDFs, Videos, External Links)       |
|   ├── notifications    : Role Broadcasts & Student Alerts                     |
|   ├── analytics        : Statistical Aggregations & Report Generators         |
|   └── audit            : System Event Logging & Traceability                  |
|                                                                               |
|  [ LAYERED APPLICATION DESIGN ]                                               |
|   ├── Presentation Views : HTTP parameter extraction, context assembly        |
|   ├── Validator Services : Manual server-side input sanitation & validations  |
|   ├── Business Services  : Eligibility engine, CSV batch parser, stats math   |
|   └── Models / ORM Layer : Declarative relational schemas & querysets         |
+---------------------------------------+---------------------------------------+
                                        | Parameterized SQL Operations
+---------------------------------------v---------------------------------------+
|                            PERSISTENCE & STORAGE TIER                         |
|  - SQLite Relational Database Engine (`db.sqlite3` with WAL Mode)              |
|  - Institutional Media Storage (`media/resumes/`, `media/study_materials/`)   |
|  - Static Assets Delivery (`static/css/`, `static/js/`, `static/img/`)        |
+-------------------------------------------------------------------------------+
```

---

## 2. Django Modular App Breakdown

### 2.1 `accounts`
- **Purpose**: Provides authentication and identity management.
- **Key Components**:
  - `User`: Custom user model inheriting from `AbstractBaseUser` and `PermissionsMixin`.
  - `UserRole`: Enum choices (`ADMIN`, `PRINCIPAL`, `TNP_OFFICER`, `TNP_ASSISTANT`, `STUDENT`).
  - `decorators.py`: Custom security decorators (`@login_required_custom`, `@role_required`, `@department_scoped`).
  - `services/auth_service.py`: Password validation, authentication checks, session assignment.

### 2.2 `core`
- **Purpose**: Public portal and universal presentation components.
- **Key Components**:
  - Landing page view (`views.landing_view`), about, contact, and system information.
  - Base template hierarchy (`templates/base/base.html`, `templates/base/dashboard_base.html`).
  - Custom HTTP 403, 404, and 500 error view handlers.

### 2.3 `departments`
- **Purpose**: Academic department master data and assistant allocation.
- **Key Components**:
  - `Department`: Master model for branches (CSE, IT, ECE, ME, CE, etc.).
  - `AssistantDepartmentAssignment`: Explicit association linking a `TNP_ASSISTANT` user to one or more departments.

### 2.4 `students`
- **Purpose**: Student academic lifecycle, profile maintenance, and bulk data onboarding.
- **Key Components**:
  - `StudentProfile`: 1-to-1 extension of `User` containing institutional roll number, PRN, branch, CGPA, 10th %, 12th %, backlogs, resume path, and placement status.
  - `services/bulk_import.py`: High-performance ingestion pipeline supporting CSV and Excel (`openpyxl`) files with rollback on critical failures and duplicate suppression.

### 2.5 `companies`
- **Purpose**: Corporate relationship registry.
- **Key Components**:
  - `Company`: Employer entity storing name, industry category, website, HR contact person, email, phone, corporate tier, and logo.

### 2.6 `placements`
- **Purpose**: Campus recruitment drives, job openings, and eligibility calculations.
- **Key Components**:
  - `JobOpening`: Job posting entity detailing role title, salary CTC, deadline, and cut-off parameters (Min 10th %, Min 12th %, Min CGPA, Max Backlogs, Allowed Departments).
  - `DepartmentJobApproval`: Per-department review record (`APPROVED`, `PENDING`, `REJECTED`) managed by TnP Assistants.
  - `services/eligibility.py`: Deterministic algorithm evaluating student metrics against job cut-offs with detailed failure explanations.

### 2.7 `applications`
- **Purpose**: Candidate application lifecycle and interview stage progression.
- **Key Components**:
  - `JobApplication`: Application record binding `StudentProfile` to `JobOpening`.
  - `ApplicationStatus`: Progressive stages (`APPLIED`, `SHORTLISTED`, `ASSESSMENT`, `TECHNICAL_ROUND`, `HR_ROUND`, `OFFERED`, `REJECTED`).
  - `VerificationStatus`: Assistant verification state (`PENDING`, `VERIFIED`, `FLAGGED`).

### 2.8 `study_materials`
- **Purpose**: Learning resources and placement preparation repository.
- **Key Components**:
  - `StudyMaterial`: Resource record supporting uploaded documents (PDF), video lectures, and external tutorial URLs, filterable by topic category, department, and company.

### 2.9 `notifications`
- **Purpose**: Real-time communication and in-app event alerts.
- **Key Components**:
  - `Notification`: Target user or role-broadcast alerts for drive announcements, application updates, and schedule notices.

### 2.10 `analytics`
- **Purpose**: Business intelligence, reporting, and dashboard aggregation.
- **Key Components**:
  - `services/analytics_service.py`: Real-time query aggregations for placement percentages, branch-wise hiring rates, and salary distributions (Min/Avg/Max CTC).
  - Data payload generation for Chart.js canvases.

### 2.11 `audit`
- **Purpose**: Compliance tracking and administrative accountability.
- **Key Components**:
  - `AuditLog`: Captures actor, action type, target entity, timestamp, and IP address for critical system actions.

### 2.12 `career_assistant`
- **Purpose**: Personalized conversational AI placement mentorship and career guidance subsystem.
- **Key Components**:
  - `Conversation`: Threaded session model binding student profiles to chat histories with automatic contextual naming.
  - `ChatMessage`: Individual message entities storing sender role (`STUDENT`, `ASSISTANT`), raw markdown content, and timestamps.
  - `AICareerAssistantService`: Orchestration layer integrating Google Gemini REST API (`GEMINI_MODEL`, defaulting to `gemini-flash-latest`) with automatic fallback to an institutional rule-based guidance engine.
  - `CareerContextBuilder`: Assembles real-time academic standing (CGPA, active backlogs), verified technical skills, applied drives, and upcoming campus openings into prompt context.
  - `CareerPromptBuilder`: Formats structured system instructions prompting comprehensive Markdown output (actionable roadmaps, skill gap tables, preparation tips).
  - Presentation: Interactive conversational UI (`career_assistant.html`) with dual-engine Markdown parser (`marked.js` + secure fallback `customSafeMarkdownParser`).

---

## 3. Directory Structure Layout

```
f:\tpms\
│
├── manage.py
├── requirements.txt
├── db.sqlite3
│
├── tpms_project/             # Core Project Configuration
│   ├── __init__.py
│   ├── settings.py           # Configured with custom User model, apps, media
│   ├── urls.py               # Master URL routing
│   ├── asgi.py
│   └── wsgi.py
│
├── docs/                     # Engineering & Architecture Documentation
│   ├── screenshots/          # Architectural & UI visual references
│   ├── PROJECT_OVERVIEW.md
│   ├── REQUIREMENTS_BREAKDOWN.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DATABASE_DESIGN.md
│   ├── ROLE_PERMISSION_MATRIX.md
│   ├── IMPLEMENTATION_ROADMAP.md
│   ├── PROGRESS_REPORT.md
│   └── UI_UX_REFINEMENT_REPORT.md
│
├── apps/                     # Modular Django Applications
│   ├── accounts/
│   ├── core/
│   ├── departments/
│   ├── students/
│   ├── companies/
│   ├── placements/
│   ├── applications/
│   ├── study_materials/
│   ├── notifications/
│   ├── analytics/
│   ├── audit/
│   └── career_assistant/     # AI Placement Mentorship Subsystem
│
├── static/                   # Static Frontend Assets
│   ├── css/
│   │   └── style.css         # Modern Institutional Design System (Ink Navy & Marigold)
│   ├── js/
│   │   └── app.js
│   ├── vendor/               # Bundled Vendor Dependencies (100% Offline Capability)
│   │   ├── bootstrap/        # Bootstrap 5.3 CSS & JS Bundle
│   │   ├── bootstrap-icons/  # Complete vector icon font library
│   │   ├── chartjs/          # Chart.js library
│   │   └── fonts/            # Schibsted Grotesk & Public Sans WOFF2 fonts
│   └── img/
│       └── logo.svg
│
├── templates/                # Custom HTML Templates (Zero Django Forms)
│   ├── base/
│   │   ├── base.html
│   │   └── dashboard_base.html
│   ├── public/
│   │   ├── landing.html
│   │   ├── login.html
│   │   ├── error.html
│   │   └── profile_missing.html
│   ├── admin_panel/
│   ├── principal_panel/
│   ├── tpo_panel/
│   ├── assistant_panel/
│   └── student_panel/
│
├── media/                    # User & Operational Media Storage
│   ├── resumes/              # Protected candidate resumes (served via permission check only)
│   ├── study_materials/
│   └── company_logos/
│
└── tests/                    # Automated Test Suite (77 Tests Total)
    ├── test_auth.py
    ├── test_permissions.py
    ├── test_eligibility.py
    ├── test_bulk_import.py
    ├── test_department_scoping.py
    ├── test_workflows.py
    ├── test_security_audit.py
    ├── test_phase3_integration.py
    └── test_fixes.py
```

---

## 4. Key Security & Performance Engineering Controls

1. **Custom Forms with Manual Server-Side Validation**:
   - Zero reliance on Django `ModelForm` or `Form`.
   - Every POST endpoint parses fields manually from `request.POST` and files from `request.FILES`.
   - Dedicated validator helper modules sanitize string inputs, cast numeric values with boundary checks, and return contextual error dicts.
2. **Multi-Tenant Assistant Scoping**:
   - TnP Assistants can never inspect, export, or modify student records or job approvals outside their assigned departments.
   - Assistant querysets enforce `department_id__in=request.user.assistant_departments.values_list('department_id', flat=True)`.
3. **Database Concurrency & Integrity**:
   - SQLite configured with `WAL` (Write-Ahead Logging) mode for enhanced concurrent read/write performance.
   - All bulk student imports wrapped in `transaction.atomic()` to guarantee clean rollbacks on malformed datasets.
