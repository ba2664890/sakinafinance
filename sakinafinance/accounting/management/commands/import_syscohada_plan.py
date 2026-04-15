"""
Management command : importe le plan comptable SYSCOHADA depuis le PDF officiel.

Corrections et améliorations par rapport à la version initiale :
  1. Gestion des noms multi-lignes (continuation lines).
  2. Suppression des marqueurs de notes de bas de page (() , (1), (2)…).
  3. detect_account_type : logique par préfixe numérique plutôt que mots-clés
     fragiles pour les classes 1, 4, 5 et 8.
  4. build_parent_map : remonte la chaîne de parenté de manière générique.
  5. Encodage UTF-8 explicite pour pdftotext.
  6. Compteurs créés / mis à jour / ignorés en sortie.
  7. --verbose-dry-run pour inspecter les comptes détectés.
  8. Message d'erreur clair quand pdftotext est absent.
  9. Corrections orthographiques connues du PDF (IMMOBLISATIONS → IMMOBILISATIONS).
"""

import re
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from sakinafinance.accounting.models import Account, AccountTemplate


# ---------------------------------------------------------------------------
# Patterns de compilation
# ---------------------------------------------------------------------------

# Ligne de compte : 2 à 4 chiffres, au moins un espace, puis l'intitulé.
CODE_LINE_RE = re.compile(r'^\s*(\d{2,4})\s{1,}(.+?)\s*$')

# En-têtes/pieds de page à ignorer.
PAGE_GARBAGE_RE = re.compile(
    r'^(www\.|contact@|Page\s+\d+\s+sur\s+\d+|SYSCOHADA\s*:)',
    re.IGNORECASE,
)

# Marqueurs de notes de bas de page en fin de nom : (), (1), (2), (1, (².
FOOTNOTE_SUFFIX_RE = re.compile(r'\s*\(\s*[¹²³1-3]?\s*\)\s*$|\s*\(\s*[¹²³1-3]\s*$')

# Lignes composées uniquement d'un exposant typographique.
FOOTNOTE_ONLY_RE = re.compile(r'^\s*[¹²³]\s*$')

# Corrections orthographiques connues dans ce PDF.
_PDF_TYPOS: dict[str, str] = {
    'IMMOBLISATIONS': 'IMMOBILISATIONS',
    'INSANCE': 'INSTANCE',
}


# ---------------------------------------------------------------------------
# Utilitaires de nettoyage
# ---------------------------------------------------------------------------

def normalize_name(value: str) -> str:
    """
    Nettoie un intitulé de compte :
      - supprime les marqueurs de notes de bas de page en fin de chaîne,
      - normalise les espaces multiples,
      - retire les tirets/espaces en début et fin,
      - corrige les fautes connues du PDF.
    """
    value = FOOTNOTE_SUFFIX_RE.sub('', value)
    value = re.sub(r'\s+', ' ', value)
    value = value.strip(' \t\r\n-–')
    for wrong, right in _PDF_TYPOS.items():
        value = value.replace(wrong, right)
    return value


def _is_continuation(line: str) -> bool:
    """
    Retourne True si la ligne ressemble à la suite d'un intitulé de compte
    (pas un code, pas un en-tête de section, pas vide).
    """
    stripped = line.strip()
    if not stripped:
        return False
    if CODE_LINE_RE.match(line):
        return False
    if PAGE_GARBAGE_RE.match(stripped):
        return False
    if FOOTNOTE_ONLY_RE.match(stripped):
        return False
    # Les en-têtes de section commencent souvent par "Section", "A -", "B -", etc.
    if re.match(r'^(Section|[A-Z]\s*[-–])\s', stripped):
        return False
    return stripped[0].isalpha()


# ---------------------------------------------------------------------------
# Détection du type de compte
# ---------------------------------------------------------------------------

# Racines à deux chiffres dont la nature comptable est déterministe
# dans le référentiel SYSCOHADA.
_CLASS1_EQUITY_ROOTS = {'10', '11', '12', '13', '14', '15'}
_CLASS1_LIABILITY_ROOTS = {'16', '17', '18', '19'}

