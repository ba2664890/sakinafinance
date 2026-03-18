from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'financeos.accounts'

    def ready(self):
        import financeos.accounts.signals
