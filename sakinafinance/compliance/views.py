"""
Fiscalité & Conformité (Compliance) Views — SakinaFinance
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
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
    """Module Fiscalité & Réglementaire — vue principale"""
    return render(request, 'compliance/index.html', {'page_title': 'Fiscalité & Réglementaire'})

@login_required
def tax_filing_create(request):
    """Déclarer un impôt"""
    company = _get_company(request)
    if request.method == 'POST':
        form = TaxFilingForm(request.POST, company=company)
        if form.is_valid():
            filing = form.save(commit=False)
            filing.company = company
            filing.save()
            return redirect('compliance_dashboard')
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
    if request.method == 'POST':
        form = ComplianceRiskForm(request.POST)
        if form.is_valid():
            risk = form.save(commit=False)
            risk.company = company
            risk.save()
            return redirect('compliance_dashboard')
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
    company = request.user.company
    if not company:
        return JsonResponse({'error': 'No company associated with user'}, status=400)

    # Fetch real data
    filings = TaxFiling.objects.filter(company=company).select_related('tax_type', 'entity')
    risks = ComplianceRisk.objects.filter(company=company, is_resolved=False)
    entities = Entity.objects.filter(company=company)
    
    # Summary stats
    open_risks_count = risks.count()
    pending_filings = filings.filter(status='pending').count()
    
    # Calculate tax provision (example: sum of all unpaid/pending filings)
    # Using a simple aggregation or manual sum for demo
    tax_provision = sum(f.tax_amount for f in filings.filter(status__in=['pending', 'draft']))

    # Prepare Tax Calendar (Upcoming deadlines)
    calendar_data = []
    upcoming = filings.filter(deadline__gte=timezone.now().date()).order_by('deadline')[:5]
    for f in upcoming:
        days_left = (f.deadline - timezone.now().date()).days
        calendar_data.append({
            'deadline': f.deadline.strftime('%d/%m/%Y'),
            'tax': f.tax_type.name,
            'entity': f.entity.name,
            'amount': float(f.tax_amount),
            'status': f.get_status_display(),
            'status_class': 'warning' if f.status == 'pending' else 'info',
            'days_left': days_left,
            'urgent': days_left <= 7
        })

    # Prepare Filed Declarations
    history_data = []
    recent_filed = filings.filter(status__in=['filed', 'paid']).order_by('-filed_at')[:5]
    for f in recent_filed:
        history_data.append({
            'period': f.period_start.strftime('%b %Y'),
            'tax': f.tax_type.code,
            'entity': f.entity.name,
            'amount': float(f.tax_amount),
            'filed': f.filed_at.strftime('%d/%m/%Y') if f.filed_at else '',
            'receipt': f.receipt_number or 'N/A'
        })

    # Prepare Risks
    risk_list = []
    for r in risks:
        risk_list.append({
            'description': r.title,
            'impact': r.impact_description,
            'probability': r.get_probability_display(),
            'status': r.status,
            'level': r.severity # 'success', 'warning', 'danger'
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
            'description': reg.description
        })

    data = {
        'compliance_score': 100 if open_risks_count == 0 else max(100 - (open_risks_count * 10), 0),
        'open_risks_count': open_risks_count,
        'declarations_pending': pending_filings,
        'tax_provision': float(tax_provision),
        'next_deadline_days': (upcoming[0].deadline - timezone.now().date()).days if upcoming else 0,
        'tax_calendar': calendar_data,
        'filed_declarations': history_data,
        'risks': risk_list,
        'entities': [
            {
                'name': e.name,
                'country': e.country,
                'tin': e.tax_id or 'À renseigner',
                'vat_reg': e.vat_number or 'À renseigner',
                'status': 'Active' if e.is_active else 'Inactive'
            } for e in entities
        ],
    }
    return JsonResponse(data)
