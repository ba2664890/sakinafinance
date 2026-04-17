"""
HR Views — SakinaFinance
Connecte les vues aux vrais modèles DB
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from .forms import EmployeeForm, LeaveRequestForm, RecruitmentForm

from .models import (
    Employee, Department, JobPosition, PayrollPeriod, Payslip,
    LeaveRequest, Recruitment, LeaveType, PayrollConfig
)
from django.views.decorators.http import require_POST
from decimal import Decimal


def _get_company(request):
    """Helper: returns the user's company or None"""
    company = getattr(request.user, 'company', None)
    if company:
        return company
    profile = getattr(request.user, 'profile', None)
    return getattr(profile, 'company', None)


@login_required
def hr_dashboard(request):
    """Module RH & Paie — vue principale (Squelette)"""
    return render(request, 'hr/index.html', {'page_title': 'RH & Paie'})


@login_required
def api_hr_data(request):
    """API: Get HR Stats and Lists"""
    company = _get_company(request)

    if company:
        employees = Employee.objects.filter(company=company, is_active=True)
        total_employees = employees.count()
        new_hires = employees.filter(
            hire_date__gte=timezone.now().date().replace(day=1)
        ).count()

        payroll_periods = PayrollPeriod.objects.filter(company=company).order_by('-period_start')[:4]
        payroll_runs = []
        for period in payroll_periods:
            payroll_runs.append({
                'period': period.name,
                'employees': period.employee_count,
                'gross': float(period.total_gross),
                'deductions': float(period.total_deductions),
                'net': float(period.total_net),
                'status': period.get_status_display(),
                'date': (period.payment_date or period.period_end).strftime('%d/%m/%Y'),
            })

        departments = Department.objects.filter(company=company, is_active=True)
        dept_data = []
        colors = ['primary', 'success', 'warning', 'info', 'secondary', 'danger']
        for i, dept in enumerate(departments[:6]):
            count = dept.employee_count()
            dept_data.append({
                'name': dept.name,
                'count': count,
                'pct': round(count / max(total_employees, 1) * 100),
                'color': colors[i % len(colors)],
            })

        leave_types = LeaveType.objects.filter(company=company)
        leave_summary = []
        for lt in leave_types:
            leave_summary.append({
                'type': lt.name,
                'pending': lt.requests.filter(status='pending').count(),
                'approved': lt.requests.filter(status='approved').count(),
            })

        recruitments_qs = Recruitment.objects.filter(
            company=company
        ).exclude(status__in=['filled', 'cancelled']).order_by('-posted_date')[:4]
        recruitments = []
        for r in recruitments_qs:
            recruitments.append({
                'title': r.title,
                'dept': r.department.name if r.department else '—',
                'posted': r.posted_date.strftime('%d/%m/%Y'),
                'candidates': r.candidates_count,
                'stage': r.get_status_display(),
            })

        last_period = payroll_periods.first()
        previous_period = payroll_periods[1] if len(payroll_periods) > 1 else None
        payroll_total = float(last_period.total_gross) if last_period else 0
        avg_salary = round(payroll_total / max(total_employees, 1))
        payroll_growth = 0.0
        payroll_variance = 0.0
        net_ratio = 0.0
        last_payment_date = ''
        if last_period:
            last_payment_date = (last_period.payment_date or last_period.period_end).strftime('%d/%m/%Y')
            if previous_period and previous_period.total_gross > 0:
                payroll_growth = round((float(last_period.total_gross) - float(previous_period.total_gross)) / float(previous_period.total_gross) * 100, 1)
                payroll_variance = round((float(last_period.total_gross) - float(previous_period.total_gross)) / float(previous_period.total_gross) * 100, 1)
            if last_period.total_gross > 0:
                net_ratio = round(float(last_period.total_net) / float(last_period.total_gross) * 100, 1)

        config = PayrollConfig.objects.filter(company=company).first()
        if not config:
            config = PayrollConfig(company=company)
        social_charge_rate = float(
            config.cnss_employee_rate + config.cnss_employer_rate +
            config.ipres_employee_rate + config.ipres_employer_rate
        )
        avg_cost_per_employee = round(payroll_total / max(total_employees, 1), 2)

        open_positions_count = Recruitment.objects.filter(company=company, status=Recruitment.Status.OPEN).count()
        focus_items = []
        if last_period:
            if last_period.status == PayrollPeriod.Status.DRAFT:
                focus_items.append({'title': 'Finaliser le cycle de paie en brouillon', 'status': 'Urgent', 'due': 'Dès que possible'})
            elif last_period.status == PayrollPeriod.Status.PROCESSING:
                focus_items.append({'title': 'Vérifier les retenues et valider la paie', 'status': 'En cours', 'due': '3 j.'})
            elif last_period.status == PayrollPeriod.Status.VALIDATED:
                focus_items.append({'title': 'Préparer le paiement final', 'status': 'Planifié', 'due': '1 sem.'})
        if open_positions_count:
            focus_items.append({'title': f'{open_positions_count} postes ouverts à prioriser', 'status': 'En cours', 'due': '1 sem.'})

        positions = JobPosition.objects.filter(company=company)

        pending_leaves = LeaveRequest.objects.filter(employee__company=company, status='pending').count()
        approved_leaves = LeaveRequest.objects.filter(employee__company=company, status='approved').count()
        ongoing_leaves = LeaveRequest.objects.filter(
            employee__company=company,
            status='approved',
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        ).count()

        improvement_metrics = {
            'avg_cost_per_employee': avg_cost_per_employee,
            'net_ratio': net_ratio,
            'social_charges': social_charge_rate,
            'payroll_variance': payroll_variance,
            'last_payment_date': last_payment_date,
            'focus_items': focus_items,
            'forecast_series': [
                {'label': 'Coût moyen', 'value': avg_cost_per_employee},
                {'label': 'Charges', 'value': social_charge_rate},
                {'label': 'Net/Brut', 'value': net_ratio},
                {'label': 'Variance', 'value': abs(payroll_variance)},
            ]
        }

    data = {
        'total_employees': total_employees,
        'new_hires': new_hires,
        'turnover_rate': 0.0,
        'payroll_total': payroll_total,
        'payroll_growth': 0.0,
        'avg_salary': avg_salary,
        'satisfaction_score': 0,
        'departments': dept_data,
        'payroll_runs': payroll_runs,
        'leave_summary': leave_summary,
        'recruitments': recruitments,
        'pending_leaves': pending_leaves,
        'approved_leaves': approved_leaves,
        'ongoing_leaves': ongoing_leaves,
        'departments_list': list(departments.values('id', 'name')),
        'positions_list': list(positions.values('id', 'title')),
        'improvement': improvement_metrics,
    }
    return JsonResponse(data)


