"""
App configuration for Core Module
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sakinafinance.core'
    verbose_name = 'Core'