_CLASS4_ALWAYS_ASSET = {
    '409',  # Fournisseurs débiteurs
    '421',  # Personnel, avances et acomptes
    '414',  # Créances sur cessions d'immobilisations
    '415',  # Clients, effets escomptés non échus
    '416',  # Créances litigieuses/douteuses
    '418',  # Clients, produits à recevoir
    '449',  # État, créances diverses
    '471', '472', '474', '475', '476',  # Divers actif
    '485', '486', '488',  # Créances HAO
}
_CLASS4_ALWAYS_LIABILITY = {
    '401', '402', '408',  # Fournisseurs dettes
    '419',  # Clients créditeurs
    '422', '423', '424', '425', '426', '427', '428',  # Personnel dettes
    '431', '432', '433', '438',  # Organismes sociaux
    '441', '442', '443', '444', '445', '446', '447', '448',  # État/TVA
    '461', '462', '463', '465', '466',  # Associés dettes
    '477',  # Produits constatés d'avance
    '478', '479',  # Écarts de conversion
    '481', '482', '483', '484',  # Fournisseurs d'investissements / dettes HAO
    '490', '491', '492', '493', '494',  # Dépréciations tiers
    '495', '496', '497', '498', '499',
}

# Pour les préfixes à 2 chiffres de la classe 4 non couverts ci-dessus :
_CLASS4_TWO_DIGIT_DEFAULT = {
    '40': Account.AccountType.LIABILITY,  # Fournisseurs
    '41': Account.AccountType.ASSET,      # Clients
    '42': Account.AccountType.LIABILITY,  # Personnel dettes
    '43': Account.AccountType.LIABILITY,  # Organismes sociaux
    '44': Account.AccountType.LIABILITY,  # État
    '45': Account.AccountType.ASSET,      # Organismes internationaux (créances)
    '46': Account.AccountType.LIABILITY,  # Associés
    '47': Account.AccountType.ASSET,      # Divers débiteurs
    '48': Account.AccountType.LIABILITY,  # HAO dettes
    '49': Account.AccountType.LIABILITY,  # Dépréciations
}


def detect_account_type(class_digit: str, code: str, name: str) -> str:
    """
    Détermine le type de compte (ASSET, LIABILITY, EQUITY, EXPENSE, INCOME)
    en s'appuyant prioritairement sur la structure numérique du plan SYSCOHADA
    plutôt que sur des mots-clés fragiles.
    """
    name_l = name.lower()
    two = code[:2]
    three = code[:3] if len(code) >= 3 else ''

    # ---- Classe 2 : Actif immobilisé ----------------------------------------
    if class_digit == '2':
        return Account.AccountType.ASSET

    # ---- Classe 3 : Stocks --------------------------------------------------
    if class_digit == '3':
        return Account.AccountType.ASSET

    # ---- Classe 6 : Charges -------------------------------------------------
    if class_digit == '6':
        return Account.AccountType.EXPENSE

    # ---- Classe 7 : Produits ------------------------------------------------
    if class_digit == '7':
        return Account.AccountType.INCOME

    # ---- Classe 8 : Autres charges/produits ---------------------------------
    # Structure : paires impair/pair → charge/produit (81/82, 83/84, 85/86)
    # 87 Participation travailleurs = charge ; 88 Subventions équilibre = produit
    # 89 Impôts sur résultat = charge
    if class_digit == '8':
        income_roots = {'82', '84', '86', '88'}
        expense_roots = {'81', '83', '85', '87', '89'}
        if two in income_roots:
            return Account.AccountType.INCOME
        if two in expense_roots:
            return Account.AccountType.EXPENSE
        # Fallback par mots-clés pour les sous-comptes non couverts
        if any(w in name_l for w in ('produit', 'reprise', 'revenu', 'gain')):
            return Account.AccountType.INCOME
        return Account.AccountType.EXPENSE

    # ---- Classe 1 : Ressources durables -------------------------------------
    # 10-15 : capitaux propres ; 16-19 : dettes financières
    if class_digit == '1':
        if two in _CLASS1_EQUITY_ROOTS:
            return Account.AccountType.EQUITY
        if two in _CLASS1_LIABILITY_ROOTS:
            return Account.AccountType.LIABILITY
        # Ne devrait pas arriver ; sécurité
        return Account.AccountType.LIABILITY

    # ---- Classe 4 : Comptes de tiers ----------------------------------------
    if class_digit == '4':
        if three in _CLASS4_ALWAYS_ASSET:
            return Account.AccountType.ASSET
        if three in _CLASS4_ALWAYS_LIABILITY:
            return Account.AccountType.LIABILITY
        default = _CLASS4_TWO_DIGIT_DEFAULT.get(two)
        if default is not None:
            return default
        return Account.AccountType.ASSET  # filet de sécurité

    # ---- Classe 5 : Trésorerie ----------------------------------------------
    # 56 = crédits de trésorerie / découverts → passif
    if class_digit == '5':
        if two == '56':
            return Account.AccountType.LIABILITY
        if 'crédit de trésorerie' in name_l or 'credit de tresorerie' in name_l:
            return Account.AccountType.LIABILITY
        # 59 = dépréciations → contra-actif, on le met en ASSET par convention
        return Account.AccountType.ASSET

    # Filet de sécurité final
    return Account.AccountType.ASSET


