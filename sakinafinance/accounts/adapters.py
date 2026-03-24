from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.shortcuts import resolve_url
from .models import Company

class SakinaFinanceSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_login_redirect_url(self, request):
        user = request.user
        if not hasattr(user, 'company') or not user.company:
            return resolve_url('company_setup')
        return super().get_login_redirect_url(request)


class SakinaFinanceAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        user = request.user
        if not hasattr(user, 'company') or not user.company:
            return resolve_url('company_setup')
        return super().get_login_redirect_url(request)