@login_required
def employee_list(request):
    """Liste des employés"""
    company = _get_company(request)
    employees = Employee.objects.filter(
        company=company, is_active=True
    ).select_related('department', 'position') if company else Employee.objects.none()

    # Search
    q = request.GET.get('q', '')
    if q:
        employees = employees.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
            | Q(employee_number__icontains=q) | Q(email__icontains=q)
        )

    dept_filter = request.GET.get('dept', '')
    if dept_filter:
        employees = employees.filter(department__id=dept_filter)

    departments = Department.objects.filter(company=company, is_active=True) if company else []

    context = {
        'page_title': 'Employés',
        'employees': employees,
        'departments': departments,
        'q': q,
        'dept_filter': dept_filter,
    }
    return render(request, 'hr/employee_list.html', context)


@login_required
def employee_detail(request, pk):
    """Fiche employé"""
    employee = get_object_or_404(Employee, pk=pk, company=_get_company(request))
    payslips = Payslip.objects.filter(employee=employee).order_by('-period__period_start')[:12]
    leaves = LeaveRequest.objects.filter(employee=employee).order_by('-created_at')[:10]
    context = {
        'page_title': f'{employee.get_full_name()}',
        'employee': employee,
        'payslips': payslips,
        'leaves': leaves,
    }
    return render(request, 'hr/employee_detail.html', context)


