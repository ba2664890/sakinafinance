"""
HR Admin — FinanceOS IA
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Department, JobPosition, Employee, LeaveType,
    LeaveRequest, PayrollPeriod, Payslip, Recruitment
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'company', 'manager', 'employee_count', 'is_active']
    list_filter = ['company', 'is_active']
    search_fields = ['name', 'code']


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'grade', 'min_salary', 'max_salary', 'is_active']
    list_filter = ['company', 'department', 'is_active']
    search_fields = ['title']


class PayslipInline(admin.TabularInline):
    model = Payslip
    extra = 0
    fields = ['period', 'gross_salary', 'net_salary', 'status']
    readonly_fields = ['gross_salary', 'net_salary']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'employee_number', 'get_full_name', 'department', 'position',
        'contract_type', 'hire_date', 'base_salary', 'status'
    ]
    list_filter = ['company', 'status', 'contract_type', 'department', 'gender']
    search_fields = ['employee_number', 'first_name', 'last_name', 'email', 'cnss_number']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PayslipInline]
    fieldsets = (
        ('Identité', {
            'fields': (
                'employee_number', 'first_name', 'last_name', 'gender',
                'date_of_birth', 'national_id', 'nationality', 'photo'
            )
        }),
        ('Contact', {
            'fields': ('email', 'phone', 'address')
        }),
        ('Emploi', {
            'fields': (
                'company', 'entity', 'department', 'position',
                'contract_type', 'hire_date', 'end_date', 'status'
            )
        }),
        ('Rémunération', {
            'fields': ('base_salary', 'currency', 'bank_name', 'account_number', 'iban')
        }),
        ('Charges Sociales', {
            'fields': ('cnss_number', 'tax_id')
        }),
    )

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Nom complet'


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'days_per_year', 'is_paid', 'requires_approval']
    list_filter = ['company', 'is_paid']


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'days', 'status']
    list_filter = ['status', 'leave_type', 'employee__department']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['created_at']
    actions = ['approve_leaves', 'reject_leaves']

    def approve_leaves(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='approved', approved_by=request.user, approved_at=timezone.now())
        self.message_user(request, f"{queryset.count()} demande(s) approuvée(s).")
    approve_leaves.short_description = "Approuver les congés sélectionnés"

    def reject_leaves(self, request, queryset):
        queryset.update(status='rejected')
        self.message_user(request, f"{queryset.count()} demande(s) refusée(s).")
    reject_leaves.short_description = "Refuser les congés sélectionnés"


class PayslipInlineForPeriod(admin.TabularInline):
    model = Payslip
    extra = 0
    fields = ['employee', 'gross_salary', 'total_deductions', 'net_salary', 'status']
    readonly_fields = ['gross_salary', 'total_deductions', 'net_salary']


@admin.register(PayrollPeriod)
class PayrollPeriodAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'period_start', 'period_end', 'payment_date',
        'employee_count', 'total_gross', 'total_net', 'status'
    ]
    list_filter = ['company', 'status']
    search_fields = ['name']
    inlines = [PayslipInlineForPeriod]
    readonly_fields = ['total_gross', 'total_deductions', 'total_net', 'employee_count']


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = [
        'reference', 'employee', 'period', 'gross_salary',
        'total_deductions', 'net_salary', 'status'
    ]
    list_filter = ['status', 'period', 'employee__department']
    search_fields = ['employee__first_name', 'employee__last_name', 'reference']
    readonly_fields = ['created_at', 'paid_at']


@admin.register(Recruitment)
class RecruitmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'contract_type', 'status', 'priority', 'posted_date', 'candidates_count']
    list_filter = ['status', 'priority', 'department', 'contract_type']
    search_fields = ['title']
    readonly_fields = ['created_at']
