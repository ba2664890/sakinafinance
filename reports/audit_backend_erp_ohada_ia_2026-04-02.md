# Audit Complet du Backend SakinaFinance

## Evaluation technique, comptable, ERP et IA

Date de production: 2026-04-02
Heure locale: 15:07 EDT
Perimetre: backend Django, modeles, calculs, endpoints, couverture fonctionnelle ERP, pertinence comptable OHADA, capacites IA, robustesse runtime

### Resume executif

Le backend audite presente une base de travail serieuse pour une plateforme de pilotage financier, mais il n'est pas encore au niveau d'un ERP complet, integral et fiable de classe entreprise. La structure applicative est large, avec des domaines bien identifies, mais plusieurs modules sont encore au stade de squelette, certains calculs sont simplifies ou incorrects, et le coeur comptable n'offre pas encore les garanties attendues pour une production comptable conforme et auditable.

Sur l'axe metier, le principal constat est le suivant: la plateforme sait afficher des indicateurs, mais elle ne dispose pas encore d'un moteur transactionnel comptable assez rigoureux pour garantir des chiffres exhaustifs, traces, repostables et explicables. Sur l'axe ERP, les cycles Order-to-Cash, Procure-to-Pay, Treasury-to-Accounting, Fixed Assets, Payroll-to-GL et Tax-to-GL sont encore incomplets. Sur l'axe IA, la plateforme dispose d'une couche de demonstration convaincante, mais l'IA n'est pas encore suffisamment branchee sur des donnees comptables fiabilisees, gouvernees et historisees pour jouer le role d'assistant financier de production.

Le projet est donc mieux decrit aujourd'hui comme un prototype avance de plateforme de gestion financiere et d'analyse IA que comme un ERP financier complet oriente OHADA, pret pour un usage critique en entreprise.

### Methodologie de l'audit

L'audit a ete mene selon quatre axes:

- revue de l'architecture Django et des applications metier;
- revue des modeles de donnees, relations, contraintes et calculs;
- revue des vues et API, avec attention particuliere a la securite, au multi-tenant et a la coherence fonctionnelle;
- verification runtime avec `manage.py check` et execution de tests disponibles dans un environnement local.

L'analyse a egalement ete relue avec un prisme finance et comptabilite OHADA:

- pertinence du grand livre et de la balance;
- capacite a produire des etats financiers fiables;
- solidite des calculs de tresorerie, fiscalite, paie et amortissements;
- capacite du systeme a supporter un referentiel SYSCOHADA/AUDCIF de maniere industrielle.

### Cartographie du backend

Le monolithe Django est structure autour des domaines suivants:

- `accounts`: utilisateurs, entreprises, entites, activite utilisateur, notifications;
- `accounting`: plan comptable, journaux, ecritures, lignes d'ecriture, factures, etats financiers, declarations fiscales, immobilisations, consolidation;
- `treasury`: vues de pilotage tresorerie, mais sans modeles metier dedies;
- `reporting`: vues de reporting, sans modeles metier dedies;
- `hr`: departements, postes, employes, conges, periodes de paie, bulletins, recrutement;
- `procurement`: fournisseurs, RFQ, bons de commande, receptions, inventaire, mouvements de stock;
- `compliance`: taxes, declarations, exigences reglementaires, risques de conformite;
- `projects`: projets, taches, jalons, temps, budget projet;
- `ai_engine`: analyses IA, previsions de tresorerie, insights, anomalies, OCR, base de connaissance RAG;
- `payments`: abonnements, moyens de paiement, facturation Stripe.

Cette cartographie est positive: le decoupage fonctionnel est logique et couvre l'essentiel des briques qu'un ERP financier moderne doit proposer. En revanche, la profondeur d'implementation est tres heterogene selon les domaines.

[[PAGEBREAK]]

## Partie 1 - Constat general de maturite

### 1.1 Points forts de l'existant

- Le projet est deja structure par domaines ERP clairs et lisibles.
- Les modeles couvrent plusieurs objets metier critiques: ecritures comptables, immobilisations, fournisseurs, employes, projets, risques, documents IA.
- Le module `ai_engine` est plus avance que la moyenne des prototypes: RAG, OCR, insights, forecasting, ChromaDB et base documentaire sont deja presents.
- Les applications `accounting`, `hr`, `procurement`, `projects` et `compliance` contiennent de vrais modeles, pas seulement des vues.
- `manage.py check` passe sans erreur bloquante dans l'environnement local actif.

