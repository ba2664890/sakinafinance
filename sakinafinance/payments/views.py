"""
Payments Views - Stripe Integration
"""

import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
import json

from .models import Subscription, PaymentMethod, Invoice, PaymentHistory, Plan

# Initialize Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def pricing_view(request):
    """Pricing Page View"""
    plans = Plan.objects.filter(is_active=True)
    
    context = {
        'plans': plans,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'payments/pricing.html', context)


@login_required
def subscribe_view(request, plan_slug):
    """Subscribe to a Plan"""
    plan = get_object_or_404(Plan, slug=plan_slug, is_active=True)
    user = request.user

    # Check for placeholder Stripe keys (Demo Mode)
    # Improved demo mode detection
    stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    is_demo = not stripe_key or stripe_key == 'sk_test_...' or stripe_key.startswith('sk_test_placeholder')
    
    if settings.DEBUG and is_demo:
        # Mock Stripe flow for demo purposes
        if not user.company:
            messages.warning(request, "Veuillez configurer votre entreprise avant de vous abonner (Mode Demo).")
            return redirect('company_setup')
            
        subscription, created = Subscription.objects.update_or_create(
            user=user,
            defaults={
                'company': user.company,
                'stripe_customer_id': 'cus_mock_123',
                'stripe_subscription_id': 'sub_mock_123',
                'plan': plan.slug,
                'status': 'active',
            }
        )
        user.subscription_plan = plan.slug
        user.save()
        messages.success(request, f'DEMO MODE: Votre abonnement au plan {plan.name} a été activé sans transaction réelle.')
        return redirect('dashboard')
     # Ensure user has a company
    if not user.company:
        messages.warning(request, "Veuillez configurer votre entreprise avant de vous abonner.")
        return redirect('company_setup')

    # Get or create Stripe customer
    try:
        subscription = Subscription.objects.get(user=user)
        customer_id = subscription.stripe_customer_id
    except Subscription.DoesNotExist:
        # Create new Stripe customer
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.get_full_name(),
                metadata={
                    'user_id': str(user.id),
                    'company_id': str(user.company.id),
                }
            )
            customer_id = customer.id
        except Exception as e:
            messages.error(request, f"Erreur lors de la création du client Stripe: {str(e)}")
            return redirect('pricing')
    
    # Create Stripe Checkout Session
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan.stripe_price_id_monthly,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri('/payments/success/') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri('/payments/cancel/'),
            metadata={
                'user_id': str(user.id),
                'plan': plan.slug,
            }
        )
        return redirect(session.url)
    except Exception as e:
        messages.error(request, f"Erreur Stripe: {str(e)}. Veuillez vérifier vos IDs de prix dans settings.py ou utiliser le mode Demo.")
        return redirect('pricing')


@login_required
def subscription_success_view(request):
    """Subscription Success Callback"""
    session_id = request.GET.get('session_id')
    
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            # Update or create subscription
            subscription, created = Subscription.objects.update_or_create(
                user=request.user,
                defaults={
                    'company': request.user.company,
                    'stripe_customer_id': session.customer,
                    'stripe_subscription_id': session.subscription,
                    'plan': session.metadata.get('plan'),
                    'status': 'active',
                }
            )
            
            # Update user's subscription plan
            user = request.user
            user.subscription_plan = session.metadata.get('plan')
            user.save()
            
            messages.success(request, 'Votre abonnement a été activé avec succès !')
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'activation: {str(e)}')
    
    return redirect('dashboard')


@login_required
def subscription_cancel_view(request):
    """Subscription Cancel Callback"""
    messages.info(request, 'L\'abonnement a été annulé.')
    return redirect('pricing')


@login_required
def manage_subscription_view(request):
    """Manage Subscription View"""
    user = request.user
    
    try:
        subscription = Subscription.objects.get(user=user)
        payment_methods = PaymentMethod.objects.filter(user=user, is_active=True)
        invoices = Invoice.objects.filter(subscription=subscription)[:10]
    except Subscription.DoesNotExist:
        subscription = None
        payment_methods = []
        invoices = []
    
    context = {
        'subscription': subscription,
        'payment_methods': payment_methods,
        'invoices': invoices,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'payments/manage.html', context)


@login_required
def cancel_subscription_view(request):
    """Cancel Subscription"""
    if request.method == 'POST':
        try:
            subscription = Subscription.objects.get(user=request.user)
            
            # Check for placeholder Stripe keys (Demo Mode)
            # Improved demo mode detection
            stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
            is_demo = not stripe_key or stripe_key == 'sk_test_...' or stripe_key.startswith('sk_test_placeholder')
                    
            if settings.DEBUG and is_demo:
                # Mock cancellation
                pass
            else:
                # Cancel in Stripe
                stripe.Subscription.delete(subscription.stripe_subscription_id)
            
            # Update local subscription
            subscription.status = 'canceled'
            subscription.canceled_at = timezone.now()
            subscription.save()
            
            # Update user
            user = request.user
            user.subscription_plan = 'free'
            user.save()
            
            messages.success(request, 'Votre abonnement a été annulé.')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('manage_subscription')