@login_required
def payslip_detail(request, pk):
    """Bulletin de paie"""
    payslip = get_object_or_404(Payslip, pk=pk, employee__company=_get_company(request))
    context = {
        'page_title': f'Bulletin — {payslip.employee.get_full_name()}',
        'payslip': payslip,
    }
    return render(request, 'hr/payslip_detail.html', context)


@login_required
def employee_create(request):
    """Créer un employé"""
    company = _get_company(request)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, company=company)
        if form.is_valid():
            emp = form.save(commit=False)
            emp.company = company
            emp.save()
            return redirect('hr_dashboard')
    else:
        form = EmployeeForm(company=company)
    
    return render(request, 'projects/project_form.html', {
        'form': form,
        'page_title': 'Nouvel Employé',
        'action': 'Créer'
    })


@login_required
def leave_request_create(request):
    """Créer une demande de congé"""
    company = _get_company(request)
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, company=company)
        if form.is_valid():
            form.save()
            return redirect('hr_dashboard')
    else:
        form = LeaveRequestForm(company=company)
    
    return render(request, 'projects/project_form.html', {
        'form': form,
        'page_title': 'Demande de Congé',
        'action': 'Soumettre'
    })


@require_POST
@login_required
def api_hr_recruit(request):
    """API: Créer une offre de recrutement"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'status': 'error', 'message': 'Société introuvable pour l’utilisateur.'}, status=400)

    form = RecruitmentForm(request.POST, company=company)
    if form.is_valid():
        recruit = form.save(commit=False)
        recruit.company = company
        recruit.created_by = request.user
        recruit.save()
        return JsonResponse({
            'status': 'success',
            'message': 'Offre publiée',
            'recruit': {'id': str(recruit.id), 'title': recruit.title}
        })

    errors = []
    for field, field_errors in form.errors.items():
        errors.append(f"{field}: {', '.join(field_errors)}")
    return JsonResponse({
        'status': 'error',
        'message': 'Validation impossible.',
        'errors': errors
    }, status=400)


@require_POST
@login_required
def api_hr_employee_add(request):
    """API: Créer un nouvel employé (Embauche)"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'status': 'error', 'message': 'Société introuvable.'}, status=400)

    form = EmployeeForm(request.POST, request.FILES, company=company)
    if form.is_valid():
        employee = form.save(commit=False)
        employee.company = company
        employee.save()
        return JsonResponse({
            'status': 'success',
            'message': f'Employé {employee.get_full_name()} créé avec succès.',
            'employee': {'id': str(employee.id), 'name': employee.get_full_name()}
        })

    errors = []
    for field, field_errors in form.errors.items():
        errors.append(f"{field}: {', '.join(field_errors)}")
    return JsonResponse({
        'status': 'error',
        'message': 'Erreur de validation.',
        'errors': errors
    }, status=400)


@require_POST
@login_required
def api_hr_payroll_config(request):
    """API: Configurer les taux de paie"""
    company = _get_company(request)
    if not company:
        return JsonResponse({'status': 'error', 'message': 'Société introuvable pour l’utilisateur.'}, status=400)

    config, _ = PayrollConfig.objects.get_or_create(company=company)
    
    try:
        def safe_decimal(value, default):
            raw = request.POST.get(value)
            if raw in [None, '']:
                raw = str(default)
            return Decimal(raw)

        config.cnss_employee_rate = safe_decimal('cnss_employee_rate', '7.0')
        config.cnss_employer_rate = safe_decimal('cnss_employer_rate', '14.0')
        config.ipres_employee_rate = safe_decimal('ipres_employee_rate', '5.6')
        config.ipres_employer_rate = safe_decimal('ipres_employer_rate', '8.4')
        config.irpp_estimated_rate = safe_decimal('irpp_estimated_rate', '15.0')
        config.irpp_threshold = safe_decimal('irpp_threshold', '250000')
        config.save()
        return JsonResponse({'status': 'success', 'message': 'Configuration sauvegardée'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Erreur de validation des données : {e}'}, status=400)