### 1.2 Limites globales

- Le coeur comptable n'est pas encore suffisamment transactionnel et auditable.
- Le multi-tenant n'est pas securise au niveau API.
- Plusieurs modules annonces comme complets sont en realite partiellement vides ou relies a des donnees simulees.
- La production de KPI financiers melange calcul reel, heuristique et fallback demo.
- La couverture de tests est quasi inexistante hors `ai_engine`.

### 1.3 Verdict de maturite

Niveau estime:

- architecture produit: intermediaire;
- robustesse comptable: faible a intermediaire;
- robustesse ERP transactionnelle: faible;
- maturite IA de demonstration: intermediaire;
- maturite IA de production finance: faible;
- adequation ERP OHADA de production: insuffisante.

[[PAGEBREAK]]

## Partie 2 - Findings critiques

### 2.1 Risque de securite majeur sur le modele utilisateur

Le modele utilisateur transforme tout utilisateur portant le role `admin` en `is_staff=True` et `is_superuser=True`. Or le flux d'inscription cree explicitement le premier utilisateur d'une entreprise avec le role `admin`.

Impact:

- toute nouvelle inscription peut potentiellement obtenir des privileges d'administration globale Django;
- le cloisonnement entre administration metier d'une societe et superadministration technique de la plateforme n'existe pas;
- le risque d'escalade de privilege est critique.

References principales:

- `sakinafinance/accounts/models.py`, methode `save()`;
- `sakinafinance/accounts/views.py`, `register_view()`.

Recommandation:

- separer strictement `role metier` et `privileges systeme`;
- reserver `is_superuser` a une creation manuelle ou a un bootstrap admin dedie;
- introduire un role "company_admin" sans acces superuser Django.

### 2.2 Absence d'isolation multi-tenant dans l'API REST

Les viewsets API exposent des querysets globaux du type `Model.objects.all()` avec seulement `IsAuthenticated`.

Impact:

- un utilisateur authentifie peut potentiellement lister, consulter, modifier ou supprimer des objets d'autres entreprises;
- le produit n'est pas conforme aux attentes minimales d'un SaaS ERP multi-tenant.

Exemples:

- `accounts/api.py`;
- `accounting/api.py`.

Recommandation:

- surcharger `get_queryset()` pour filtrer par `request.user.company`;
- verrouiller `perform_create()` pour imposer `company=request.user.company`;
- ajouter des permissions objet explicites par entreprise et, si necessaire, par entite.

### 2.3 Surface de securite trop permissive

Plusieurs choix de configuration sont incompatibles avec un ERP de production:

- `DEBUG=True` par defaut;
- `SECRET_KEY` de secours hardcodee;
- `ALLOWED_HOSTS` contient `*`;
- creation d'ecriture comptable via endpoint exempt de CSRF.

Impact:

- exposition accrue aux erreurs de configuration;
- risque de deploiement non durci en production;
- fragilite sur les endpoints sensibles.

Recommandation:

- rendre `DEBUG=False` par defaut;
- supprimer toute cle de secours exploitable;
- interdire `*` sur `ALLOWED_HOSTS`;
- retirer `csrf_exempt` des endpoints de saisie comptable web.

### 2.4 Ecart fort entre promesse produit et implementation reelle

Le README et la structure du produit annoncent:

- tresorerie complete;
- reporting complet;
- API REST complete;
- ERP multi-modules.

Mais en pratique:

- `treasury/models.py` est vide;
- `reporting/models.py` est vide;
- plusieurs `api.py` ne sont que des stubs renvoyant un statut de placeholder;
- le module reporting sert des chiffres fixes, non issus du grand livre.

Conclusion:

la promesse fonctionnelle depasse l'etat reel du backend.

[[PAGEBREAK]]

## Partie 3 - Audit du coeur comptable et pertinence OHADA

### 3.1 Ce qu'un ERP comptable OHADA doit garantir

Dans un systeme orientee OHADA et conforme a l'AUDCIF/SYSCOHADA, le backend doit garantir au minimum:

