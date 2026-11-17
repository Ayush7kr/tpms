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


STEP_ORDER = ['APPLIED', 'SHORTLISTED', 'ASSESSMENT', 'TECHNICAL_ROUND', 'HR_ROUND', 'OFFERED']
STEP_LABELS = ['Applied', 'Shortlisted', 'Test', 'Technical', 'HR', 'Offer']


def application_steps(app):
    """Progress steps for one application, as a list of {label, state}."""
    if app.stage in STEP_ORDER:
        current = STEP_ORDER.index(app.stage)
        steps = []
        for i, label in enumerate(STEP_LABELS):
            if i < current or app.stage == 'OFFERED':
                state = 'completed'
            elif i == current:
                state = 'active'
            else:
                state = ''
            steps.append({'label': label, 'state': state, 'n': i + 1})
        return steps
    # Rejected or withdrawn: only the first step is known to be done.
    steps = [{'label': l, 'state': '', 'n': i + 1} for i, l in enumerate(STEP_LABELS)]
    steps[0]['state'] = 'completed'
    if app.stage == 'REJECTED':
        steps[-1] = {'label': 'Not selected', 'state': 'rejected', 'n': 6}
    return steps


def initials(name):
    words = [w for w in name.replace('&', ' ').split() if w[0].isalnum()]
    return ''.join(w[0] for w in words[:2]).upper() or '?'


@student_required
def dashboard_view(request):
    """
    Candidate Personal Dashboard:
    - Overview of eligibility status
    - Summary of ongoing drives with eligibility flags
    - Live recruitment stage tracker for active applications
    - Recent study materials
    """
    profile = request.user.student_profile

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
    my_applications = list(JobApplication.objects.filter(student=profile).select_related('job_opening__company').order_by('-applied_at'))
    for app in my_applications:
        app.steps = application_steps(app)
    active_applications = [a for a in my_applications if a.stage not in ('WITHDRAWN', 'REJECTED')]
    for item in evaluated_jobs:
        item['initials'] = initials(item['job'].company.name)
    open_to_apply = [i for i in evaluated_jobs if i['eval']['can_apply']]

    # Prep materials
    from django.db.models import Q
    prep_materials = StudyMaterial.objects.filter(
        Q(department__isnull=True) | Q(department=profile.department)
    ).order_by('-created_at')[:4]

    return render(request, 'student_panel/dashboard.html', {
        'profile': profile,
        'evaluated_jobs': evaluated_jobs[:5],
        'open_to_apply': open_to_apply,
        'active_applications': active_applications,
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

    every = [
        {'job': job, 'eval': EligibilityEngine.evaluate(profile, job), 'initials': initials(job.company.name)}
        for job in active_jobs
    ]
    counts = {
        'all': len(every),
        'eligible_only': sum(1 for i in every if i['eval']['is_eligible']),
        'applied': sum(1 for i in every if i['eval']['has_applied']),
    }
    if filter_mode == 'eligible_only':
        evaluated_jobs = [i for i in every if i['eval']['is_eligible']]
    elif filter_mode == 'applied':
        evaluated_jobs = [i for i in every if i['eval']['has_applied']]
    else:
        filter_mode = 'all'
        evaluated_jobs = every

    return render(request, 'student_panel/eligible_jobs.html', {
        'counts': counts,
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
    applications = list(JobApplication.objects.filter(student=profile).select_related('job_opening__company').order_by('-applied_at'))
    for app in applications:
        app.steps = application_steps(app)
        app.can_reapply = (
            app.stage == 'WITHDRAWN' and app.job_opening.status == 'PUBLISHED'
            and not app.job_opening.is_deadline_passed
        )

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

        from django.core.validators import URLValidator
        from django.core.exceptions import ValidationError
        url_check = URLValidator(schemes=['http', 'https'])
        for label, value in (('LinkedIn', linkedin_url), ('GitHub', github_url)):
            if value:
                try:
                    url_check(value)
                except ValidationError:
                    messages.error(request, f"{label} link must be a full web address starting with https://")
                    return redirect('student_panel:profile')

        profile.skills = ", ".join(s.strip() for s in skills.split(',') if s.strip())
        profile.linkedin_url = linkedin_url or None
        profile.github_url = github_url or None

        if resume_file:
            if not resume_file.name.lower().endswith('.pdf'):
                messages.error(request, "Resume must be a PDF file.")
                return redirect('student_panel:profile')
            if resume_file.size > 5 * 1024 * 1024:
                messages.error(request, "Resume must be smaller than 5 MB.")
                return redirect('student_panel:profile')
            profile.resume = resume_file

        profile.save()
        messages.success(request, "Profile saved.")
        return redirect('student_panel:profile')

    return render(request, 'student_panel/profile.html', {
        'profile': profile,
        'active_nav': 'profile'
    })
