from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from apps.accounts.decorators import student_required, login_required_custom, role_required
from apps.departments.assistant_views import get_assistant_departments
from apps.placements.models import JobOpening
from apps.placements.services.eligibility import EligibilityEngine
from apps.applications.models import JobApplication, ApplicationStage, VerificationStatus
from apps.students.models import StudentProfile, PlacementStatus
from apps.notifications.models import Notification
from apps.audit.models import AuditLog


@student_required
def apply_view(request, job_id):
    """
    1-Click Application Submission Handler.
    Programmatically verifies eligibility criteria and deadline before persisting application.
    Enforces strict duplicate prevention.
    """
    profile = request.user.student_profile
    job = get_object_or_404(JobOpening, id=job_id)

    if request.method == 'POST':
        # Check existing submission
        if JobApplication.objects.filter(job_opening=job, student=profile).exists():
            messages.warning(request, f"You have already applied for {job.title} at {job.company.name}.")
            return redirect('student_panel:my_applications')

        # Evaluate eligibility criteria
        eval_result = EligibilityEngine.evaluate(profile, job)

        if not eval_result['can_apply']:
            if eval_result['is_deadline_passed']:
                messages.error(request, "Application window has closed for this campus drive.")
            elif job.status != 'PUBLISHED':
                messages.error(request, f"This campus drive is currently {job.get_status_display().lower()} and not accepting submissions.")
            else:
                reasons = " | ".join(eval_result['failed_criteria'])
                messages.error(request, f"You do not meet the cut-off criteria: {reasons}")
            return redirect('student_panel:eligible_jobs')

        # Persist 1-Click Application
        application = JobApplication.objects.create(
            job_opening=job,
            student=profile,
            stage=ApplicationStage.APPLIED,
            verification_status=VerificationStatus.PENDING
        )

        # Notify Student
        Notification.objects.create(
            recipient=request.user,
            title=f"Application Submitted: {job.company.name}",
            message=f"Your application for {job.title} ({job.package_ctc} LPA) has been submitted and is pending verification.",
            action_url=f"/student/applications/"
        )

        AuditLog.objects.create(
            user=request.user,
            action="JOB_APPLICATION_SUBMIT",
            entity_type="JobApplication",
            entity_id=str(application.id),
            details=f"Student {profile.roll_number} applied for {job.title} at {job.company.name}"
        )

        messages.success(request, f"Successfully applied for {job.title} at {job.company.name}!")
        return redirect('student_panel:my_applications')

    return redirect('student_panel:eligible_jobs')


@student_required
def withdraw_application_view(request, application_id):
    """
    Candidate Application Withdrawal.
    Allows students to withdraw an application before selection progression begins.
    """
    profile = request.user.student_profile
    application = get_object_or_404(JobApplication, id=application_id, student=profile)

    if request.method == 'POST':
        if application.stage != ApplicationStage.APPLIED:
            messages.error(request, "Applications that have advanced past the initial submission stage cannot be self-withdrawn.")
            return redirect('student_panel:my_applications')

        application.stage = ApplicationStage.WITHDRAWN
        application.remarks = f"Withdrawn by candidate on {timezone.now().strftime('%b %d, %Y %H:%M')}."
        application.stage_updated_at = timezone.now()
        application.save()

        AuditLog.objects.create(
            user=request.user,
            action="APPLICATION_WITHDRAWN",
            entity_type="JobApplication",
            entity_id=str(application.id),
            details=f"Student {profile.roll_number} withdrew application for {application.job_opening.title} at {application.job_opening.company.name}"
        )

        messages.info(request, f"Your application for {application.job_opening.title} has been successfully withdrawn.")
        return redirect('student_panel:my_applications')

    return redirect('student_panel:my_applications')


