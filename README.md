# SakinaFinance - Système d'Intelligence Financière Universel

![SakinaFinance](https://img.shields.io/badge/SakinaFinance-blue)
![Django](https://img.shields.io/badge/Django-5.0-green)
![Python](https://img.shields.io/badge/Python-3.11+-yellow)
![License](https://img.shields.io/badge/License-Enterprise-red)

SakinaFinance est un système d'intelligence financière de nouvelle génération conçu pour répondre aux besoins de toutes les structures — de la startup de 3 personnes au groupe industriel multi-filiales.

## 🎯 Les 6 Piliers

- **VOIR** - Tableaux de bord temps réel. Zéro friction.
- **PRÉDIRE** - ML forecasting. Cash flow à 18 mois.
- **ALERTER** - Anomalies et dérives instantanées.
- **CONSEILLER** - IA générative sur vos données réelles.
- **CONFORMER** - OHADA, IFRS, fiscal, réglementaire.
- **CONSOLIDER** - Multi-entités, multi-devises, groupe.

## 🚀 Modules Complets

### 1. Comptabilité Formelle & Normes Comptables
- Support SYSCOHADA, OHADA, IFRS, IFRS PME, PCGE Maroc, SYSCOA
- Journaux comptables automatisés
- États financiers automatiques (Bilan, CR, TFT)
- Clôture comptable assistée par IA

### 2. Trésorerie & Cash Management
- Gestion multi-comptes & multi-banques
- Prévision de trésorerie par Machine Learning (Prophet, LSTM, XGBoost)
- Gestion du BFR (Besoin en Fonds de Roulement)
- Gestion des risques de change

### 3. Contrôle de Gestion
- Budget & Prévisions
- Comptabilité analytique & Centres de responsabilité
- Tableaux de bord dirigeants

### 4. Achats & Gestion Fournisseurs (Procure-to-Pay)
- Cycle complet Procure-to-Pay
- Intelligence IA sur les achats (OCR, détection doublons)
- Catalogue & Référentiel Fournisseurs

### 5. RH & Paie
- Gestion de la paie (CNSS, IPRES, IRPP)
- Pilotage de la masse salariale
- Multi-pays (Sénégal, Côte d'Ivoire, Maroc, etc.)

### 6. Conformité Fiscale & Réglementaire
- Calendrier fiscal automatique
- Contrôle fiscal interne (Tax Health Check)
- Veille réglementaire par IA

### 7. Gestion de Projets
- Finance par initiative
- Gantt financier
- Calcul ROI automatique

### 8. Relations Investisseurs
- Data Room automatique
- Board Pack & Reporting périodique
- CRM Investisseurs

## 💻 Installation

### Prérequis
- Python 3.11+
- PostgreSQL 14+ (ou SQLite pour le développement)
- Redis (pour Celery)

### Étapes d'installation

1. **Cloner le repository**
```bash
git clone https://github.com/your-org/sakinafinance.git
cd sakinafinance
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos configurations
```

5. **Créer la base de données**
```bash
python manage.py migrate
```

6. **Créer un superutilisateur**
```bash
python manage.py createsuperuser
```

7. **Lancer le serveur de développement**
```bash
python manage.py runserver
```

## 🔧 Configuration

### Google OAuth2
1. Créer un projet sur [Google Cloud Console](https://console.cloud.google.com/)
2. Activer l'API Google+ et OAuth2
3. Créer des identifiants OAuth2
4. Configurer les URIs de redirection
5. Ajouter les clés dans le fichier `.env`

### Stripe
1. Créer un compte sur [Stripe](https://stripe.com/)
2. Obtenir les clés API (test et production)
3. Configurer les webhooks
4. Ajouter les clés dans le fichier `.env`

### Email
Pour Gmail, utiliser un [mot de passe d'application](https://support.google.com/accounts/answer/185833).

## 📁 Structure du Projet

```
sakinafinance/
├── sakinafinance/          # Configuration Django
│   ├── settings.py         # Paramètres
│   ├── urls.py            # URLs principales
│   ├── wsgi.py            # WSGI
│   └── core/              # Module Core
├── accounts/              # Gestion utilisateurs & entreprises
├── accounting/            # Module Comptabilité
├── treasury/              # Module Trésorerie
├── reporting/             # Module Reporting
├── hr/                    # Module RH & Paie
├── procurement/           # Module Achats
├── compliance/            # Module Conformité
├── projects/              # Module Projets
├── ai_engine/             # Module Intelligence Artificielle
├── payments/              # Module Paiements (Stripe)
├── templates/             # Templates HTML
├── static/                # Fichiers statiques
├── media/                 # Fichiers uploadés
├── requirements.txt       # Dépendances Python
├── manage.py             # Commandes Django
└── README.md             # Documentation
```

## 🔐 Authentification

### Authentification par Email
Les utilisateurs peuvent s'inscrire et se connecter avec leur adresse email.

### Authentification Google
Intégration complète avec Google OAuth2 pour une connexion rapide et sécurisée.

### Rôles Utilisateurs
- **Admin** - Accès complet
- **CEO/DG** - Vue exécutive
- **CFO/DAF** - Finance et reporting
- **Comptable** - Comptabilité
- **Trésorier** - Trésorerie
- **Contrôleur de Gestion** - Budget et analyse
- **RH** - Paie et ressources humaines
- **Achats** - Procurement
- **Lecteur** - Consultation uniquement

## 💳 Système de Paiement

### Plans d'abonnement
- **Startup** - 49€/mois
- **PME** - 149€/mois
- **Enterprise** - 499€/mois
- **Groupe** - 1 499€/mois

### Fonctionnalités de paiement
- Paiement par carte (Stripe)
- Abonnements récurrents
- Facturation automatique
- Gestion des méthodes de paiement
- Historique des paiements

## 🤖 Intelligence Artificielle

### Prévision de Trésorerie
- Prophet (Meta) - 3-18 mois
- LSTM (Deep Learning) - 1-6 mois
- ARIMA/SARIMA - 1-3 mois
- XGBoost Regressor - Court terme
- Ensemble Stacking - Réduction variance erreur ~35%

### Détection d'Anomalies
- Dépenses inhabituelles (Isolation Forest)
- Doublons de transaction (Similarité cosinus)
- Budget dépassé (Z-score)
- Fraude potentielle (Autoencoder)

### IA Advisor
- Questions en langage naturel
- Réponses basées sur les données réelles
- RAG (Retrieval-Augmented Generation)

## 🌍 Normes Comptables Supportées

- **SYSCOHADA Révisé** - Afrique subsaharienne (17 pays)
- **OHADA** - Zones OHADA
- **IFRS Complets** - Groupes cotés
- **IFRS PME** - PME avec exigences internationales
- **PCGE Maroc** - Maroc
- **SYSCOA** - UEMOA renforcé

## 📝 API REST

L'API REST complète est disponible à `/api/v1/` avec documentation automatique.

### Authentification API
- Token Authentication
- Session Authentication

### Endpoints principaux
- `/api/v1/users/` - Utilisateurs
- `/api/v1/companies/` - Entreprises
- `/api/v1/accounts/` - Plan comptable
- `/api/v1/transactions/` - Transactions
- `/api/v1/invoices/` - Factures
- `/api/v1/bank-accounts/` - Comptes bancaires
- `/api/v1/forecasts/` - Prévisions
- `/api/v1/employees/` - Employés
- `/api/v1/projects/` - Projets

## 🧪 Tests

```bash
# Lancer tous les tests
python manage.py test

# Lancer les tests d'un module
python manage.py test sakinafinance.accounting

# Avec couverture
coverage run manage.py test
coverage report
```

## 🚀 Déploiement

### Docker
```bash
docker-compose up -d
```

### Production
1. Configurer `DEBUG=False`
2. Configurer `ALLOWED_HOSTS`
3. Configurer SSL/TLS
4. Configurer PostgreSQL
5. Configurer Redis
6. Configurer Celery workers
7. Configurer Nginx

## 📞 Support

- **Email** : support@sakinafinance.ai
- **Documentation** : https://docs.sakinafinance.ai
- **Status** : https://status.sakinafinance.ai

## 📄 Licence

Ce projet est sous licence Enterprise. Tous droits réservés.

## 🙏 Remerciements

- Django Team
- Stripe
- Google Cloud
- OpenAI
- Tous les contributeurs

---

**SakinaFinance** - Le Système d'Intelligence Financière Universel
© 2024 SakinaFinance. Tous droits réservés.
# sakinafinance
