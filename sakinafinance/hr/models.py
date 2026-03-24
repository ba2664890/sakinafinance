"""
RH & Paie Models — SakinaFinance
Gestion des Ressources Humaines et de la Paie
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Department(models.Model):
    """Département / Service"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='departments'
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, blank=True)
    manager = models.ForeignKey(
        'Employee', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managed_departments'
    )
    cost_center = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def employee_count(self):
        return self.employees.filter(is_active=True).count()


class JobPosition(models.Model):
    """Poste / Fonction"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='job_positions'
    )
    title = models.CharField(max_length=150)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='positions'
    )
    grade = models.CharField(max_length=20, blank=True)
    min_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class Employee(models.Model):
    """Employé — Fiche individuelle"""

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Actif')
        ON_LEAVE = 'on_leave', _('En congé')
        PROBATION = 'probation', _('Période d\'essai')
        TERMINATED = 'terminated', _('Résilié')

    class ContractType(models.TextChoices):
        CDI = 'cdi', _('CDI')
        CDD = 'cdd', _('CDD')
        INTERIM = 'interim', _('Intérim')
        FREELANCE = 'freelance', _('Freelance / Consultant')
        APPRENTICESHIP = 'apprenticeship', _('Apprentissage')

    class Gender(models.TextChoices):
        MALE = 'M', _('Homme')
        FEMALE = 'F', _('Femme')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='employees'
    )
    entity = models.ForeignKey(
        'accounts.Entity', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='employees'
    )

    # Identity
    employee_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    national_id = models.CharField(max_length=50, blank=True)
    nationality = models.CharField(max_length=100, default='Sénégalaise')
    photo = models.ImageField(upload_to='employees/photos/', blank=True, null=True)

    # Contact
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    # Employment
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='employees'
    )
    position = models.ForeignKey(
        JobPosition, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='employees'
    )
    contract_type = models.CharField(
        max_length=20, choices=ContractType.choices, default=ContractType.CDI
    )
    hire_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )

    # Compensation
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')

    # Bank Details
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    iban = models.CharField(max_length=50, blank=True)

    # Social
    cnss_number = models.CharField(max_length=30, blank=True)
    tax_id = models.CharField(max_length=30, blank=True)

    # Linked user account
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='employee_profile'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.employee_number} — {self.first_name} {self.last_name}"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def seniority_years(self):
        if self.hire_date:
            return (timezone.now().date() - self.hire_date).days // 365
        return 0


class LeaveType(models.Model):
    """Type de congé"""

    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='leave_types'
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    days_per_year = models.IntegerField(default=30)
    is_paid = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=True)
    color = models.CharField(max_length=20, default='primary')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    """Demande de congé"""

    class Status(models.TextChoices):
        PENDING = 'pending', _('En attente')
        APPROVED = 'approved', _('Approuvé')
        REJECTED = 'rejected', _('Refusé')
        CANCELLED = 'cancelled', _('Annulé')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='leave_requests'
    )
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name='requests'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_leaves'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.employee} — {self.leave_type} ({self.start_date} → {self.end_date})"


class PayrollPeriod(models.Model):
    """Période de paie"""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        PROCESSING = 'processing', _('En traitement')
        VALIDATED = 'validated', _('Validé')
        PAID = 'paid', _('Payé')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='payroll_periods'
    )
    name = models.CharField(max_length=50)
    period_start = models.DateField()
    period_end = models.DateField()
    payment_date = models.DateField(null=True, blank=True)

    # Totals
    total_gross = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_net = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employee_count = models.IntegerField(default=0)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_payrolls'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-period_start']

    def __str__(self):
        return f"{self.name} — {self.status}"


class Payslip(models.Model):
    """Bulletin de Paie"""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        CONFIRMED = 'confirmed', _('Confirmé')
        PAID = 'paid', _('Payé')
        CANCELLED = 'cancelled', _('Annulé')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period = models.ForeignKey(
        PayrollPeriod, on_delete=models.CASCADE, related_name='payslips'
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name='payslips'
    )
    reference = models.CharField(max_length=50, blank=True)

    # Gross
    base_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    overtime = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonuses = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Deductions
    cnss_employee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cnss_employer = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ipres_employee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ipres_employer = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Net
    net_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['period', 'employee']
        ordering = ['-period__period_start']

    def __str__(self):
        return f"Bulletin {self.employee.get_full_name()} — {self.period.name}"

    def compute(self):
        """Calcule la paie selon les règles OHADA/CFAE/IPRES sénégalaises"""
        self.gross_salary = self.base_salary + self.allowances + self.overtime + self.bonuses
        # CNSS Sénégal: 7% employé, 14% employeur
        self.cnss_employee = round(self.gross_salary * 0.07, 2)
        self.cnss_employer = round(self.gross_salary * 0.14, 2)
        # IPRES (retraite): 5.6% employé, 8.4% employeur
        self.ipres_employee = round(self.gross_salary * 0.056, 2)
        self.ipres_employer = round(self.gross_salary * 0.084, 2)
        # IRPP simplifié (estimation 15% sur revenu imposable)
        taxable = self.gross_salary - self.cnss_employee - self.ipres_employee
        self.income_tax = round(max(taxable * 0.15 - 250_000, 0), 2)
        self.total_deductions = (
            self.cnss_employee + self.ipres_employee + self.income_tax + self.other_deductions
        )
        self.net_salary = self.gross_salary - self.total_deductions
        return self


class Recruitment(models.Model):
    """Offre de recrutement"""

    class Status(models.TextChoices):
        OPEN = 'open', _('Ouverte')
        SCREENING = 'screening', _('Présélection')
        INTERVIEWS = 'interviews', _('Entretiens')
        OFFER = 'offer', _('Offre envoyée')
        FILLED = 'filled', _('Pourvue')
        CANCELLED = 'cancelled', _('Annulée')

    class Priority(models.TextChoices):
        LOW = 'low', _('Faible')
        NORMAL = 'normal', _('Normale')
        HIGH = 'high', _('Haute')
        CRITICAL = 'critical', _('Critique')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        'accounts.Company', on_delete=models.CASCADE, related_name='recruitments'
    )
    position = models.ForeignKey(
        JobPosition, on_delete=models.SET_NULL, null=True, blank=True
    )
    title = models.CharField(max_length=200)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    contract_type = models.CharField(
        max_length=20, choices=Employee.ContractType.choices, default='cdi'
    )
    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    priority = models.CharField(
        max_length=20, choices=Priority.choices, default=Priority.NORMAL
    )
    posted_date = models.DateField(default=timezone.now)
    deadline = models.DateField(null=True, blank=True)
    candidates_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-posted_date']

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
