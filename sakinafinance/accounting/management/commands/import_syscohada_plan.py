import os
import re
import subprocess
from pathlib import Path
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from sakinafinance.accounting.models import Account, AccountTemplate


CODE_LINE_RE = re.compile(r'^\s*(\d{2,4})\s+(.+?)\s*$')
PAGE_GARBAGE_RE = re.compile(r'^(www\.|contact@|Page\s+\d+\s+sur\s+\d+)', re.IGNORECASE)


def normalize_name(value):
    return re.sub(r'\s+', ' ', value).strip(' \t\r\n-–')


def detect_account_type(class_digit, name):
    name_l = name.lower()

    if class_digit in {'2', '3'}:
        return Account.AccountType.ASSET
    if class_digit == '6':
        return Account.AccountType.EXPENSE
    if class_digit == '7':
        return Account.AccountType.INCOME
    if class_digit == '8':
        if any(word in name_l for word in ['produit', 'reprise', 'revenu', 'gain']):
            return Account.AccountType.INCOME
        return Account.AccountType.EXPENSE
    if class_digit == '1':
        if any(word in name_l for word in ['capital', 'reserve', 'réserve', 'resultat', 'résultat', 'subvention', 'provision reglementee', 'provision réglementée', 'fonds assimil']):
            return Account.AccountType.EQUITY
        return Account.AccountType.LIABILITY

    asset_keywords = ['client', 'debiteur', 'débiteur', 'creance', 'créance', 'avance', 'acomptes verses', 'acomptes versés', 'stocks', 'tresorerie', 'trésorerie', 'banque', 'caisse', 'cheques', 'chèques', 'effets a recevoir', 'effets à recevoir', 'valeurs a encaisser', 'valeurs à encaisser']
    liability_keywords = ['fournisseur', 'dettes', 'dette', 'credit', 'crédit', 'emprunt', 'banques creditrices', 'banques créditrices', 'clients crediteurs', 'clients créditeurs', 'avances recues', 'avances reçues', 'produits constates d avance', 'produits constatés d avance', 'charges a payer', 'charges à payer', 'provision']

    if any(word in name_l for word in asset_keywords):
        return Account.AccountType.ASSET
    if any(word in name_l for word in liability_keywords):
        return Account.AccountType.LIABILITY

    # Fallback for classes 4 and 5
    return Account.AccountType.ASSET


def parse_plan(text):
    accounts = {}

    for line in text.splitlines():
        line = line.strip('\ufeff')
        if not line or PAGE_GARBAGE_RE.match(line):
            continue
        if line.startswith('SYSCOHADA') or line.startswith('Section'):
            continue

        match = CODE_LINE_RE.match(line)
        if not match:
            continue

        code, name = match.group(1), match.group(2)
        # Filter out obvious non-account lines
        if len(code) == 2 and name.isupper() and 'CLASSE' in name:
            continue

        name = normalize_name(name)
        if not name:
            continue

        # Avoid lines that are just page headers or separators
        if 'www.africa' in name.lower() or 'contact@' in name.lower():
            continue

        class_digit = code[0]
        if class_digit not in {'1', '2', '3', '4', '5', '6', '7', '8'}:
            # Class 9 ignored for now (analytic / engagements)
            continue

        existing = accounts.get(code)
        if not existing or len(name) > len(existing['name']):
            accounts[code] = {
                'code': code,
                'name': name,
            }

    return list(accounts.values())


def build_parent_map(accounts):
    by_code = {acc['code']: acc for acc in accounts}
    for acc in accounts:
        code = acc['code']
        acc['level'] = max(1, len(code) - 1)
        acc['parent_code'] = None
        if len(code) == 3:
            acc['parent_code'] = code[:2] if code[:2] in by_code else None
        elif len(code) == 4:
            acc['parent_code'] = code[:3] if code[:3] in by_code else (code[:2] if code[:2] in by_code else None)

    return accounts


class Command(BaseCommand):
    help = "Importe le plan SYSCOHADA dans le référentiel global du plan comptable."

    def add_arguments(self, parser):
        parser.add_argument('--pdf', default='Ohada_syscohada_plan_comptable.pdf')
        parser.add_argument(
            '--accounting-standard',
            default=AccountTemplate.AccountingStandard.SYSCOHADA,
            choices=[choice[0] for choice in AccountTemplate.AccountingStandard.choices],
        )
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--update-existing', action='store_true')

    def handle(self, *args, **options):
        pdf_path = Path(options['pdf'])
        if not pdf_path.exists():
            raise CommandError(f"PDF introuvable: {pdf_path}")

        try:
            result = subprocess.run(
                ['pdftotext', '-layout', str(pdf_path), '-'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as exc:
            raise CommandError("pdftotext est requis pour extraire le plan SYSCOHADA.") from exc
        except subprocess.CalledProcessError as exc:
            raise CommandError(f"pdftotext a echoue: {exc.stderr}") from exc

        accounts = build_parent_map(parse_plan(result.stdout))
        if not accounts:
            raise CommandError("Aucun compte detecte dans le PDF.")

        accounting_standard = options['accounting_standard']
        self.stdout.write(self.style.NOTICE(f"Comptes detectes: {len(accounts)}"))
        self.stdout.write(self.style.NOTICE(f"Norme cible: {accounting_standard}"))
        if options['dry_run']:
            return

        with transaction.atomic():
            existing = {
                acc.code: acc
                for acc in AccountTemplate.objects.filter(accounting_standard=accounting_standard)
            }

            for acc in sorted(accounts, key=lambda a: len(a['code'])):
                code = acc['code']
                name = acc['name']
                class_digit = code[0]
                account_class = class_digit
                account_type = detect_account_type(class_digit, name)
                level = acc['level']
                parent = None
                if acc['parent_code']:
                    parent = existing.get(acc['parent_code'])

                if code in existing:
                    if options['update_existing']:
                        existing_acc = existing[code]
                        existing_acc.name = name
                        existing_acc.account_class = account_class
                        existing_acc.account_type = account_type
                        existing_acc.level = level
                        existing_acc.parent = parent
                        existing_acc.is_system = True
                        existing_acc.is_active = True
                        existing_acc.save(update_fields=['name', 'account_class', 'account_type', 'level', 'parent', 'is_system', 'is_active', 'updated_at'])
                    continue

                new_acc = AccountTemplate.objects.create(
                    accounting_standard=accounting_standard,
                    code=code,
                    name=name,
                    account_class=account_class,
                    account_type=account_type,
                    parent=parent,
                    level=level,
                    is_system=True,
                    is_active=True,
                )
                existing[code] = new_acc

        self.stdout.write(self.style.SUCCESS("Import du référentiel SYSCOHADA termine."))