# ---------------------------------------------------------------------------
# Parsing du texte extrait
# ---------------------------------------------------------------------------

def parse_plan(text: str) -> list[dict]:
    """
    Parse le texte brut produit par `pdftotext -layout` et retourne la liste
    des comptes détectés sous la forme :
        [{'code': str, 'name': str}, ...]

    Gère les intitulés multi-lignes en détectant les lignes de continuation.
    """
    accounts: dict[str, dict] = {}
    last_code: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip('\ufeff')
        stripped = line.strip()

        # Ligne vide → coupe le contexte de continuation
        if not stripped:
            last_code = None
            continue

        # En-têtes / pieds de page
        if PAGE_GARBAGE_RE.match(stripped):
            continue

        # Ligne de note seule (², ³…)
        if FOOTNOTE_ONLY_RE.match(stripped):
            continue

        # En-têtes de sections textuelles
        if stripped.startswith('Section') or re.match(r'^[A-Z]\s*[-–]\s*[A-ZÉÀÈÊÎ]', stripped):
            last_code = None
            continue

        # ---- Tentative de matching d'une ligne de compte --------------------
        match = CODE_LINE_RE.match(line)
        if match:
            code, raw_name = match.group(1), match.group(2)

            # Ignorer les lignes d'en-tête de classe ("10 CLASSE 1", etc.)
            if len(code) == 2 and 'CLASSE' in raw_name.upper():
                last_code = None
                continue

            # Ignorer les URLs/contacts éventuellement capturés
            if 'africa' in raw_name.lower() or 'contact@' in raw_name.lower():
                last_code = None
                continue

            # Ignorer la classe 9 (analytique, facultatif)
            class_digit = code[0]
            if class_digit not in {'1', '2', '3', '4', '5', '6', '7', '8'}:
                last_code = None
                continue

            name = normalize_name(raw_name)
            if not name:
                last_code = None
                continue

            # De-duplication : conserver l'intitulé le plus long en cas de
            # répétition du même code (tables résumées + détail dans le PDF).
            existing = accounts.get(code)
            if not existing or len(name) > len(existing['name']):
                accounts[code] = {'code': code, 'name': name}

            last_code = code

        # ---- Ligne de continuation possible ---------------------------------
        elif last_code is not None and _is_continuation(line):
            continuation = normalize_name(stripped)
            if continuation:
                accounts[last_code]['name'] += ' ' + continuation
                # Ne pas réinitialiser last_code : possibilité de 3e ligne.
        else:
            last_code = None

    return list(accounts.values())


# ---------------------------------------------------------------------------
# Construction de la hiérarchie parent/enfant
# ---------------------------------------------------------------------------

def build_parent_map(accounts: list[dict]) -> list[dict]:
    """
    Enrichit chaque compte avec :
      - level        : 1 pour codes 2 chiffres, 2 pour 3 chiffres, 3 pour 4 chiffres
      - parent_code  : préfixe le plus long présent dans le plan, ou None
    """
    by_code: set[str] = {acc['code'] for acc in accounts}

    for acc in accounts:
        code = acc['code']
        acc['level'] = len(code) - 1  # 2→1, 3→2, 4→3

        # Remonte la chaîne : 4321 → 432 → 43 → rien
        parent_code = None
        for prefix_len in range(len(code) - 1, 1, -1):
            prefix = code[:prefix_len]
            if prefix in by_code:
                parent_code = prefix
                break
        acc['parent_code'] = parent_code

    return accounts