- la tenue reguliere des journaux;
- des ecritures equilibrees et tracables;
- la separation des brouillons, ecritures validees et ecritures annulees;
- la mise a jour fiable du grand livre et des soldes par compte;
- des balances exactes par periode;
- des mecanismes de cloture, de report a nouveau et d'ecritures d'inventaire;
- la production d'etats financiers par mapping normatif, pas par heuristiques visuelles;
- une piste d'audit complete.

### 3.2 Etat reel du moteur comptable

Le module `accounting` contient:

- un plan comptable (`Account`);
- des journaux (`Journal`);
- des ecritures (`Transaction`);
- des lignes (`TransactionLine`);
- des factures;
- des declarations fiscales;
- des immobilisations;
- des objets de consolidation.

C'est une bonne base de schema. En revanche, le comportement metier est incomplet.

#### 3.2.1 Absence de vrai posting

Le modele `Transaction` contient bien:

- `status`;
- `posted_by`;
- `posted_at`;
- `total_debit`;
- `total_credit`.

Mais je n'ai pas trouve:

- de service de validation comptable formel;
- de controle bloquant d'equilibre ligne par ligne avant validation;
- de mise a jour du grand livre lors du passage en `posted`;
- de verrouillage de la modification d'une ecriture postee;
- de mecanisme d'annulation par contrepassation.

Cela signifie que le systeme sait stocker une ecriture, mais pas encore la "poster" comme le ferait un moteur comptable de production.

#### 3.2.2 `current_balance` non fiabilise

Les dashboards et certaines fonctions IA se basent sur `Account.current_balance`.

Probleme:

- le champ existe;
- il est expose en admin et utilise dans les KPI;
- mais aucune logique fiable ne le maintient automatiquement a partir des lignes d'ecritures postees.

Consequence:

- les tableaux de bord peuvent presenter des chiffres incorrects;
- les ratios de structure et de liquidite deviennent peu fiables;
- le contexte SQL fourni a l'IA peut etre faux.

#### 3.2.3 Balance generale: bonne intention, moteur incomplet

L'endpoint de balance generale calcule:

- solde initial debit/credit;
- mouvements debit/credit;
- solde final debit/credit.

La logique est utile, mais elle repose sur:

- des soldes d'ouverture saisis;
- une heuristique sur le sens naturel des comptes;
- l'absence de veritable processus d'ouverture, cloture, report a nouveau et justification de soldes.

Pour une balance OHADA exploitable, il faut ajouter:

- cloture par exercice;
- reports a nouveau;
- ecritures de regularisation et d'inventaire;
- gel de periode;
- justification et lettrage des comptes de tiers.

### 3.3 Etats financiers et ratio comptables

L'endpoint `api_accounting_data()` calcule:

- actifs;
- dettes;
- capitaux propres;
- produits;
- charges;
- "net income";
- ratios de liquidite et solvabilite.

Le probleme n'est pas l'idee, mais la methode.

#### 3.3.1 Total actif et passif

Le code agrège des classes de comptes a partir de `current_balance`.

Limites:

- cela suppose que `current_balance` soit exact, ce qui n'est pas garanti;
- cela ne distingue pas suffisamment les rubriques normatives des etats OHADA;
- la ventilation du bilan renvoyee au front est ensuite construite a partir de pourcentages arbitraires, et non de vraies sous-rubriques.

Exemple:

- immobilisations = `assets_f * 0.6`;
- disponibilites = `assets_f * 0.2`.

Ce n'est pas un bilan comptable. C'est une decomposition visuelle fictive.

#### 3.3.2 Ratio de liquidite

Le code calcule:

- `liquidity_ratio = assets / liabilities`.

Ce n'est pas le ratio de liquidite generale classique.

Pour un pilotage financier pertinent, il faudrait distinguer:

- ratio de liquidite generale = actif circulant / passif circulant;
- ratio de liquidite reduite = (actif circulant - stocks) / passif circulant;
- liquidite immediate = disponibilites / passif court terme.

En l'etat, le nom du KPI est trompeur.

#### 3.3.3 Solvabilite

Le code calcule:

- `solvability_ratio = equity / assets`.

Cette mesure peut servir d'indicateur de structure financiere, mais elle n'est pas documentee ni alignee sur un tableau de bord de solvabilite complet. Il manque au minimum:

