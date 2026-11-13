from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from apps.companies.models import Company, CompanyTier
from apps.accounts.decorators import login_required_custom, tpo_required
from apps.students.models import StudentProfile
from apps.audit.models import AuditLog


@login_required_custom
def company_list_view(request):
    """
    Lists all corporate recruiting partners with tier badges, contact details, instant search, and pagination.
    """
    tier_filter = request.GET.get('tier', '')
    query = request.GET.get('q', '').strip()

    companies_qs = Company.objects.filter(is_active=True).order_by('name')

    if tier_filter:
        companies_qs = companies_qs.filter(tier=tier_filter)
    if query:
        companies_qs = companies_qs.filter(
            Q(name__icontains=query) |
            Q(industry_sector__icontains=query) |
            Q(contact_person__icontains=query) |
            Q(contact_email__icontains=query)
        )

    paginator = Paginator(companies_qs, 12)
    page_number = request.GET.get('page')
    companies = paginator.get_page(page_number)

    return render(request, 'companies/company_list.html', {
        'companies': companies,
        'tiers': CompanyTier.choices,
        'selected_tier': tier_filter,
        'query': query,
        'total_count': companies_qs.count(),
        'active_nav': 'companies'
    })


@tpo_required
def company_create_view(request):
    """
    Adds a new corporate partner with manual server-side validation.
    Strictly NO Django Forms.
    """
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        website = request.POST.get('website', '').strip()
        industry_sector = request.POST.get('industry_sector', '').strip()
        tier = request.POST.get('tier', CompanyTier.TIER_2_CORE)
        contact_person = request.POST.get('contact_person', '').strip()
        contact_email = request.POST.get('contact_email', '').strip().lower()
        contact_phone = request.POST.get('contact_phone', '').strip()
        address = request.POST.get('address', '').strip()

        errors = {}
        if not name:
            errors['name'] = 'Company name is required.'
        elif Company.objects.filter(name=name).exists():
            errors['name'] = 'A company with this name already exists.'

        if not industry_sector:
            errors['industry_sector'] = 'Industry sector is required.'
        if not contact_person:
            errors['contact_person'] = 'Recruiter contact person is required.'
        if not contact_email:
            errors['contact_email'] = 'Recruiter email address is required.'

        if errors:
            return render(request, 'companies/company_form.html', {
                'errors': errors,
                'form_data': request.POST,
                'tiers': CompanyTier.choices,
                'is_create': True,
                'active_nav': 'companies'
            })

        company = Company.objects.create(
            name=name,
            website=website,
            industry_sector=industry_sector,
            tier=tier,
            contact_person=contact_person,
            contact_email=contact_email,
            contact_phone=contact_phone,
            address=address
        )

        AuditLog.objects.create(
            user=request.user,
            action="CREATE_COMPANY",
            entity_type="Company",
            entity_id=str(company.id),
            details=f"Added hiring partner: {company.name} ({tier})"
        )

        messages.success(request, f"Company {company.name} successfully registered.")
        return redirect('companies:list')

    return render(request, 'companies/company_form.html', {
        'tiers': CompanyTier.choices,
        'is_create': True,
        'active_nav': 'companies',
        'company': None,
        'form_data': {},
        'errors': {},
    })


@tpo_required
def company_edit_view(request, company_id):
    """
    Edits existing corporate profile.
    """
    company = get_object_or_404(Company, id=company_id)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        website = request.POST.get('website', '').strip()
        industry_sector = request.POST.get('industry_sector', '').strip()
        tier = request.POST.get('tier', CompanyTier.TIER_2_CORE)
        contact_person = request.POST.get('contact_person', '').strip()
        contact_email = request.POST.get('contact_email', '').strip().lower()
        contact_phone = request.POST.get('contact_phone', '').strip()
        address = request.POST.get('address', '').strip()

        errors = {}
        if not name:
            errors['name'] = 'Company name is required.'
        elif Company.objects.filter(name=name).exclude(id=company.id).exists():
            errors['name'] = 'Another company with this name already exists.'

        if errors:
            return render(request, 'companies/company_form.html', {
                'errors': errors,
                'company': company,
                'tiers': CompanyTier.choices,
                'is_create': False,
                'active_nav': 'companies'
            })

        company.name = name
        company.website = website
        company.industry_sector = industry_sector
        company.tier = tier
        company.contact_person = contact_person
        company.contact_email = contact_email
        company.contact_phone = contact_phone
        company.address = address
        company.save()

        messages.success(request, f"Updated profile for {company.name}.")
        return redirect('companies:list')

    return render(request, 'companies/company_form.html', {
        'company': company,
        'tiers': CompanyTier.choices,
        'is_create': False,
        'active_nav': 'companies'
    })


@login_required_custom
def company_detail_view(request, company_id):
    """
    Detailed corporate recruitment profile and historical placement audit.
    """
    company = get_object_or_404(Company, id=company_id)

    active_drives = company.job_openings.filter(status='PUBLISHED').prefetch_related('allowed_departments').order_by('-created_at')
    past_drives = company.job_openings.exclude(status='PUBLISHED').prefetch_related('allowed_departments').order_by('-created_at')

    hired_students = StudentProfile.objects.filter(placed_company=company).select_related('user', 'department').order_by('-salary_package')
    avg_package = hired_students.aggregate(avg=Avg('salary_package'))['avg'] or 0.0

    return render(request, 'companies/company_detail.html', {
        'company': company,
        'active_drives': active_drives,
        'past_drives': past_drives,
        'hired_students': hired_students,
        'total_drives': company.job_openings.count(),
        'total_hires': hired_students.count(),
        'avg_package': round(avg_package, 2),
        'active_nav': 'companies'
    })
