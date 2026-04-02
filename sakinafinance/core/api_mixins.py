"""
Shared API mixins for tenant-aware REST endpoints.
"""

from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError


class CompanyScopedViewSetMixin:
    """Filter querysets and writable relations to the authenticated company."""

    company_field = 'company'

    def get_user_company(self):
        return getattr(self.request.user, 'company', None)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        company = self.get_user_company()

        if getattr(user, 'is_superuser', False):
            return queryset

        if self.company_field == 'self':
            return queryset.filter(pk=getattr(company, 'pk', None)) if company else queryset.none()

        if not company:
            return queryset.none()

        return queryset.filter(**{self.company_field: company})

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        target = serializer.child if hasattr(serializer, 'child') else serializer
        user = self.request.user
        company = self.get_user_company()

        if getattr(user, 'is_superuser', False) or not company:
            return serializer

        for field in getattr(target, 'fields', {}).values():
            queryset = getattr(field, 'queryset', None)
            if queryset is None:
                continue

            model = getattr(queryset, 'model', None)
            if model is None:
                continue

            if hasattr(model, 'company'):
                field.queryset = queryset.filter(company=company)
            elif model.__name__ == 'Company':
                field.queryset = queryset.filter(pk=company.pk)

        return serializer

    def perform_create(self, serializer):
        model = getattr(getattr(serializer, 'Meta', None), 'model', None)
        user = self.request.user
        company = self.get_user_company()
        save_kwargs = {}

        if model and not getattr(user, 'is_superuser', False):
            if hasattr(model, 'company'):
                if not company:
                    raise ValidationError({'company': "Aucune entreprise n'est associée à cet utilisateur."})
                save_kwargs['company'] = company

            if hasattr(model, 'entity') and getattr(user, 'entity', None):
                save_kwargs.setdefault('entity', user.entity)

        if model and hasattr(model, 'created_by'):
            save_kwargs['created_by'] = user

        serializer.save(**save_kwargs)


class CompanyScopedModelViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class CompanyScopedReadOnlyViewSet(CompanyScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