- autonomie financiere;
- gearing;
- levier financier;
- couverture des charges financieres;
- FR, BFR, tresorerie nette.

#### 3.3.4 Resultat net et EBITDA

Dans `core/views.py`, le systeme calcule:

- revenu = classe 7;
- depenses = classe 6;
- EBITDA = revenu - depenses;
- net_income = EBITDA.

C'est metierement incorrect.

Le resultat net ne peut pas etre egal a l'EBITDA, sauf cas tres particulier et non documente. Il faut au minimum distinguer:

- EBITDA;
- EBIT ou resultat d'exploitation;
- resultat financier;
- resultat courant;
- impots;
- resultat net.

Pour un ERP OHADA, il faut en plus mapper les comptes aux sous-rubriques du compte de resultat selon le referentiel cible.

[[PAGEBREAK]]

## Partie 4 - Audit de tresorerie et cash management

### 4.1 Calcul de liquidite

Le calcul de liquidite utilise les mouvements des comptes de classe 5:

- somme des debits moins credits des lignes postees.

Ce calcul est acceptable comme approximation d'un solde comptable de tresorerie, sous reserve que:

- toutes les ecritures soient correctement postees;
- les comptes bancaires et caisses soient bien classes;
- les contrepassations et regularisations soient gerees;
- les dates de valeur et rapprochements bancaires soient maitrises.

Aujourd'hui, ces garanties ne sont pas presentes.

### 4.2 DSO

Le code calcule le DSO en prenant:

- les creances 411;
- divisees par un "CA / 30" base sur les comptes de produits.

Limites:

- le DSO devrait idealement etre calcule sur les ventes a credit d'une periode comparable;
- il faut tenir compte des encaissements reels, des avoirs et du lettrage client;
- il faut choisir une base journaliere ou mensuelle claire.

Le DSO actuel est donc un indicateur simplifie, pas un DSO de reference.

### 4.3 DIO, DPO, cycle de cash

Le code retourne:

- `dio_days = 45`;
- `dpo_days = 55`;
- `cash_cycle_days = 40`.

Ces chiffres sont fixes. Ils ne sont pas calcules.

Conclusion:

le module tresorerie ne produit pas encore un cash conversion cycle reel.

### 4.4 Net cashflow 30 jours

Le code calcule:

- `net_cashflow_30d = liquidity * 0.15`.

Ce n'est pas un flux. C'est une projection derivee du solde.

Un vrai calcul devrait utiliser:

- encaissements sur 30 jours;
- decaissements sur 30 jours;
- variation nette de tresorerie sur la periode.

### 4.5 Ce qu'il faut pour une vraie tresorerie ERP

- comptes bancaires dedies en base;
- releves bancaires importes;
- rapprochement bancaire;
- echeanciers clients et fournisseurs;
- previsions basees sur factures, commandes, salaires et taxes;
- distinction entre date comptable et date de valeur;
- previsions multi-scenarios;
- gestion multi-banque et multi-devise.

[[PAGEBREAK]]

## Partie 5 - Audit paie, fiscalite et immobilisations

### 5.1 Paie

Le modele `Payslip.compute()` est problematique a deux niveaux.

#### 5.1.1 Niveau technique

Le code multiplie des `Decimal` par des `float`:

- `self.gross_salary * 0.07`;
- `self.gross_salary * 0.056`.

En Python, cela peut lever une erreur de type. La formule doit rester entierement en `Decimal`.

#### 5.1.2 Niveau metier

Le commentaire parle de "regles OHADA/CFAE/IPRES senegalaises".

Probleme metier:

- l'OHADA n'est pas un moteur de paie;
- la paie doit etre parametree par pays, regime, convention, plafonds, assiettes et baremes;
- les taux et regles doivent etre historises et parametrables, pas codés en dur dans le modele.

Il faut donc:

- un moteur de paie parametrable par pays;
- des baremes et tranches versionnees;
- une distinction entre retenues salariales, charges patronales, avantages imposables, exonérations et plafonds.

### 5.2 Fiscalite

Le module `compliance` sait stocker:

- types de taxe;
- declarations;
- risques;
- exigences reglementaires.

Mais il ne calcule pas encore fiscalement:

