from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from allauth.account.signals import email_confirmed
from .models import Notification

@receiver(email_confirmed)
def send_welcome_email_after_confirmation(request, email_address, **kwargs):
    """
    Sends a welcome email and creates a notification after the user confirms their email.
    """
    user = email_address.user
    company = getattr(user, 'company', None)
    company_name = company.name if company else "votre entreprise"

    # 1. Create Welcome Notification
    Notification.objects.create(
        user=user,
        title="Compte Activé !",
        message=f"Félicitations {user.first_name}, votre compte SakinaFinance est désormais actif et votre entreprise {company_name} est prête.",
        notification_type='success',
        module='accounts'
    )

    # 2. Send Welcome Email
    try:
        subject = "Bienvenue sur SakinaFinance - Compte Activé !"
        context = {
            'first_name': user.first_name,
            'email': user.email,
            'company_name': company_name,
            'dashboard_url': request.build_absolute_uri(reverse('dashboard'))
        }
        # Charger les versions HTML et Texte
        html_message = render_to_string('emails/welcome.html', context)
        plain_message = render_to_string('emails/welcome.txt', context)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False  # On veut voir les erreurs en DEBUG
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending welcome email after confirmation: {e}")
