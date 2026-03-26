"""
URLs for Accounts Module
"""

from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('confirm-email-sent/', views.email_confirmation_sent_view, name='account_email_verification_sent'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    
    # Company
    path('company/setup/', views.company_setup_view, name='company_setup'),
    path('company/settings/', views.company_update_view, name='company_settings'),
    
    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<uuid:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/<uuid:notification_id>/delete/', views.delete_notification, name='delete_notification'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # API
    path('api/user/', views.api_user_info, name='api_user_info'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
]