- la TVA collectee;
- la TVA deductible;
- les retenues a la source;
- l'impot sur les societes;
- les ecarts entre comptabilite et fiscalite;
- les ecritures de constatation et de paiement.

La "tax provision" actuelle est seulement une somme de declarations brouillon ou en attente.

Pour un ERP complet, il faut un vrai moteur fiscal relie aux ecritures.

### 5.3 Immobilisations

Le module d'immobilisations contient:

- categories;
- actifs;
- lignes d'amortissement.

Ce socle est bon. Mais les regles sont encore simplifiees:

- pas de prorata temporis de mise en service;
- pas de distinction amortissement comptable et fiscal;
- pas de bascule methodologique degressive vers lineaire;
- pas de composant d'actif;
- pas de test de depreciaiton;
- calcul de la methode degressive en `float`.

Pour une gestion OHADA et IFRS robuste, ces points sont indispensables.

[[PAGEBREAK]]

## Partie 6 - Audit achats, stock, projets et reporting

### 6.1 Procurement

Le module achats est assez prometteur:

- fournisseurs;
- RFQ;
- bons de commande;
- receptions;
- stock.

Calculs et limites:

- la formule de ligne d'achat est correcte dans un schema simple HT;
- le total du bon de commande n'est pas automatiquement maintenu apres modification des lignes;
- le stock est ajuste seulement a la creation d'un mouvement;
- il n'y a pas de protection contre le stock negatif;
- il n'y a pas de 3-way match bon de commande / reception / facture;
- il n'y a pas de workflow complet d'approbation budgetaire et delegations.

### 6.2 Projets

Le module projets contient une bonne base:

- budget total;
- budget consomme;
- avancement;
- taches;
- temps;
- jalons.

Limites:

- la rentabilite projet reste superficielle;
- il manque une vraie integration analytique avec les comptes, achats, RH, depenses et facturation;
- il manque le calcul du reste a faire, du cout a terminaison et du ROI reel.

### 6.3 Reporting

Le module `reporting` est aujourd'hui le signal le plus clair de decalage entre promesse et implementation:

- il n'a pas de modeles;
- il sert des chiffres hardcodes;
- il ne depend pas du grand livre;
- il ne produit pas un reporting normatif.

Pour un ERP complet, le reporting doit sortir:

- de la comptabilite postee;
- des modules operationnels;
- d'un moteur de consolidation et d'analytique.

[[PAGEBREAK]]

## Partie 7 - Audit de la couche IA

### 7.1 Ce qui est deja positif

Le module IA contient des briques interessantes:

- analyses IA;
- previsions de tresorerie;
- insights;
- anomalies;
- OCR de documents;
- RAG avec ChromaDB et base documentaire;
- tests unitaires sur une partie du module.

### 7.2 Ce qui limite aujourd'hui la pertinence metier de l'IA

L'IA peut etre impressionnante en demonstration, mais un copilote financier de production exige trois conditions:

- des donnees fiables;
- des regles comptables explicites;
- une gouvernance des calculs.

Aujourd'hui:

- les KPIs comptables utilisent parfois des soldes non fiabilises;
- certains modules utilisent des donnees simulees;
- l'IA de tresorerie tombe facilement sur des approximations;
- le contexte SQL du RAG s'appuie sur `current_balance`, qui n'est pas garanti.

### 7.3 Ce qu'une IA finance de production devrait faire

- proposer des imputations comptables OHADA avec explication;
- assister le rapprochement bancaire;
- detecter les doublons fournisseurs et anomalies de paiement;
- anticiper les tensions de tresorerie a partir des echeances reelles;
- suggerer des ecritures de cloture;
- produire des notes explicatives de variation;
- aider a la preparation des declarations fiscales;
- assister la consolidation, les eliminations intra-groupe et la revue analytique.

### 7.4 Niveau de maturite IA

Niveau actuel:

- couche IA de demonstration: bonne;
- couche IA adossee a un ERP de production fiabilise: encore insuffisante.

[[PAGEBREAK]]

## Partie 8 - Verification runtime et qualite technique

### 8.1 Resultats de verification

Verification effectuee:

- `./finance_env/bin/python manage.py check`: succes;
- execution des tests avec la configuration courante: echec a cause d'une dependance reseau/DNS vers la base distante;
- execution des tests en forcant SQLite local: les tests existent, mais un test HuggingFace reel echoue faute d'acces reseau.

