from django.core.management.base import BaseCommand
from django.conf import settings
from sakinafinance.payments.models import Plan

class Command(BaseCommand):
    help = 'Initialize subscription plans from settings'

    def handle(self, *args, **kwargs):
        plans_data = getattr(settings, 'SUBSCRIPTION_PLANS', {})
        
        if not plans_data:
            self.stdout.write(self.style.WARNING('No subscription plans found in settings.'))
            return
            
        display_order = 1
        for slug, plan_data in plans_data.items():
            plan, created = Plan.objects.update_or_create(
                slug=slug,
                defaults={
                    'name': plan_data.get('name', slug.title()),
                    'price_monthly': plan_data.get('price_monthly', 0),
                    'price_yearly': plan_data.get('price_yearly', 0),
                    'stripe_price_id_monthly': plan_data.get('stripe_price_id_monthly', ''),
                    'stripe_price_id_yearly': plan_data.get('stripe_price_id_yearly', ''),
                    'features': plan_data.get('features', []),
                    'display_order': display_order
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created plan: {plan.name}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Updated plan: {plan.name}'))
                
            display_order += 1
            
        self.stdout.write(self.style.SUCCESS('Successfully initialized all plans.'))
