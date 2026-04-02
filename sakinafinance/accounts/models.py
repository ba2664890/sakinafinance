"""
Models for Accounts Module - User & Company Management
SakinaFinance - Système d'Intelligence Financière Universel
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .managers import UserManager


LANGUAGE_CHOICES = [
    ('fr', _('Français')),
    ('en', _('English')),
]

CURRENCY_CHOICES = [
    ('XOF', _('Franc CFA (XOF)')),
    ('EUR', _('Euro (EUR)')),
    ('USD', _('US Dollar (USD)')),
    ('GBP', _('British Pound (GBP)')),
]


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User Model for SakinaFinance"""
    
    class UserType(models.TextChoices):
        STARTUP = 'startup', _('Startup')
        PME = 'pme', _('PME')
        ETI = 'eti', _('ETI')
        ENTERPRISE = 'enterprise', _('Grande Entreprise')
        GROUPE = 'groupe', _('Groupe / Holding')
    
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Administrateur société')
        CEO = 'ceo', _('CEO / DG')
        CFO = 'cfo', _('DAF / CFO')
        ACCOUNTANT = 'accountant', _('Comptable')
        TREASURER = 'treasurer', _('Trésorier')
        CONTROLLER = 'controller', _('Contrôleur de Gestion')
        HR = 'hr', _('RH / Paie')
        PROCUREMENT = 'procurement', _('Achats')
        VIEWER = 'viewer', _('Lecteur')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    phone = models.CharField(_('phone'), max_length=20, blank=True)
    
    # User Type & Role
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.STARTUP
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ADMIN
    )
    
    # Status
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_account_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Profile
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    
    # Preferences
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='fr')
    timezone = models.CharField(max_length=50, default='Africa/Dakar')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='XOF')

    # Relations
    company = models.ForeignKey(
        'Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    entity = models.ForeignKey(
        'Entity',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    
    # Subscription
    subscription_plan = models.CharField(
        max_length=20,
        choices=[
            ('free', 'Gratuit'),
            ('startup', 'Startup'),
            ('pme', 'PME'),
            ('enterprise', 'Enterprise'),
            ('groupe', 'Groupe'),
        ],
        default='free'
    )
    subscription_expires = models.DateTimeField(null=True, blank=True)
    
    # Security
    @property
    def two_factor_enabled(self):
        """Check if 2FA is enabled and confirmed for this user"""
        from django_otp import devices_for_user
        return any(devices_for_user(self, confirmed=True))

    login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_short_name(self):
        return self.first_name
    
    def has_active_subscription(self):
        if self.subscription_plan == 'free':
            return True
        if self.subscription_expires and self.subscription_expires > timezone.now():
            return True
        return False
    
    @property
    def plan(self):
        """Returns the effective plan (Company plan prioritized over User plan)"""
        if self.company:
            return self.company.subscription_plan
        return self.subscription_plan

    @property
    def is_free_plan(self):
        return self.plan == 'free'

    @property
    def is_startup_plan(self):
        return self.plan == 'startup'

    @property
    def is_pme_plan(self):
        return self.plan == 'pme'

    @property
    def is_enterprise_plan(self):
        return self.plan == 'enterprise'

    @property
    def is_groupe_plan(self):
        return self.plan == 'groupe'

    # Access helpers (Cumulative based on Pricing Page)
    @property
    def can_access_finance(self):
        # Startup and above
        return self.plan in ['startup', 'pme', 'enterprise', 'groupe']

    @property
    def can_access_operations(self):
        # Startup and above
        return self.plan in ['startup', 'pme', 'enterprise', 'groupe']

    @property
    def can_access_hr(self):
        # PME and above
        return self.plan in ['pme', 'enterprise', 'groupe']

    @property
    def can_access_compliance(self):
        # Enterprise and above
        return self.plan in ['enterprise', 'groupe']

    @property
    def can_access_consolidation(self):
        # PME has 5 entities, Enterprise/Groupe have unlimited/custom
        return self.plan in ['pme', 'enterprise', 'groupe']

    @property
    def can_access_executive(self):
        # Enterprise and above
        return self.plan in ['enterprise', 'groupe']
    
    def save(self, *args, **kwargs):
        """Business roles never grant Django staff or superuser privileges."""
        super().save(*args, **kwargs)


class Company(models.Model):
    """Company/Organization Model"""
    
    class CompanyType(models.TextChoices):
        STARTUP = 'startup', _('Startup')
        PME = 'pme', _('PME')
        ETI = 'eti', _('ETI')
        ENTERPRISE = 'enterprise', _('Grande Entreprise')
        GROUPE = 'groupe', _('Groupe / Holding')
    
    class AccountingStandard(models.TextChoices):
        SYSCOHADA = 'syscohada', _('SYSCOHADA Révisé')
        OHADA = 'ohada', _('OHADA')
        IFRS = 'ifrs', _('IFRS Complets')
        IFRS_PME = 'ifrs_pme', _('IFRS PME')
        PCGE_MAROC = 'pcge_maroc', _('PCGE Maroc')
        SYSCOA = 'syscoa', _('SYSCOA UEMOA')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('company name'), max_length=255)
    legal_name = models.CharField(_('legal name'), max_length=255, blank=True)
    
    # Type & Classification
    company_type = models.CharField(
        max_length=20,
        choices=CompanyType.choices,
        default=CompanyType.STARTUP
    )
    accounting_standard = models.CharField(
        max_length=20,
        choices=AccountingStandard.choices,
        default=AccountingStandard.SYSCOHADA
    )
    
    # Registration
    registration_number = models.CharField(max_length=50, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    vat_number = models.CharField(max_length=50, blank=True)
    trade_register = models.CharField(max_length=50, blank=True)
    
    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Sénégal')
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Contact
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Legal
    legal_form = models.CharField(max_length=100, blank=True)
    capital = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    fiscal_year_start = models.DateField(null=True, blank=True)
    fiscal_year_end = models.DateField(null=True, blank=True)
    
    # Settings
    base_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='XOF')
    timezone = models.CharField(max_length=50, default='Africa/Dakar')
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='fr')

    # Multi-entity
    is_parent = models.BooleanField(default=False)
    parent_company = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subsidiaries'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Subscription
    subscription_plan = models.CharField(
        max_length=20,
        choices=[
            ('free', 'Gratuit'),
            ('startup', 'Startup'),
            ('pme', 'PME'),
            ('enterprise', 'Enterprise'),
            ('groupe', 'Groupe'),
        ],
        default='free'
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Actif'),
            ('trial', 'Essai'),
            ('expired', 'Expiré'),
            ('cancelled', 'Annulé'),
        ],
        default='trial'
    )
    trial_ends = models.DateTimeField(null=True, blank=True)
    
    # Limits
    max_users = models.IntegerField(default=1)
    max_entities = models.IntegerField(default=1)
    
    class Meta:
        verbose_name = _('company')
        verbose_name_plural = _('companies')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_entity_count(self):
        return self.entities.count()
    
    def get_user_count(self):
        return self.users.count()