### 8.2 Lecture de ce resultat

Cela signifie:

- la structure Django est chargeable;
- le projet n'est pas en ruine technique;
- mais la suite de tests est trop faible et insuffisamment hermetique;
- le pipeline de qualite ne couvre pas les domaines critiques comptables et ERP.

### 8.3 Couverture de tests

J'ai trouve essentiellement:

- des tests dans `sakinafinance/ai_engine/tests.py`;
- pas de vraie suite de tests pour `accounting`, `treasury`, `hr`, `procurement`, `payments`, `projects` ou `compliance`.

Pour un ERP financier, c'est un deficit majeur.

Il faut des tests sur:

- equilibre des ecritures;
- fermeture de periode;
- calcul de TVA;
- calcul de paie;
- gestion de stock;
- imputations achats;
- rapprochement bancaire;
- amortissements;
- consolidation;
- permissions par entreprise et par role.

[[PAGEBREAK]]

## Partie 9 - Fonctionnalites recommandees pour un ERP complet

### 9.1 Comptabilite generale et auxiliaire

- workflow complet de validation comptable;
- plan comptable SYSCOHADA parametre par pays et type d'entreprise;
- lettrage client et fournisseur;
- rapprochement bancaire;
- gestion des journaux auxiliaires;
- cloture, report a nouveau, extournes, ecritures d'inventaire;
- grand livre, balance, balance agee, journaux, FEC equivalent interne;
- gestion des pieces justificatives liees aux ecritures.

### 9.2 Order-to-Cash

- tiers clients avec limites et conditions;
- devis;
- bons de livraison;
- facturation;
- avoirs;
- echeanciers;
- relances;
- suivi des impayes;
- provisions pour creances douteuses;
- encaissements multi-modes.

### 9.3 Procure-to-Pay

- demandes d'achat;
- circuits d'approbation;
- contrats fournisseurs;
- bons de commande;
- receptions;
- factures fournisseurs;
- 3-way match;
- litiges et avoirs;
- paiement fournisseur;
- rapprochement avec comptabilite.

### 9.4 Tresorerie

- comptes bancaires reels;
- import de releves;
- rapprochement automatique assiste par IA;
- previsions 13 semaines et 12 mois;
- cash pooling;
- gestion des prets et echelons de remboursement;
- gestion des placements;
- suivi des dates de valeur.

### 9.5 Fiscalite

- moteur TVA;
- moteur retenues a la source;
- moteur IS;
- calendrier fiscal;
- generation d'ecritures fiscales;
- dossiers de preuves et piste d'audit;
- parametres fiscaux par pays et par date d'effet.

### 9.6 RH et paie

- baremes versionnes;
- assiettes de cotisation;
- plafonds;
- multi-pays;
- paie mensuelle, quinzaine, prorata;
- absences, conges, avances, primes, variables;
- integration comptable de la paie;
- coffre documentaire social.

### 9.7 Analytique et controle de gestion

- axes analytiques;
- centres de cout;
- sections;
- budgets;
- forecast;
- rolling forecast;
- ecarts budget/reel;
- rentabilite par produit, projet, entite, client, canal.

### 9.8 Immobilisations

- composants;
- mise en service;
- cession;
- mise au rebut;
- amortissement comptable et fiscal;
- tableau d'amortissement;
- integration comptable automatique.

### 9.9 Consolidation groupe

- pourcentages de detention;
- methodes de consolidation;
- conversion de devise;
- elimination intra-groupe;
- interets minoritaires;
- package de consolidation;
- piste d'audit des retraitements.

### 9.10 IA finance de production

- OCR avec validation humaine;
- imputation comptable assistee;
- detection d'anomalies de paiements;
- prevision de cash par echeances;
- copilote de cloture mensuelle;
- assistant de justification d'ecarts;
- support a la consolidation;
- generation de notes de synthese CFO.

[[PAGEBREAK]]

## Partie 10 - Roadmap recommandee

### 10.1 Priorite immediate - 48 heures

- corriger l'escalade de privilege utilisateur;
- filtrer toutes les API par entreprise;
- retirer les endpoints sensibles exemptes de CSRF;
- geler les donnees demo melangees aux chiffres reels;
- corriger les routes et templates cassants;
- documenter clairement les modules encore en stub.

