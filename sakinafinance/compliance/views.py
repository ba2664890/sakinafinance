"""
Fiscalité & Conformité (Compliance) Views — SakinaFinance
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum
from datetime import timedelta
from decimal import Decimal
from .models import TaxFiling, RegulatoryRequirement, ComplianceRisk, TaxType
from sakinafinance.accounts.models import Entity
from .forms import TaxFilingForm, ComplianceRiskForm

def _get_company(request):
    """Helper to get the user's company"""
    if hasattr(request.user, 'company') and request.user.company:
        return request.user.company
    if hasattr(request.user, 'profile') and request.user.profile.company:
        return request.user.profile.company
    return None

@login_required
def compliance_view(request):
    """Module Conformité — vue principale"""
    return render(request, 'compliance/index.html', {
        'page_title': 'Conformité',
    })

@login_required
def tax_filing_create(request):
    """Déclarer un impôt"""
    company = _get_company(request)
    if not company:
        return redirect('dashboard')
    if request.method == 'POST':
        form = TaxFilingForm(request.POST, request.FILES, company=company)
        if form.is_valid():
            filing = form.save(commit=False)
            filing.company = company
            if filing.status in [TaxFiling.Status.FILED, TaxFiling.Status.PAID] and not filing.filed_at:
                filing.filed_at = timezone.now()
            filing.save()
            return redirect('taxation')
    else:
        form = TaxFilingForm(company=company)
    
    return render(request, 'projects/project_form.html', {
        'form': form,
        'page_title': 'Nouvelle Déclaration Fiscale',
        'action': 'Enregistrer'
    })

@login_required
def compliance_risk_create(request):
    """Signaler un risque"""
    company = _get_company(request)
    if not company:
        return redirect('dashboard')
    if request.method == 'POST':
        form = ComplianceRiskForm(request.POST)
        if form.is_valid():
            risk = form.save(commit=False)
            risk.company = company
            risk.save()
            return redirect('regulatory')
    else:
        form = ComplianceRiskForm()
    
    return render(request, 'projects/project_form.html', {
        'form': form,
        'page_title': 'Signaler un Risque de Conformité',
        'action': 'Signaler'
    })