@role_required(['TNP_OFFICER', 'ADMIN', 'PRINCIPAL'])
def central_tracker_view(request):
    """
    Central Application Pipeline Tracker for institutional leadership and TPO.
    Supports instant multi-field search and pagination.
    """
    stage_filter = request.GET.get('stage', '')
    company_filter = request.GET.get('company', '')
    query = request.GET.get('q', '').strip()

    applications_qs = JobApplication.objects.select_related(
        'student__user', 'student__department', 'job_opening__company'
    ).order_by('-applied_at')

    if stage_filter:
        applications_qs = applications_qs.filter(stage=stage_filter)
    if company_filter:
        applications_qs = applications_qs.filter(job_opening__company_id=company_filter)
    if query:
        applications_qs = applications_qs.filter(
            Q(student__roll_number__icontains=query) |
            Q(student__user__first_name__icontains=query) |
            Q(student__user__last_name__icontains=query) |
            Q(student__user__email__icontains=query) |
            Q(job_opening__title__icontains=query) |
            Q(job_opening__company__name__icontains=query)
        )

    from apps.companies.models import Company
    companies = Company.objects.filter(is_active=True).order_by('name')

    paginator = Paginator(applications_qs, 15)
    page_number = request.GET.get('page')
    applications = paginator.get_page(page_number)

    return render(request, 'applications/central_tracker.html', {
        'applications': applications,
        'companies': companies,
        'stages': ApplicationStage.choices,
        'selected_stage': stage_filter,
        'selected_company': company_filter,
        'query': query,
        'total_count': applications_qs.count(),
        'active_nav': 'applications'
    })


@role_required(['TNP_OFFICER', 'TNP_ASSISTANT', 'ADMIN'])
def update_stage_view(request, application_id):
    """
    Recruitment Round Progression:
    Advances candidate through Applied -> Shortlisted -> Assessment -> Technical -> HR -> Offered / Rejected.
    Automatically syncs StudentProfile.placement_status = 'PLACED' upon offer.
    Reverses placement status if offer is revoked.
    """
    application = get_object_or_404(
        JobApplication.objects.select_related('student__user', 'student__department', 'job_opening__company'),
        id=application_id
    )

    if request.user.role == 'TNP_ASSISTANT':
        assigned_depts = get_assistant_departments(request.user)
        if application.student.department not in assigned_depts:
            return HttpResponseForbidden("Access denied: You are not authorized to update candidates outside your assigned department.")

    if application.stage == ApplicationStage.WITHDRAWN:
        messages.error(request, "This application was withdrawn by the candidate and cannot be advanced.")
        return redirect('placements:drive_detail', job_id=application.job_opening.id)

    if application.job_opening.status == 'CANCELLED':
        messages.error(request, "This campus drive has been cancelled. Applications cannot be progressed.")
        return redirect('placements:drive_detail', job_id=application.job_opening.id)

    if request.method == 'POST':
        new_stage = request.POST.get('stage')
        remarks = request.POST.get('remarks', '').strip()

        valid_stages = [s[0] for s in ApplicationStage.choices if s[0] != ApplicationStage.WITHDRAWN]
        if new_stage not in valid_stages:
            messages.error(request, "Invalid recruitment stage.")
            return redirect('applications:update_stage', application_id=application.id)

        old_stage = application.stage
        application.stage = new_stage
        application.remarks = remarks
        application.stage_updated_at = timezone.now()
        application.save()

        # Automatic status sync upon placement offer release
        if new_stage == ApplicationStage.OFFERED:
            student = application.student
            student.placement_status = PlacementStatus.PLACED
            student.placed_company = application.job_opening.company
            student.salary_package = application.job_opening.package_ctc
            student.save()

            Notification.objects.create(
                recipient=student.user,
                title=f"🎉 Congratulations! Placement Offer from {application.job_opening.company.name}",
                message=f"You have been officially selected for {application.job_opening.title} with a compensation package of {application.job_opening.package_ctc} LPA!",
                action_url="/student/profile/"
            )
        elif old_stage == ApplicationStage.OFFERED and new_stage != ApplicationStage.OFFERED:
            # Revoke offer and revert placement status
            student = application.student
            student.placement_status = PlacementStatus.UNPLACED
            student.placed_company = None
            student.salary_package = None
            student.save()

        AuditLog.objects.create(
            user=request.user,
            action=f"STAGE_UPDATE_{new_stage}",
            entity_type="JobApplication",
            entity_id=str(application.id),
            details=f"Candidate {application.student.roll_number} moved from {old_stage} to {new_stage} for {application.job_opening.title}"
        )

        messages.success(request, f"Updated candidate {application.student.roll_number} status to {application.get_stage_display()}.")
        return redirect('placements:drive_detail', job_id=application.job_opening.id)

    return render(request, 'applications/update_stage.html', {
        'application': application,
        'stages': [s for s in ApplicationStage.choices if s[0] != ApplicationStage.WITHDRAWN],
        'active_nav': 'applications'
    })