# ---------------------------------------------------------------------------
# Commande Django
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Importe le plan SYSCOHADA dans le référentiel global du plan comptable."

    def add_arguments(self, parser):
        parser.add_argument(
            '--pdf',
            default='Ohada_syscohada_plan_comptable.pdf',
            help="Chemin vers le PDF du plan comptable SYSCOHADA.",
        )
        parser.add_argument(
            '--accounting-standard',
            default=AccountTemplate.AccountingStandard.SYSCOHADA,
            choices=[c[0] for c in AccountTemplate.AccountingStandard.choices],
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Affiche les statistiques sans écrire en base.",
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help="Met à jour les comptes déjà présents en base.",
        )
        parser.add_argument(
            '--verbose-dry-run',
            action='store_true',
            help="En dry-run, affiche les 30 premiers comptes détectés avec leur type.",
        )

    def handle(self, *args, **options):  # noqa: C901
        pdf_path = Path(options['pdf'])
        if not pdf_path.exists():
            raise CommandError(f"PDF introuvable : {pdf_path}")

        self.stdout.write(f"Extraction du texte depuis {pdf_path} …")
        try:
            result = subprocess.run(
                ['pdftotext', '-layout', str(pdf_path), '-'],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',   # ← encodage explicite (UTF-8 du PDF)
            )
        except FileNotFoundError as exc:
            raise CommandError(
                "pdftotext est introuvable. Installez le paquet poppler-utils :\n"
                "  sudo apt install poppler-utils   # Debian/Ubuntu\n"
                "  brew install poppler             # macOS"
            ) from exc
        except subprocess.CalledProcessError as exc:
            raise CommandError(
                f"pdftotext a échoué (code {exc.returncode}) :\n{exc.stderr}"
            ) from exc

        accounts = build_parent_map(parse_plan(result.stdout))

        if not accounts:
            raise CommandError(
                "Aucun compte détecté dans le PDF. "
                "Vérifiez que le fichier est bien le plan comptable SYSCOHADA."
            )

        # ---- Statistiques par classe ----------------------------------------
        by_class: dict[str, list] = {}
        for acc in accounts:
            by_class.setdefault(acc['code'][0], []).append(acc)

        self.stdout.write(self.style.NOTICE(f"\nComptes détectés : {len(accounts)}"))
        for cls in sorted(by_class):
            self.stdout.write(f"  Classe {cls} : {len(by_class[cls])} comptes")

        accounting_standard = options['accounting_standard']
        self.stdout.write(self.style.NOTICE(f"Norme cible : {accounting_standard}"))

        # ---- Prévisualisation (dry-run verbose) -----------------------------
        if options.get('verbose_dry_run') or options['dry_run']:
            self.stdout.write("\n--- Aperçu (30 premiers comptes triés par code) ---")
            for acc in sorted(accounts, key=lambda a: a['code'])[:30]:
                atype = detect_account_type(acc['code'][0], acc['code'], acc['name'])
                self.stdout.write(
                    f"  {acc['code']:<6s}  {acc['name'][:55]:<55s}"
                    f"  [{atype:<12s}]  parent={acc['parent_code']}"
                )

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("\nDry-run : aucune écriture en base."))
            return

        # ---- Import en base -------------------------------------------------
        created_count = updated_count = skipped_count = 0

        with transaction.atomic():
            existing: dict[str, AccountTemplate] = {
                obj.code: obj
                for obj in AccountTemplate.objects.filter(
                    accounting_standard=accounting_standard
                )
            }

            # Tri par longueur de code pour garantir que les parents
            # sont créés avant leurs enfants.
            for acc in sorted(accounts, key=lambda a: len(a['code'])):
                code = acc['code']
                name = acc['name']
                class_digit = code[0]
                account_type = detect_account_type(class_digit, code, name)
                level = acc['level']
                parent = existing.get(acc['parent_code']) if acc['parent_code'] else None

                if code in existing:
                    if options['update_existing']:
                        obj = existing[code]
                        obj.name = name
                        obj.account_class = class_digit
                        obj.account_type = account_type
                        obj.level = level
                        obj.parent = parent
                        obj.is_system = True
                        obj.is_active = True
                        obj.save(update_fields=[
                            'name', 'account_class', 'account_type',
                            'level', 'parent', 'is_system', 'is_active',
                            'updated_at',
                        ])
                        updated_count += 1
                    else:
                        skipped_count += 1
                    continue

                new_obj = AccountTemplate.objects.create(
                    accounting_standard=accounting_standard,
                    code=code,
                    name=name,
                    account_class=class_digit,
                    account_type=account_type,
                    parent=parent,
                    level=level,
                    is_system=True,
                    is_active=True,
                )
                existing[code] = new_obj
                created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nImport terminé : "
            f"{created_count} créés, "
            f"{updated_count} mis à jour, "
            f"{skipped_count} ignorés (déjà présents)."
        ))