@login_required
def api_compliance_data(request):
    """API: Get Compliance, Tax & Regulatory Data from models"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'error': 'No company associated with user'}, status=400)

    # Fetch real data
    filings = TaxFiling.objects.filter(company=company).select_related('tax_type', 'entity')
    open_risks = ComplianceRisk.objects.filter(company=company, is_resolved=False)
    entities = Entity.objects.filter(company=company).order_by('code', 'name')
    today = timezone.localdate()
    
    # Summary stats
    open_risks_count = open_risks.count()
    pending_filings = filings.filter(status__in=[TaxFiling.Status.PENDING, TaxFiling.Status.DRAFT]).count()
    overdue_filings = filings.filter(
        deadline__lt=today,
        status__in=[TaxFiling.Status.DRAFT, TaxFiling.Status.PENDING]
    ).count()
    due_soon_filings = filings.filter(
        deadline__gte=today,
        deadline__lte=today + timedelta(days=7),
        status__in=[TaxFiling.Status.DRAFT, TaxFiling.Status.PENDING]
    ).count()
    
    tax_provision = filings.filter(
        status__in=[TaxFiling.Status.PENDING, TaxFiling.Status.DRAFT]
    ).aggregate(total=Sum('tax_amount'))['total'] or Decimal('0')

    completed_filings = filings.filter(status__in=[TaxFiling.Status.FILED, TaxFiling.Status.PAID]).count()
    total_tracked_filings = filings.exclude(status=TaxFiling.Status.CANCELLED).count()
    punctuality_rate = round((completed_filings / total_tracked_filings) * 100) if total_tracked_filings else 100

    # Prepare Tax Calendar (Upcoming deadlines)
    calendar_data = []
    upcoming_qs = filings.filter(
        status__in=[TaxFiling.Status.DRAFT, TaxFiling.Status.PENDING],
        deadline__gte=today
    ).order_by('deadline')
    upcoming = list(upcoming_qs[:8])
    for f in upcoming:
        days_left = (f.deadline - today).days
        urgency = 'critical' if days_left <= 3 else 'warning' if days_left <= 7 else 'normal'
        calendar_data.append({
            'deadline': f.deadline.strftime('%d/%m/%Y'),
            'tax': f.tax_type.name,
            'tax_code': f.tax_type.code,
            'entity': f.entity.name,
            'amount': float(f.tax_amount),
            'status': f.get_status_display(),
            'status_code': f.status,
            'days_left': days_left,
            'urgency': urgency,
            'period': f"{f.period_start.strftime('%d/%m/%Y')} - {f.period_end.strftime('%d/%m/%Y')}",
        })

    # Prepare Filed Declarations
    history_data = []
    recent_filed = filings.filter(status__in=[TaxFiling.Status.FILED, TaxFiling.Status.PAID]).order_by('-filed_at', '-updated_at')[:8]
    for f in recent_filed:
        history_data.append({
            'period': f.period_start.strftime('%b %Y'),
            'tax': f.tax_type.code,
            'entity': f.entity.name,
            'amount': float(f.tax_amount),
            'filed': f.filed_at.strftime('%d/%m/%Y') if f.filed_at else '',
            'receipt': f.receipt_number or 'N/A',
            'status': f.get_status_display(),
            'document_url': f.document.url if f.document else '',
        })

    # Prepare Risks
    risk_list = []
    risk_weights = {'low': 4, 'medium': 8, 'high': 15, 'critical': 25}
    probability_weights = {'low': 1, 'medium': 2, 'high': 3}
    risk_penalty = 0
    for r in open_risks.order_by('-severity', '-created_at'):
        risk_penalty += risk_weights.get(r.severity, 8) + probability_weights.get(r.probability, 1)
        risk_list.append({
            'title': r.title,
            'description': r.description,
            'impact': r.impact_description,
            'probability': r.get_probability_display(),
            'status': r.status,
            'level': r.severity,
            'level_label': r.get_severity_display(),
            'mitigation': r.mitigation_plan,
            'created_at': r.created_at.strftime('%d/%m/%Y'),
        })

    # No data in DB: returns empty state naturally via preparations above

    # 4. Regulatory Requirements
    regulatory_qs = RegulatoryRequirement.objects.filter(company=company, is_active=True)
    regulatory_data = []
    for reg in regulatory_qs:
        regulatory_data.append({
            'name': reg.name,
            'authority': reg.authority,
            'frequency': reg.get_frequency_display(),
            'description': reg.description,
        })

    missing_tax_ids = entities.filter(tax_id='').count()
    missing_vat_numbers = entities.filter(vat_number='').count()
    risk_breakdown = open_risks.values('severity').annotate(total=Count('id'))

    data = {
        'compliance_score': max(100 - risk_penalty - (overdue_filings * 8), 0),
        'open_risks_count': open_risks_count,
        'declarations_pending': pending_filings,
        'overdue_filings': overdue_filings,
        'due_soon_filings': due_soon_filings,
        'tax_provision': float(tax_provision),
        'punctuality_rate': punctuality_rate,
        'next_deadline_days': (upcoming[0].deadline - today).days if upcoming else None,
        'tax_calendar': calendar_data,
        'filed_declarations': history_data,
        'risks': risk_list,
        'risk_breakdown': {item['severity']: item['total'] for item in risk_breakdown},
        'regulatory_requirements': regulatory_data,
        'tax_health': {
            'tax_types_count': TaxType.objects.filter(company=company).count(),
            'entities_count': entities.count(),
            'missing_tax_ids': missing_tax_ids,
            'missing_vat_numbers': missing_vat_numbers,
        },
        'entities': [
            {
                'name': e.name,
                'code': e.code,
                'country': e.country,
                'tin': e.tax_id or 'À renseigner',
                'vat_reg': e.vat_number or 'À renseigner',
                'status': 'Active' if e.is_active else 'Inactive',
                'is_complete': bool(e.tax_id and e.vat_number),
            } for e in entities
        ],
    }
    return JsonResponse(data)
