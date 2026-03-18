"""
App configuration for Core Module
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financeos.core'
    verbose_name = 'Core'