### 10.2 Stabilisation - 2 semaines

- creer un vrai service de posting comptable;
- mettre a jour les soldes de comptes a partir des lignes postees;
- verrouiller les ecritures postees;
- mettre en place des tests sur ecritures, TVA, paie, stock et permissions;
- remplacer les KPI fictifs par des calculs reels ou les masquer.

### 10.3 Construction ERP - 6 a 8 semaines

- finaliser O2C et P2P;
- creer les modeles tresorerie manquants;
- relier achats, factures, paiement et comptabilite;
- construire une balance agee client/fournisseur;
- mettre en place les parametres fiscaux et sociaux versionnes;
- lancer une vraie comptabilite analytique.

### 10.4 Cible moyen terme - 3 mois et plus

- etats financiers OHADA fiables;
- moteur de cloture;
- consolidation groupe;
- IA de production finance;
- gouvernance des donnees, logs, traceabilite, supervision, audit trail complet.

[[PAGEBREAK]]

## Partie 11 - References normatives et metier

### 11.1 OHADA / AUDCIF

Le referentiel comptable central pour une implementation orientee OHADA est l'AUDCIF et le SYSCOHADA revise. Les etats financiers, les comptes consolides ou combines, les principes de tenue comptable et les presentations doivent etre derives de ce cadre, et non de simples regroupements visuels de classes comptables.

Reference officielle:

- https://www.ohada.org/acte-uniforme-relatif-au-droit-comptable-et-a-linformation-financiere-audcif/

### 11.2 Travail et paie

J'en deduis qu'il ne faut pas modeller la paie comme un "moteur OHADA generic". L'OHADA harmonise le droit des affaires et a engage des travaux d'harmonisation sur le droit du travail, mais la paie reste concretement parametrable par pays, regime social, convention et baremes nationaux.

Reference generale:

- https://www.ohada.org/en/harmonization-of-labor-law/

[[PAGEBREAK]]

## Conclusion generale

SakinaFinance dispose deja d'une ossature produit ambitieuse et d'un socle de donnees qui peut evoluer vers un veritable ERP financier oriente OHADA et augmente par l'IA. Le projet est suffisamment avance pour justifier un investissement de stabilisation, mais pas encore suffisamment fiable pour etre qualifie aujourd'hui d'ERP integral et complet au sens finance, comptabilite, auditabilite et exploitation de production.

Le principal enjeu n'est pas d'ajouter encore des dashboards. Le principal enjeu est de solidifier le coeur transactionnel:

- poster proprement les ecritures;
- fiabiliser les soldes;
- fermer les periodes;
- relier les cycles metiers a la comptabilite;
- construire les etats sur des regles normatives;
- brancher l'IA sur une base de verite fiable.

Une fois ce socle pose, la plateforme pourra devenir un veritable ERP financier moderne:

- conforme;
- exploitable;
- multi-entites;
- pilotable;
- et reellement intelligent.

### Annexes techniques - references de fichiers examines

- `sakinafinance/settings.py`
- `sakinafinance/urls.py`
- `sakinafinance/core/api_urls.py`
- `sakinafinance/accounts/models.py`
- `sakinafinance/accounts/views.py`
- `sakinafinance/accounts/api.py`
- `sakinafinance/accounting/models.py`
- `sakinafinance/accounting/views.py`
- `sakinafinance/accounting/api.py`
- `sakinafinance/treasury/views.py`
- `sakinafinance/treasury/api.py`
- `sakinafinance/reporting/views.py`
- `sakinafinance/hr/models.py`
- `sakinafinance/hr/views.py`
- `sakinafinance/procurement/models.py`
- `sakinafinance/procurement/views.py`
- `sakinafinance/projects/models.py`
- `sakinafinance/projects/views.py`
- `sakinafinance/compliance/models.py`
- `sakinafinance/compliance/views.py`
- `sakinafinance/ai_engine/models.py`
- `sakinafinance/ai_engine/views.py`
- `sakinafinance/ai_engine/services.py`
- `sakinafinance/ai_engine/services_rag.py`
- `sakinafinance/payments/models.py`
- `sakinafinance/payments/views.py`