class Entity(models.Model):
    """Entity/Subsidiary Model for Multi-entity Companies"""
    
    class EntityType(models.TextChoices):
        HEADQUARTERS = 'hq', _('Siège Social')
        BRANCH = 'branch', _('Succursale')
        SUBSIDIARY = 'subsidiary', _('Filiale')
        JV = 'jv', _('Joint-Venture')
        PARTNERSHIP = 'partnership', _('Partenariat')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='entities'
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10, unique=True)
    
    entity_type = models.CharField(
        max_length=20,
        choices=EntityType.choices,
        default=EntityType.BRANCH
    )
    
    # Location
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Sénégal')
    
    # Accounting
    local_currency = models.CharField(max_length=3, default='XOF')
    accounting_standard = models.CharField(
        max_length=20,
        choices=Company.AccountingStandard.choices,
        default=Company.AccountingStandard.SYSCOHADA
    )
    
    # Tax
    tax_id = models.CharField(max_length=50, blank=True)
    vat_number = models.CharField(max_length=50, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('entity')
        verbose_name_plural = _('entities')
        ordering = ['code', 'name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"


class UserActivity(models.Model):
    """User Activity Log"""
    
    class ActivityType(models.TextChoices):
        LOGIN = 'login', _('Connexion')
        LOGOUT = 'logout', _('Déconnexion')
        CREATE = 'create', _('Création')
        UPDATE = 'update', _('Modification')
        DELETE = 'delete', _('Suppression')
        VIEW = 'view', _('Consultation')
        EXPORT = 'export', _('Export')
        IMPORT = 'import', _('Import')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(max_length=20, choices=ActivityType.choices)
    description = models.TextField()
    module = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('user activity')
        verbose_name_plural = _('user activities')
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user} - {self.activity_type} - {self.timestamp}"


class Notification(models.Model):
    """User Notifications"""
    
    class NotificationType(models.TextChoices):
        INFO = 'info', _('Information')
        SUCCESS = 'success', _('Succès')
        WARNING = 'warning', _('Avertissement')
        ERROR = 'error', _('Erreur')
        ALERT = 'alert', _('Alerte')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    
    # Link to related object
    module = models.CharField(max_length=50, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    link = models.URLField(blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user}"
