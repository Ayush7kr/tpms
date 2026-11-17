from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.accounts.decorators import login_required_custom, role_required
from apps.study_materials.models import StudyMaterial, ResourceCategory, ResourceType
from apps.departments.models import Department
from apps.placements.models import JobOpening
from apps.departments.assistant_views import get_assistant_departments
from apps.audit.models import AuditLog


@login_required_custom
def materials_list_view(request):
    """
    Searchable and filterable repository of campus recruitment preparation assets.
    """
    category_filter = request.GET.get('category', '')
    department_filter = request.GET.get('department', '')

    materials = StudyMaterial.objects.select_related('department', 'job_opening__company', 'uploaded_by').order_by('-created_at')

    # Student sees global materials + their department materials
    if request.user.is_student and hasattr(request.user, 'student_profile'):
        student_dept = request.user.student_profile.department
        materials = materials.filter(Q(department__isnull=True) | Q(department=student_dept))

    if category_filter:
        materials = materials.filter(category=category_filter)
    if department_filter:
        materials = materials.filter(department_id=department_filter)

    departments = Department.objects.filter(is_active=True).order_by('code')

    can_upload = request.user.is_tnp_officer or request.user.is_tnp_assistant or request.user.is_admin

    return render(request, 'study_materials/materials_list.html', {
        'materials': materials,
        'categories': ResourceCategory.choices,
        'departments': departments,
        'selected_category': category_filter,
        'selected_dept': department_filter,
        'can_upload': can_upload,
        'active_nav': 'materials'
    })


@role_required(['TNP_OFFICER', 'TNP_ASSISTANT', 'ADMIN'])
def material_upload_view(request):
    """
    Uploads preparation materials (PDFs, video links, external URLs).
    Assistants can scope assets to their assigned departments.
    Strictly NO Django Forms.
    """
    if request.user.is_tnp_assistant:
        departments = get_assistant_departments(request.user)
    else:
        departments = Department.objects.filter(is_active=True).order_by('code')

    jobs = JobOpening.objects.filter(status='PUBLISHED').order_by('-created_at')[:20]

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category = request.POST.get('category')
        resource_type = request.POST.get('resource_type')
        department_id = request.POST.get('department_id')
        job_opening_id = request.POST.get('job_opening_id')
        external_url = request.POST.get('external_url', '').strip()
        file_attachment = request.FILES.get('file_attachment')

        errors = {}
        if not title:
            errors['title'] = 'Material title is required.'
        if not category:
            errors['category'] = 'Please select a resource category.'
        if not resource_type:
            errors['resource_type'] = 'Please select resource type.'

        if resource_type == ResourceType.DOCUMENT_FILE and not file_attachment:
            errors['file_attachment'] = 'Please choose a document file to upload.'
        if resource_type in [ResourceType.VIDEO_LINK, ResourceType.EXTERNAL_URL] and not external_url:
            errors['external_url'] = 'Please provide the external video or website URL.'
        elif external_url and not external_url.startswith(('http://', 'https://')):
            errors['external_url'] = 'Link must start with http:// or https://'
        if category and category not in ResourceCategory.values:
            errors['category'] = 'Please select a resource category.'
        if resource_type and resource_type not in ResourceType.values:
            errors['resource_type'] = 'Please select resource type.'

        if errors:
            return render(request, 'study_materials/material_form.html', {
                'errors': errors,
                'form_data': request.POST,
                'categories': ResourceCategory.choices,
                'resource_types': ResourceType.choices,
                'departments': departments,
                'jobs': jobs,
                'active_nav': 'materials'
            })

        dept_obj = departments.filter(id=department_id).first() if department_id and department_id.isdigit() else None
        if request.user.is_tnp_assistant and dept_obj is None:
            # Assistants publish to their own department only.
            dept_obj = departments.first()
        job_obj = JobOpening.objects.filter(id=job_opening_id).first() if job_opening_id and job_opening_id.isdigit() else None

        material = StudyMaterial.objects.create(
            title=title,
            description=description,
            category=category,
            resource_type=resource_type,
            department=dept_obj,
            job_opening=job_obj,
            external_url=external_url,
            file_attachment=file_attachment,
            uploaded_by=request.user
        )

        AuditLog.objects.create(
            user=request.user,
            action="UPLOAD_STUDY_MATERIAL",
            entity_type="StudyMaterial",
            entity_id=str(material.id),
            details=f"Uploaded preparation resource: {title} ({category})"
        )

        messages.success(request, f"Resource '{title}' successfully added to preparation library.")
        return redirect('study_materials:list')

    return render(request, 'study_materials/material_form.html', {
        'categories': ResourceCategory.choices,
        'resource_types': ResourceType.choices,
        'departments': departments,
        'jobs': jobs,
        'active_nav': 'materials',
        'form_data': {},
        'errors': {},
    })
