# -*- coding: utf-8 -*-
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_report():
    pdf_path = "/home/cardan/Documents/sakinafinance/reports/rapport_onglets_fiscalite_reglementaire.pdf"
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    
    # Create Document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#065f46'), # Dark green theme
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'),
        spaceAfter=25
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#064e3b'),
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155'),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'Code',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#0f172a'),
        backColor=colors.HexColor('#f8fafc'),
        borderColor=colors.HexColor('#e2e8f0'),
        borderWidth=0.5,
        borderPadding=5,
        spaceAfter=10
    )
    
    story = []
    
    # Title Page / Header
    story.append(Paragraph("Rapport d'Audit Technique : Onglets Fiscalité & Réglementaire", title_style))
    story.append(Paragraph("Analyse approfondie du code source Frontend (HTML/JS) et Backend (Python/Django) de la plateforme SakinaFinance", subtitle_style))
    story.append(Spacer(1, 10))
    
    # 1. Introduction
    story.append(Paragraph("1. Introduction & Périmètre de l'analyse", h1_style))
    story.append(Paragraph("Ce rapport détaille le fonctionnement, la structure et l'intégration des fonctionnalités associées aux onglets <b>Fiscalité</b> et <b>Réglementaire</b> au sein de SakinaFinance. L'analyse couvre la partie Frontend (gérée par le template HTML de l'application et les scripts JavaScript associés) et la partie Backend (gérée par les modèles Django, les vues de traitement et les contrôleurs d'API).", body_style))
    story.append(Spacer(1, 10))
    
    # 2. Onglet Fiscalité
    story.append(Paragraph("2. Onglet : Fiscalité (Calendrier & Dépôts)", h1_style))
    story.append(Paragraph("Cet onglet permet à l'utilisateur de suivre ses provisions d'impôts, de visualiser ses prochaines échéances de déclaration et de consulter l'historique des déclarations fiscales validées pour ses différentes entités.", body_style))
    
    story.append(Paragraph("A. Structure Frontend (templates/compliance/index.html)", h2_style))
    story.append(Paragraph("• <b>KPIs (Indicateurs clés) :</b> Quatre cartes affichent dynamiquement la provision fiscale totale, le nombre de déclarations en attente, le nombre de jours restants avant la prochaine échéance et un taux de ponctualité statique fixé à 98%.", bullet_style))
    story.append(Paragraph("• <b>Tableau du Calendrier Fiscal & Social :</b> Affiche les échéances triées par date. Il contient des badges de couleur dynamique (rouge si l'échéance est urgente, c'est-à-dire dans moins de 7 jours).", bullet_style))
    story.append(Paragraph("• <b>Tableau des Derniers Dépôts Validés :</b> Historique des impôts payés ou déclarés.", bullet_style))
    story.append(Paragraph("• <b>Panneau Latéral des Entités :</b> Affiche les entités enregistrées avec leur identifiant fiscal (NIF/TIN) et leur numéro de TVA.", bullet_style))
    
    story.append(Paragraph("B. Structure Backend (sakinafinance/compliance/)", h2_style))
    story.append(Paragraph("• <b>Modèle TaxType :</b> Gère le type de taxe (TVA, IS, etc.) avec son code, sa fréquence (mensuelle, trimestrielle, annuelle ou occasionnelle) et est lié à l'entreprise.", bullet_style))
    story.append(Paragraph("• <b>Modèle TaxFiling :</b> Représente une déclaration fiscale spécifique. Il gère la période, la date limite de dépôt (<i>deadline</i>), les montants (base imposable et taxe), le statut de la déclaration (brouillon, à soumettre, déposée, payée, annulée) et permet d'associer un document justificatif (FileField).", bullet_style))
    story.append(Paragraph("• <b>Formulaire TaxFilingForm (forms.py) :</b> Permet l'enregistrement d'une déclaration en filtrant les entités et types de taxes pour n'afficher que ceux liés à la structure de l'utilisateur.", bullet_style))
    
    story.append(Spacer(1, 10))
    
    # Page break for better layout
    story.append(PageBreak())
    
    # 3. Onglet Réglementaire
    story.append(Paragraph("3. Onglet : Réglementaire & Audit", h1_style))
    story.append(Paragraph("Cet onglet est dédié à la conformité institutionnelle, aux audits et à la gestion des risques opérationnels ou réglementaires.", body_style))
    
    story.append(Paragraph("A. Structure Frontend (templates/compliance/index.html)", h2_style))
    story.append(Paragraph("• <b>Obligations Réglementaires Activées :</b> Affiche des cartes détaillant les obligations (nom, autorité, description, fréquence). En l'absence de données dynamiques, le script charge deux exemples par défaut : la <i>Déclaration Fiscale Annuelle</i> (DGI) et l'<i>Audit Interne de Conformité</i>.", bullet_style))
    story.append(Paragraph("• <b>Panneau Latéral d'Analyse des Risques :</b> Liste les risques non résolus sous forme d'éléments visuels. Une bordure colorée indique la gravité (rouge pour élevé/critique, jaune pour moyen, vert pour faible).", bullet_style))
    story.append(Paragraph("• <b>Bouton d'action :</b> Un bouton 'Lancer Auto-Audit IA' est disponible pour exécuter un audit automatique.", bullet_style))
    
    story.append(Paragraph("B. Structure Backend (sakinafinance/compliance/)", h2_style))
    story.append(Paragraph("• <b>Modèle RegulatoryRequirement :</b> Représente une obligation réglementaire (ex: CNSS, IPRES, DPAE). Il comprend l'autorité émettrice, la description, la fréquence et un état d'activation (booléen).", bullet_style))
    story.append(Paragraph("• <b>Modèle ComplianceRisk :</b> Gère les risques identifiés. Il stocke le titre, la description, l'impact financier estimé, la probabilité (faible, moyenne, élevée), la gravité (faible, moyenne, élevée, critique), le statut de résolution (booléen) et le plan de remédiation associé.", bullet_style))
    story.append(Paragraph("• <b>Formulaire ComplianceRiskForm (forms.py) :</b> Permet de déclarer et qualifier un risque dans le système.", bullet_style))
    
    # 4. Flux de données
    story.append(Paragraph("4. Flux de Données & Intégration API (views.py)", h1_style))
    story.append(Paragraph("Le frontend et le backend communiquent via un appel AJAX vers le point d'accès d'API <b>api_compliance_data</b> (URL : <code>/compliance/api/data/</code>) lié à la vue correspondante :", body_style))
    
    api_code_snippet = """@login_required
def api_compliance_data(request):
    company = request.user.company
    ...
    # Récupération des données réelles
    filings = TaxFiling.objects.filter(company=company)
    risks = ComplianceRisk.objects.filter(company=company, is_resolved=False)
    entities = Entity.objects.filter(company=company)
    ...
    # Calcul du score de conformité globale
    compliance_score = 100 - (open_risks_count * 10)
    ..."""
    story.append(Paragraph(api_code_snippet.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    
    story.append(Paragraph("L'API retourne un objet JSON structuré contenant le score de conformité global, le montant total provisionné, le calendrier des 5 prochaines échéances de dépôt, l'historique des 5 derniers dépôts validés, la liste des risques ouverts et les détails sur les entités configurées. Le script JS du frontend intercepte cette réponse pour mettre à jour dynamiquement le DOM de la page.", body_style))
    
    story.append(Spacer(1, 10))
    story.append(Paragraph("5. Synthèse des Éléments Identifiés", h1_style))
    
    # Table of elements
    table_data = [
        [Paragraph("<b>Élément</b>", body_style), Paragraph("<b>Onglet Fiscalité</b>", body_style), Paragraph("<b>Onglet Réglementaire</b>", body_style)],
        [Paragraph("<b>Modèles Django associés</b>", body_style), Paragraph("TaxType, TaxFiling", body_style), Paragraph("RegulatoryRequirement, ComplianceRisk", body_style)],
        [Paragraph("<b>Formulaires de saisie</b>", body_style), Paragraph("TaxFilingForm (Déclarer un impôt)", body_style), Paragraph("ComplianceRiskForm (Signaler un risque)", body_style)],
        [Paragraph("<b>Indicateurs / KPI</b>", body_style), Paragraph("Provision impôts, déclaration en attente, jours avant échéance, taux ponctualité", body_style), Paragraph("Score global de conformité (calculé à partir des risques)", body_style)],
        [Paragraph("<b>Éléments Dynamiques</b>", body_style), Paragraph("Calendrier fiscal, historique des dépôts, liste des entités", body_style), Paragraph("Liste des obligations réglementaires actives, risques ouverts", body_style)]
    ]
    
    t = Table(table_data, colWidths=[120, 200, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    
    story.append(t)
    
    # Build PDF
    doc.build(story)
    print("Report PDF generated successfully.")

if __name__ == "__main__":
    create_report()
