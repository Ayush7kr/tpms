import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, FileResponse, Http404
from django.contrib import messages
from apps.accounts.decorators import assistant_required, login_required_custom
from apps.accounts.models import UserRole
from apps.departments.assistant_views import get_assistant_departments
from apps.departments.models import Department
from apps.students.models import StudentProfile
from apps.students.services.bulk_import import BulkStudentImportService
from apps.audit.models import AuditLog


@assistant_required
def bulk_import_view(request):
    """
    Handles CSV and Excel bulk student ingestion with duplicate detection and department scoping.
    Strictly NO Django Forms.
    """
    assigned_depts = get_assistant_departments(request.user)

    if request.method == 'POST':
        department_id = request.POST.get('department_id')
        uploaded_file = request.FILES.get('student_file')

        if not department_id:
            messages.error(request, "Please select the target department.")
            return redirect('students:bulk_import')

        if not uploaded_file:
            messages.error(request, "Please choose a CSV or Excel (.xlsx) file to upload.")
            return redirect('students:bulk_import')

        dept = get_object_or_404(assigned_depts, id=department_id)

        result = BulkStudentImportService.parse_file(uploaded_file, department=dept)

        if result['success']:
            AuditLog.objects.create(
                user=request.user,
                action="BULK_STUDENT_IMPORT",
                entity_type="StudentProfile",
                details=f"Imported {result['created_count']} students into {dept.code} ({result['skipped_count']} skipped)"
            )

            messages.success(
                request,
                f"Successfully onboarded {result['created_count']} students into {dept.code}! ({result['skipped_count']} duplicate records skipped)."
            )
            return render(request, 'students/bulk_import.html', {
                'assigned_depts': assigned_depts,
                'result': result,
                'active_nav': 'bulk_import'
            })
        else:
            messages.error(request, result.get('error', 'Import failed.'))
            return render(request, 'students/bulk_import.html', {
                'assigned_depts': assigned_depts,
                'result': result,
                'active_nav': 'bulk_import'
            })

    return render(request, 'students/bulk_import.html', {
        'assigned_depts': assigned_depts,
        'active_nav': 'bulk_import'
    })


@assistant_required
def download_template_view(request, format_type):
    """
    Generates a pre-formatted CSV template with standard column headers for bulk onboarding.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tpms_student_import_template.csv"'

    writer = csv.writer(response)
    # Header row
    writer.writerow([
        'roll_number', 'prn_number', 'first_name', 'last_name', 'email', 'phone',
        'gender', 'batch_year', 'degree', 'tenth_percentage', 'twelfth_percentage',
        'graduation_cgpa', 'active_backlogs', 'skills'
    ])
    # Sample row
    writer.writerow([
        '21CSE101', 'PRN21001', 'Rohan', 'Sharma', 'rohan.sharma@apex.edu.in', '9876543210',
        'MALE', '2025', 'B.Tech', '88.50', '85.20', '8.45', '0', 'Python, Django, React, SQL'
    ])
    writer.writerow([
        '21CSE102', 'PRN21002', 'Sneha', 'Patel', 'sneha.patel@apex.edu.in', '9876543211',
        'FEMALE', '2025', 'B.Tech', '92.00', '89.40', '9.10', '0', 'Java, Spring Boot, AWS, Docker'
    ])

    return response


@login_required_custom
def student_detail_view(request, student_id):
    """
    Detailed candidate profile inspection with role and department-based authorization.
    - Students can only view their own profile.
    - Assistants can only view students in their assigned departments.
    - Admin, Principal, TPO can view all students.
    """
    student = get_object_or_404(
        StudentProfile.objects.select_related('user', 'department', 'placed_company'),
        id=student_id
    )

    if request.user.role == UserRole.STUDENT and student.user != request.user:
        return HttpResponseForbidden("Access denied: You are only authorized to view your own candidate profile.")

    if request.user.role == UserRole.TNP_ASSISTANT:
        assigned_depts = get_assistant_departments(request.user)
        if student.department not in assigned_depts:
            return HttpResponseForbidden("Access denied: Candidate belongs to another academic department.")

    applications = student.applications.select_related('job_opening__company').order_by('-applied_at')

    return render(request, 'students/student_detail.html', {
        'student': student,
        'applications': applications,
        'active_nav': 'students'
    })


@login_required_custom
def student_resume_download_view(request, student_id):
    """
    Secure resume download handler.
    Guarantees that files cannot be downloaded without authenticating and possessing valid access rights.
    """
    student = get_object_or_404(
        StudentProfile.objects.select_related('user', 'department'),
        id=student_id
    )

    if request.user.role == UserRole.STUDENT and student.user != request.user:
        return HttpResponseForbidden("Access denied: You cannot access resumes of other candidates.")

    if request.user.role == UserRole.TNP_ASSISTANT:
        assigned_depts = get_assistant_departments(request.user)
        if student.department not in assigned_depts:
            return HttpResponseForbidden("Access denied: Candidate belongs to another department.")

    if not student.resume:
        raise Http404("No resume uploaded for this student.")

    try:
        return FileResponse(
            student.resume.open('rb'),
            content_type='application/pdf',
            filename=f"{student.roll_number}_resume.pdf"
        )
    except FileNotFoundError:
        raise Http404("Resume file not found on disk storage.")
