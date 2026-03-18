"""
Admin configuration for Accounts Module
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Company, Entity, UserActivity, Notification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'first_name', 'last_name', 'company', 
        'role', 'user_type', 'is_active', 'date_joined'
    ]
    list_filter = ['is_active', 'role', 'user_type', 'subscription_plan']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'phone', 'avatar')
        }),
        ('Professional Info', {
            'fields': ('job_title', 'department', 'company', 'entity')
        }),
        ('Permissions', {
            'fields': ('role', 'user_type', 'is_active', 'is_staff', 'is_superuser', 'groups')
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'subscription_expires')
        }),
        ('Preferences', {
            'fields': ('language', 'timezone', 'currency')
        }),
        ('Important dates', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'company_type', 'accounting_standard', 
        'base_currency', 'is_active', 'created_at'
    ]
    list_filter = ['company_type', 'accounting_standard', 'is_active']
    search_fields = ['name', 'registration_number', 'tax_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Company Info', {
            'fields': ('name', 'legal_name', 'company_type', 'accounting_standard')
        }),
        ('Registration', {
            'fields': ('registration_number', 'tax_id', 'vat_number', 'trade_register')
        }),
        ('Address', {
            'fields': ('address', 'city', 'country', 'postal_code')
        }),
        ('Contact', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Legal', {
            'fields': ('legal_form', 'capital', 'fiscal_year_start', 'fiscal_year_end')
        }),
        ('Settings', {
            'fields': ('base_currency', 'timezone', 'language')
        }),
        ('Multi-entity', {
            'fields': ('is_parent', 'parent_company')
        }),
        ('Subscription', {
            'fields': ('subscription_plan', 'subscription_status', 'trial_ends', 'max_users', 'max_entities')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'company', 'entity_type', 'country', 'is_active']
    list_filter = ['entity_type', 'country', 'is_active']
    search_fields = ['name', 'code']


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'module', 'timestamp']
    list_filter = ['activity_type', 'module', 'timestamp']
    search_fields = ['user__email', 'description']
    readonly_fields = ['timestamp']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__email']
