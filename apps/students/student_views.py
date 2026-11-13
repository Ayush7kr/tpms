from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from apps.accounts.decorators import student_required
from apps.students.models import StudentProfile, PlacementStatus
from apps.placements.models import JobOpening
from apps.placements.services.eligibility import EligibilityEngine
from apps.applications.models import JobApplication
from apps.study_materials.models import StudyMaterial


@student_required
def dashboard_view(request):
    """
    Candidate Personal Dashboard:
    - Overview of eligibility status
    - Summary of ongoing drives with eligibility flags
    - Live recruitment stage tracker for active applications
    - Recent study materials
    """
    profile = getattr(request.user, 'student_profile', None)
    if not profile:
        profile = StudentProfile.objects.filter(user=request.user).first()
    if not profile:
        from apps.departments.models import Department
        default_dept = Department.objects.first()
        if not default_dept:
            default_dept = Department.objects.create(code='GEN', name='General Engineering')
        profile = StudentProfile.objects.create(
            user=request.user,
            department=default_dept,
            roll_number=f"ROLL{request.user.id}",
            prn_number=f"PRN{request.user.id}",
            batch_year=2025,
            degree='B.Tech',
            tenth_percentage=Decimal('0.00'),
            twelfth_percentage=Decimal('0.00'),
            graduation_cgpa=Decimal('0.00')
        )

    # Active drives with evaluated eligibility
    active_jobs = JobOpening.objects.filter(status='PUBLISHED').select_related('company').prefetch_related('allowed_departments').order_by('-created_at')

    evaluated_jobs = []
    eligible_count = 0
    for job in active_jobs:
        eval_result = EligibilityEngine.evaluate(profile, job)
        if eval_result['is_eligible']:
            eligible_count += 1
        evaluated_jobs.append({
            'job': job,
            'eval': eval_result
        })

    # Student's submitted applications
    my_applications = JobApplication.objects.filter(student=profile).select_related('job_opening__company').order_by('-applied_at')

    # Prep materials
    prep_materials = StudyMaterial.objects.filter(
        department__isnull=True
    ).order_by('-created_at')[:4]

    return render(request, 'student_panel/dashboard.html', {
        'profile': profile,
        'evaluated_jobs': evaluated_jobs[:5],
        'eligible_count': eligible_count,
        'total_active_jobs': active_jobs.count(),
        'my_applications': my_applications,
        'prep_materials': prep_materials,
        'active_nav': 'dashboard'
    })


@student_required
def eligible_jobs_view(request):
    """
    Explore all active campus drives with real-time programmatic eligibility computation.
    """
    profile = request.user.student_profile
    active_jobs = JobOpening.objects.filter(status='PUBLISHED').select_related('company').prefetch_related('allowed_departments').order_by('-created_at')

    filter_mode = request.GET.get('filter', 'all')  # 'all', 'eligible_only', 'applied'

    evaluated_jobs = []
    for job in active_jobs:
        eval_result = EligibilityEngine.evaluate(profile, job)

        if filter_mode == 'eligible_only' and not eval_result['is_eligible']:
            continue
        if filter_mode == 'applied' and not eval_result['has_applied']:
            continue

        evaluated_jobs.append({
            'job': job,
            'eval': eval_result
        })

    return render(request, 'student_panel/eligible_jobs.html', {
        'profile': profile,
        'evaluated_jobs': evaluated_jobs,
        'filter_mode': filter_mode,
        'active_nav': 'eligible_jobs'
    })


@student_required
def my_applications_view(request):
    """
    Tracks recruitment round stepper for candidate applications.
    """
    profile = request.user.student_profile
    applications = JobApplication.objects.filter(student=profile).select_related('job_opening__company').order_by('-applied_at')

    return render(request, 'student_panel/my_applications.html', {
        'profile': profile,
        'applications': applications,
        'active_nav': 'my_applications'
    })


@student_required
def profile_view(request):
    """
    Candidate academic record, skills, resume upload, and profile view.
    """
    profile = request.user.student_profile

    if request.method == 'POST':
        skills = request.POST.get('skills', '').strip()
        linkedin_url = request.POST.get('linkedin_url', '').strip()
        github_url = request.POST.get('github_url', '').strip()
        resume_file = request.FILES.get('resume')

        profile.skills = skills
        profile.linkedin_url = linkedin_url
        profile.github_url = github_url

        if resume_file:
            if not resume_file.name.lower().endswith('.pdf'):
                messages.error(request, "Resume must be an uploaded PDF document.")
                return redirect('student_panel:profile')
            profile.resume = resume_file

        profile.save()
        messages.success(request, "Your profile and resume have been updated.")
        return redirect('student_panel:profile')

    return render(request, 'student_panel/profile.html', {
        'profile': profile,
        'active_nav': 'profile'
    })
