import os
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings

class Command(BaseCommand):
    help = 'Initialize Google SocialApp with credentials from .env'

    def handle(self, *args, **options):
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

        if not client_id or not client_secret:
            self.stdout.write(self.style.ERROR('GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not found in environment'))
            return

        # Ensure site exists
        site, created = Site.objects.get_or_create(
            id=settings.SITE_ID,
            defaults={'domain': '127.0.0.1:8000', 'name': 'FinanceOS IA'}
        )

        # Create or update SocialApp
        app, created = SocialApp.objects.get_or_create(
            provider='google',
            defaults={
                'name': 'Google Login',
                'client_id': client_id,
                'secret': client_secret,
            }
        )
        
        if not created:
            app.client_id = client_id
            app.secret = client_secret
            app.save()
            self.stdout.write(self.style.SUCCESS('Google SocialApp updated'))
        else:
            self.stdout.write(self.style.SUCCESS('Google SocialApp created'))

        app.sites.add(site)
        self.stdout.write(self.style.SUCCESS(f'Google SocialApp linked to site {site.domain}'))
