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
from .forms import EmployeeForm, LeaveRequestForm

from .models import (
    Employee, Department, PayrollPeriod, Payslip,
    LeaveRequest, Recruitment, LeaveType
)
from decimal import Decimal


def _get_company(request):
    """Helper: returns the user's company or None"""
    return getattr(request.user, 'company', None)


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
        payroll_total = float(last_period.total_gross) if last_period else 0
        avg_salary = round(payroll_total / max(total_employees, 1))
        
        pending_leaves = LeaveRequest.objects.filter(employee__company=company, status='pending').count()
        approved_leaves = LeaveRequest.objects.filter(employee__company=company, status='approved').count()
        ongoing_leaves = LeaveRequest.objects.filter(
            employee__company=company,
            status='approved',
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        ).count()

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