@login_required
def add_payment_method_view(request):
    """Add Payment Method"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            payment_method_id = data.get('payment_method_id')
            
            # Check for placeholder Stripe keys (Demo Mode)
            # Improved demo mode detection
            stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
            is_demo = not stripe_key or stripe_key == 'sk_test_...' or stripe_key.startswith('sk_test_placeholder')
                    
            # Get or create customer
            if settings.DEBUG and is_demo:
                customer_id = 'cus_mock_123'
                pm_brand = 'Visa'
                pm_last4 = '4242'
                pm_exp_month = 12
                pm_exp_year = 2030
            else:
                try:
                    subscription = Subscription.objects.get(user=request.user)
                    customer_id = subscription.stripe_customer_id
                except Subscription.DoesNotExist:
                    customer = stripe.Customer.create(
                        email=request.user.email,
                        name=f"{request.user.first_name} {request.user.last_name}",
                    )
                    customer_id = customer.id
                
                # Attach payment method to customer
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=customer_id,
                )
                
                # Get payment method details
                pm = stripe.PaymentMethod.retrieve(payment_method_id)
                pm_brand = pm.card.brand
                pm_last4 = pm.card.last4
                pm_exp_month = pm.card.exp_month
                pm_exp_year = pm.card.exp_year
            
            # Save to database
            PaymentMethod.objects.create(
                user=request.user,
                stripe_payment_method_id=payment_method_id if not is_demo else 'pm_mock_123',
                stripe_customer_id=customer_id,
                card_brand=pm_brand,
                card_last4=pm_last4,
                card_exp_month=pm_exp_month,
                card_exp_year=pm_exp_year,
                is_default=True,
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@login_required
def remove_payment_method_view(request, method_id):
    """Remove Payment Method"""
    if request.method == 'POST':
        try:
            payment_method = get_object_or_404(
                PaymentMethod,
                id=method_id,
                user=request.user
            )
            
            # Check for placeholder Stripe keys (Demo Mode)
            # Improved demo mode detection
            stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
            is_demo = not stripe_key or stripe_key == 'sk_test_...' or stripe_key.startswith('sk_test_placeholder')
                    
            if not (settings.DEBUG and is_demo):
                # Detach from Stripe
                stripe.PaymentMethod.detach(payment_method.stripe_payment_method_id)
            
            # Deactivate locally
            payment_method.is_active = False
            payment_method.save()
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@login_required
def invoices_view(request):
    """View Invoices"""
    try:
        subscription = Subscription.objects.get(user=request.user)
        invoices = Invoice.objects.filter(subscription=subscription)
    except Subscription.DoesNotExist:
        invoices = []
    
    context = {
        'invoices': invoices,
    }
    return render(request, 'payments/invoices.html', context)


@csrf_exempt
def stripe_webhook(request):
    """Stripe Webhook Handler"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return JsonResponse({'status': 'invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'status': 'invalid signature'}, status=400)
    
    # Handle events
    if event['type'] == 'invoice.payment_succeeded':
        handle_payment_succeeded(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(event['data']['object'])
    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    
    return JsonResponse({'status': 'success'})


def handle_payment_succeeded(invoice):
    """Handle successful payment"""
    subscription_id = invoice.get('subscription')
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        
        # Create invoice record
        Invoice.objects.create(
            subscription=subscription,
            invoice_number=invoice.get('number'),
            stripe_invoice_id=invoice.get('id'),
            subtotal=invoice.get('subtotal') / 100,
            tax_amount=invoice.get('tax') / 100,
            total=invoice.get('total') / 100,
            currency=invoice.get('currency').upper(),
            status='paid',
            invoice_date=timezone.now(),
            due_date=timezone.now(),
            paid_at=timezone.now(),
        )
        
        # Create payment history
        PaymentHistory.objects.create(
            user=subscription.user,
            amount=invoice.get('amount_paid') / 100,
            currency=invoice.get('currency').upper(),
            status='succeeded',
            stripe_payment_intent_id=invoice.get('payment_intent'),
            processed_at=timezone.now(),
        )
    except Subscription.DoesNotExist:
        pass


def handle_payment_failed(invoice):
    """Handle failed payment"""
    subscription_id = invoice.get('subscription')
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        subscription.status = 'past_due'
        subscription.save()
        
        # Create payment history
        PaymentHistory.objects.create(
            user=subscription.user,
            amount=invoice.get('amount_due') / 100,
            currency=invoice.get('currency').upper(),
            status='failed',
            error_message='Payment failed',
        )
    except Subscription.DoesNotExist:
        pass


def handle_subscription_updated(subscription_data):
    """Handle subscription update"""
    subscription_id = subscription_data.get('id')
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        subscription.status = subscription_data.get('status')
        subscription.current_period_start = timezone.datetime.fromtimestamp(
            subscription_data.get('current_period_start')
        )
        subscription.current_period_end = timezone.datetime.fromtimestamp(
            subscription_data.get('current_period_end')
        )
        subscription.save()
    except Subscription.DoesNotExist:
        pass


def handle_subscription_deleted(subscription_data):
    """Handle subscription deletion"""
    subscription_id = subscription_data.get('id')
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        subscription.status = 'canceled'
        subscription.canceled_at = timezone.now()
        subscription.save()
        
        # Update user
        user = subscription.user
        user.subscription_plan = 'free'
        user.save()
    except Subscription.DoesNotExist:
        pass
