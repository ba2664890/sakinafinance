"""
Views for Accounts Module
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse, reverse_lazy
from .models import User, Company, Entity, Notification, UserActivity
from .forms import UserRegistrationForm, UserLoginForm, CompanyForm, UserProfileForm, ComprehensiveRegistrationForm
from allauth.account.utils import send_email_confirmation


def register_view(request):
    """User Registration View"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ComprehensiveRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create Company
                    company = Company.objects.create(
                        name=form.cleaned_data['company_name'],
                        company_type=form.cleaned_data['company_type'],
                        registration_number=form.cleaned_data['registration_number'],
                        city=form.cleaned_data['city'],
                        country=form.cleaned_data['country'],
                        subscription_plan=form.cleaned_data.get('subscription_plan', 'free')
                    )
                    
                    # Create User
                    user = User.objects.create_user(
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password1'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        company=company,
                        role='admin',
                        subscription_plan=form.cleaned_data.get('subscription_plan', 'free')
                    )
                
                # Send Email Confirmation (Allauth)
                send_email_confirmation(request, user)

                # Create Welcome Notification
                Notification.objects.create(
                    user=user,
                    title="Bienvenue sur SakinaFinance !",
                    message=f"Bonjour {user.first_name}. Votre compte a été créé. Veuillez vérifier votre email pour l'activer.",
                    notification_type='info',
                    module='accounts'
                )

                # Log Activity
                UserActivity.objects.create(
                    user=user,
                    activity_type='create',
                    description=f"Création de compte (en attente de vérification) et entreprise {company.name}",
                    module='accounts',
                    ip_address=request.META.get('REMOTE_ADDR')
                )

                messages.info(request, "Un email de confirmation a été envoyé à votre adresse. Veuillez le consulter pour activer votre compte.")
                return redirect('account_email_verification_sent')
            except Exception as e:
                messages.error(request, f"Une erreur est survenue lors de la création du compte : {str(e)}")
    else:
        form = ComprehensiveRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def email_confirmation_sent_view(request):
    """Email Confirmation Sent View"""
    return render(request, 'accounts/email_confirmation_sent.html')


def login_view(request):
    """User Login View"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(email=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bonjour, {user.first_name} !')
                return redirect('dashboard')
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """User Logout View"""
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('home')


@login_required
def profile_view(request):
    """User Profile View"""
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
        'notifications': Notification.objects.filter(user=user, is_read=False)[:5]
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def company_setup_view(request):
    """Company Setup View"""
    user = request.user
    
    if hasattr(user, 'company') and user.company:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            user = request.user
            company = form.save()
            user.company = company
            user.save()

            # Create Welcome Notification for Social Login Users
            Notification.objects.create(
                user=user,
                title="Configuration Terminée",
                message=f"Votre entreprise {company.name} a été configurée avec succès.",
                notification_type='success',
                module='accounts'
            )

            messages.success(request, 'Entreprise créée avec succès !')
            return redirect('dashboard')
    else:
        form = CompanyForm()
    
    return render(request, 'accounts/company_setup.html', {'form': form})


@login_required
def company_update_view(request):
    """Company Update View"""
    user = request.user
    company = user.company
    
    if not company:
        return redirect('company_setup')
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'Entreprise mise à jour avec succès.')
            return redirect('company_settings')
    else:
        form = CompanyForm(instance=company)
    
    return render(request, 'accounts/company_settings.html', {'form': form})


@login_required
def notifications_view(request):
    """User Notifications View"""
    notifications = Notification.objects.filter(user=request.user)
    unread_count = notifications.filter(is_read=False).count()
    
    context = {
        'notifications': notifications,
        'unread_count': unread_count
    }
    return render(request, 'accounts/notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark Notification as Read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})


@login_required
def mark_all_notifications_read(request):
    """Mark All Notifications as Read"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})


# API Views
@login_required
def api_user_info(request):
    """API: Get User Info"""
    user = request.user
    return JsonResponse({
        'id': str(user.id),
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'role': user.role,
        'company': user.company.name if user.company else None,
        'subscription_plan': user.subscription_plan,
    })


@login_required
def api_notifications(request):
    """API: Get User Notifications"""
    notifications = Notification.objects.filter(user=request.user).values(
        'id', 'title', 'message', 'notification_type', 'is_read', 'created_at'
    )[:10]
    return JsonResponse({'notifications': list(notifications)})
