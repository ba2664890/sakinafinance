"""
Reusable admin mixins for company scoping in Django admin.
"""

from django.core.exceptions import FieldDoesNotExist


class CompanyScopedAdminMixin:
    """
    Restrict admin list/detail/forms to the current user's company.

    Behavior:
    - Superuser without a company: global access (platform admin mode).
    - Superuser with a company: scoped to that company (tenant admin mode).
    - Non-superuser: always scoped to their company.
    """

    company_lookup = 'company'
    related_company_lookups = (
        'company',
        'user__company',
        'employee__company',
        'project__company',
        'item__company',
        'purchase_order__company',
        'asset__company',
        'subscription__company',
    )

    def _user_company(self, request):
        return getattr(request.user, 'company', None)

    def _should_scope(self, request):
        company = self._user_company(request)
        if request.user.is_superuser:
            return company is not None
        return True

    def _supports_lookup(self, model, lookup):
        if lookup == 'pk':
            return True
        current_model = model
        parts = lookup.split('__')
        for idx, part in enumerate(parts):
            try:
                field = current_model._meta.get_field(part)
            except FieldDoesNotExist:
                return False

            is_last = idx == len(parts) - 1
            if is_last:
                return True
            if not field.is_relation:
                return False
            current_model = field.related_model
        return False

    def _scope_queryset(self, queryset, company):
        model = queryset.model
        if model.__name__ == 'Company':
            return queryset.filter(pk=company.pk)

        if self._supports_lookup(model, self.company_lookup):
            return queryset.filter(**{self.company_lookup: company})

        for lookup in self.related_company_lookups:
            if self._supports_lookup(model, lookup):
                return queryset.filter(**{lookup: company})

        return queryset.none()

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not self._should_scope(request):
            return queryset

        company = self._user_company(request)
        if not company:
            return queryset.none()

        return self._scope_queryset(queryset, company)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if self._should_scope(request):
            company = self._user_company(request)
            queryset = kwargs.get('queryset', db_field.remote_field.model._default_manager.all())
            if company:
                kwargs['queryset'] = self._scope_queryset(queryset, company)
            else:
                kwargs['queryset'] = queryset.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

