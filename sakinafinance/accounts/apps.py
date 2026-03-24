from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sakinafinance.accounts'

    def ready(self):
        import sakinafinance.accounts.signals
