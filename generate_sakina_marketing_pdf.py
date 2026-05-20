from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "SakinaFinance_IA_Document_Marketing_Complet.pdf"
LOGO = ROOT / "static/img/logo_sakinafinance.jpeg"
AI_BG = ROOT / "static/img/ai_advisor_bg.png"
FINANCE_BG = ROOT / "static/img/finance_bg.png"

PAGE_W, PAGE_H = A4

BLUE = colors.HexColor("#1358D8")
NAVY = colors.HexColor("#0B1730")
NAVY_2 = colors.HexColor("#10213F")
CYAN = colors.HexColor("#07A7B8")
GREEN = colors.HexColor("#0B8F63")
GOLD = colors.HexColor("#C98216")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#5B6472")
LIGHT = colors.HexColor("#F5F8FC")
LINE = colors.HexColor("#E4EAF2")
SOFT_BLUE = colors.HexColor("#EAF3FF")
SOFT_GOLD = colors.HexColor("#FFF6E4")
SOFT_GREEN = colors.HexColor("#EAF8F1")


def register_fonts():
    fonts = {
        "SF": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "SF-Bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "SF-Italic": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
    }
    for name, path in fonts.items():
        if Path(path).exists():
            pdfmetrics.registerFont(TTFont(name, path))


register_fonts()


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        "CoverKicker",
        fontName="SF-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#DBEAFE"),
        alignment=TA_LEFT,
        uppercase=True,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        "CoverTitle",
        fontName="SF-Bold",
        fontSize=38,
        leading=42,
        textColor=colors.white,
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        "CoverSubtitle",
        fontName="SF",
        fontSize=12.5,
        leading=18,
        textColor=colors.HexColor("#D7E4FF"),
        spaceAfter=14,
    )
)
styles.add(
    ParagraphStyle(
        "H1",
        fontName="SF-Bold",
        fontSize=22,
        leading=28,
        textColor=NAVY,
        spaceBefore=8,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        "H2",
        fontName="SF-Bold",
        fontSize=15,
        leading=20,
        textColor=BLUE,
        spaceBefore=8,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        "Body",
        fontName="SF",
        fontSize=9.3,
        leading=14,
        textColor=INK,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        "BodyMuted",
        fontName="SF",
        fontSize=8.7,
        leading=13,
        textColor=MUTED,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        "Small",
        fontName="SF",
        fontSize=7.4,
        leading=10,
        textColor=MUTED,
    )
)
styles.add(
    ParagraphStyle(
        "Quote",
        fontName="SF-Bold",
        fontSize=13,
        leading=18,
        textColor=NAVY,
        spaceAfter=0,
    )
)
styles.add(
    ParagraphStyle(
        "TableHead",
        fontName="SF-Bold",
        fontSize=7.2,
        leading=9,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
)
styles.add(
    ParagraphStyle(
        "TableCell",
        fontName="SF",
        fontSize=7.2,
        leading=9.5,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        "TableCellBold",
        fontName="SF-Bold",
        fontSize=7.2,
        leading=9.5,
        textColor=NAVY,
    )
)
styles.add(
    ParagraphStyle(
        "Center",
        fontName="SF",
        fontSize=9,
        leading=13,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
)


class CoverPage(Flowable):
    def __init__(self):
        super().__init__()
        self.width = PAGE_W
        self.height = PAGE_H

    def wrap(self, availWidth, availHeight):
        return availWidth, availHeight

    def draw(self):
        c = self.canv
        c.saveState()
        c.translate(-2 * cm, -2 * cm)
        c.setFillColor(NAVY)
        c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#143F8F"))
        c.circle(PAGE_W + 20, PAGE_H - 130, 230, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#0A8A9B"))
        c.circle(PAGE_W - 100, 60, 180, fill=1, stroke=0)
        c.setFillColor(colors.Color(1, 1, 1, alpha=0.08))
        c.circle(PAGE_W - 80, PAGE_H - 110, 115, fill=1, stroke=0)

        if AI_BG.exists():
            c.saveState()
            c.setFillAlpha(0.24)
            c.drawImage(str(AI_BG), PAGE_W - 260, 150, width=210, height=210, mask="auto")
            c.restoreState()

        if LOGO.exists():
            c.drawImage(str(LOGO), 2 * cm, PAGE_H - 3.8 * cm, width=16 * mm, height=16 * mm, mask="auto")

        c.setFillColor(colors.white)
        c.setFont("SF-Bold", 12)
        c.drawString(4.0 * cm, PAGE_H - 3.2 * cm, "SakinaFinance IA")

        badge_x, badge_y = 2 * cm, PAGE_H - 5.4 * cm
        c.setFillColor(colors.Color(1, 1, 1, alpha=0.12))
        c.roundRect(badge_x, badge_y, 88 * mm, 9 * mm, 4.5 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#DBEAFE"))
        c.setFont("SF-Bold", 7.8)
        c.drawString(badge_x + 4 * mm, badge_y + 3 * mm, "ERP FINANCIER IA POUR L'ESPACE OHADA")

        c.setFillColor(colors.white)
        c.setFont("SF-Bold", 35)
        c.drawString(2 * cm, PAGE_H - 7.3 * cm, "Document marketing")
        c.drawString(2 * cm, PAGE_H - 8.7 * cm, "SaaS & vente")
        c.setFont("SF-Bold", 30)
        c.setFillColor(colors.HexColor("#91E5F0"))
        c.drawString(2 * cm, PAGE_H - 10.0 * cm, "SakinaFinance IA")

        text = (
            "Positionnement, proposition de valeur, analyse fonctionnelle, "
            "messages commerciaux, strategie d'acquisition, pricing et roadmap "
            "go-to-market pour vendre SakinaFinance IA aux PME, ETI, groupes et cabinets comptables."
        )
        p = Paragraph(text, styles["CoverSubtitle"])
        w, h = p.wrap(127 * mm, 50 * mm)
        p.drawOn(c, 2 * cm, PAGE_H - 12.8 * cm)

        card_y = 4.0 * cm
        cards = [
            ("OHADA natif", "Comptabilite, etats financiers et logique SYSCOHADA des le premier usage."),
            ("IA Advisor", "Questions en langage naturel, analyse du cash, marges, risques et documents."),
            ("Go-to-market", "Cabinets comptables, LinkedIn B2B, demos terrain et offres de penetration."),
        ]
        x = 2 * cm
        for title, body in cards:
            c.setFillColor(colors.Color(1, 1, 1, alpha=0.12))
            c.roundRect(x, card_y, 51 * mm, 34 * mm, 5 * mm, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("SF-Bold", 8.5)
            c.drawString(x + 5 * mm, card_y + 23 * mm, title)
            p = Paragraph(body, ParagraphStyle("covercard", parent=styles["Small"], textColor=colors.HexColor("#DDEBFF"), leading=9))
            p.wrapOn(c, 41 * mm, 20 * mm)
            p.drawOn(c, x + 5 * mm, card_y + 8 * mm)
            x += 56 * mm

        c.setFillColor(colors.HexColor("#A9C4F6"))
        c.setFont("SF", 7.5)
        c.drawString(2 * cm, 2 * cm, "Version complete - document de travail commercial")
        c.restoreState()


class SectionBand(Flowable):
    def __init__(self, title, subtitle=None, color=BLUE):
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.color = color
        self.height = 28 * mm if subtitle else 20 * mm

    def wrap(self, availWidth, availHeight):
        return availWidth, self.height

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(LIGHT)
        c.roundRect(0, 0, self.width, self.height, 6 * mm, fill=1, stroke=0)
        c.setFillColor(self.color)
        c.roundRect(0, 0, 8 * mm, self.height, 4 * mm, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont("SF-Bold", 15)
        c.drawString(13 * mm, self.height - 10 * mm, self.title)
        if self.subtitle:
            c.setFillColor(MUTED)
            c.setFont("SF", 8)
            c.drawString(13 * mm, self.height - 18 * mm, self.subtitle)
        c.restoreState()


def p(text, style="Body"):
    return Paragraph(text, styles[style])


def section(title, subtitle=None, color=BLUE):
    return [Spacer(1, 6), SectionBand(title, subtitle, color), Spacer(1, 9)]


def bullet(items, level=0):
    return ListFlowable(
        [ListItem(p(item, "BodyMuted"), leftIndent=0) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=14 + level * 8,
        bulletFontName="SF-Bold",
        bulletFontSize=5.5,
        bulletColor=BLUE,
        spaceBefore=1,
        spaceAfter=7,
    )


def callout(text, bg=SOFT_BLUE, border=BLUE):
    t = Table([[p(text, "Quote")]], colWidths=[16.8 * cm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg),
                ("BOX", (0, 0), (-1, -1), 0.8, border),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return t


def card(title, text, color=BLUE):
    return Table(
        [[p(title, "TableCellBold")], [p(text, "TableCell")]],
        colWidths=[7.9 * cm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("LINEABOVE", (0, 0), (-1, 0), 3, color),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        ),
    )


def two_col_cards(items):
    rows = []
    for i in range(0, len(items), 2):
        left = card(*items[i])
        right = card(*items[i + 1]) if i + 1 < len(items) else ""
        rows.append([left, right])
    t = Table(rows, colWidths=[8.15 * cm, 8.15 * cm], hAlign="LEFT")
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
    return t


def styled_table(headers, rows, widths=None):
    data = [[p(h, "TableHead") for h in headers]]
    for row in rows:
        data.append([p(str(cell), "TableCell") for cell in row])
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY_2),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return t


def header_footer(canvas, doc):
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setFillColor(colors.white)
    canvas.rect(0, PAGE_H - 18 * mm, PAGE_W, 18 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.line(2 * cm, PAGE_H - 18 * mm, PAGE_W - 2 * cm, PAGE_H - 18 * mm)
    if LOGO.exists():
        canvas.drawImage(str(LOGO), 2 * cm, PAGE_H - 14.2 * mm, width=8 * mm, height=8 * mm, mask="auto")
    canvas.setFillColor(NAVY)
    canvas.setFont("SF-Bold", 8)
    canvas.drawString(3.1 * cm, PAGE_H - 12 * mm, "SakinaFinance IA")
    canvas.setFillColor(MUTED)
    canvas.setFont("SF", 7)
    canvas.drawRightString(PAGE_W - 2 * cm, PAGE_H - 12 * mm, "Document marketing SaaS & go-to-market")
    canvas.setStrokeColor(LINE)
    canvas.line(2 * cm, 16 * mm, PAGE_W - 2 * cm, 16 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("SF", 7)
    canvas.drawString(2 * cm, 9 * mm, "Confidentiel - support commercial et strategie")
    canvas.drawRightString(PAGE_W - 2 * cm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_story():
    story = [CoverPage(), PageBreak()]

    story += section("Resume Executif", "Le positionnement clair pour vendre SakinaFinance IA", BLUE)
    story.append(callout("SakinaFinance IA transforme la comptabilite d'une obligation subie en systeme de pilotage financier quotidien. La promesse commerciale : donner aux entreprises africaines la visibilite, la rigueur et l'intelligence financiere d'un grand groupe, sans la lourdeur d'un ERP traditionnel."))
    story.append(Spacer(1, 10))
    story.append(p("Le marche OHADA et Afrique francophone est marque par une realite tres concrete : les dirigeants travaillent encore avec Excel, Sage, des fichiers disperses, des releves bancaires, du cash, du Mobile Money et des pieces comptables transmises en retard. SakinaFinance IA repond a ce contexte en reunissant comptabilite, tresorerie, facturation, paie, achats, conformite, reporting, consolidation et IA Advisor dans une plateforme cloud.", "Body"))
    story.append(p("Le message ne doit pas etre seulement technique. Il doit parler de cash, de controle, de serenite fiscale, de gain de temps et de decision. La valeur n'est pas 'un logiciel de plus', mais un copilote financier qui aide chaque dirigeant, DAF et expert-comptable a agir plus tot.", "Body"))
    story.append(bullet([
        "<b>Cible prioritaire :</b> PME structurees, ETI, groupes multi-entites et cabinets comptables.",
        "<b>Angle fort :</b> OHADA natif + experience SaaS moderne + IA appliquee aux donnees reelles.",
        "<b>Canal prioritaire :</b> cabinets d'expertise comptable comme multiplicateurs d'acquisition.",
        "<b>Moment de vente :</b> dashboard rempli, facture en retard identifiee, question IA posee, prevision cash affichee.",
    ]))

    story += section("Promesse Et Positionnement", "Le coeur du discours marketing", CYAN)
    story.append(callout("Ne subissez plus votre comptabilite. Pilotez-la. L'ERP financier 100% OHADA propulse par l'IA.", SOFT_GOLD, GOLD))
    story.append(Spacer(1, 10))
    story.append(two_col_cards([
        ("Pour le CEO / DG", "Votre DAF virtuel dans votre poche : cash disponible, factures en retard, marge, runway et risques en langage simple.", BLUE),
        ("Pour le DAF / CFO", "Une base financiere unifiee pour accelerer les reportings, fiabiliser les analyses et anticiper les tensions de tresorerie.", CYAN),
        ("Pour le comptable", "Moins de ressaisie, plus de controle : journaux, ecritures, factures, etats financiers et logique OHADA structuree.", GREEN),
        ("Pour le cabinet", "Un portail client qui transforme des pieces eparses en donnees comptables exploitables et en mission de conseil.", GOLD),
    ]))
    story.append(p("Positionnement recommande : <b>SakinaFinance IA est l'ERP financier intelligent concu pour les entreprises de l'espace OHADA.</b> Il ne copie pas les SaaS occidentaux : il part des realites locales, du SYSCOHADA, de la tresorerie fragile, de la fiscalite, du multi-entites et de la relation cabinet-client.", "Body"))

    story += section("Analyse Complete Des Fonctionnalites", "Ce que le produit permet de vendre concretement", BLUE)
    modules = [
        ("Dashboard financier", "KPIs par periode, chiffre d'affaires, charges, resultat, EBITDA, marge, tresorerie nette, factures en attente, factures en retard, alertes et transactions recentes.", BLUE),
        ("Comptabilite OHADA/SYSCOHADA", "Plan comptable, journaux, ecritures debit/credit, factures clients/fournisseurs, TVA, etats financiers, fiscalite, immobilisations et amortissements.", GREEN),
        ("Tresorerie et rapprochement", "Comptes bancaires, releves importes, lignes de releve, rapprochement bancaire, comparaison solde comptable et solde bancaire.", CYAN),
        ("IA Advisor", "Chat IA, previsions de tresorerie, analyse EBITDA, burn rate, runway, risques, anomalies, RAG documentaire, OCR et reponses sourcees.", GOLD),
        ("Achats, fournisseurs et stocks", "Fournisseurs, RFQ, bons de commande, approbations, receptions, articles en stock, mouvements et controle de stock insuffisant.", BLUE),
        ("RH et paie", "Employes, departements, postes, conges, periodes de paie, bulletins, CNSS, IPRES, IRPP et recrutements.", GREEN),
        ("Conformite fiscale", "Types d'impots, declarations, echeances, justificatifs, obligations reglementaires, risques et plans de mitigation.", GOLD),
        ("Projets et budgets", "Budgets projet, jalons, taches, temps passe, couts, ecarts, sante projet et finance par initiative.", CYAN),
        ("Consolidation et groupe", "Societes parentes, filiales, entites multi-pays, devises locales, executive view, KPIs consolides et vision direction.", BLUE),
        ("SaaS et abonnements", "Plans Startup, PME, Enterprise, Groupe, facturation, paiement, historique, cycles mensuels/annuels et gestion d'abonnement.", GREEN),
    ]
    story.append(two_col_cards(modules))
    story.append(callout("Point strategique : le Mobile Money est un argument tres fort pour le marche ouest-africain. Il faut le porter comme vision commerciale, tout en alignant la roadmap produit si les connecteurs Wave, Orange Money, MTN ou autres ne sont pas encore disponibles en production.", SOFT_GOLD, GOLD))

    story += section("Positionnement Concurrentiel", "Comment attaquer les alternatives deja installees", NAVY)
    story.append(styled_table(
        ["Concurrent", "Faiblesse observee", "Angle d'attaque SakinaFinance IA"],
        [
            ["Sage / Saari", "Cher, lourd, interface datee, peu d'IA, logique souvent installee localement.", "Gardez la rigueur comptable. Supprimez la lourdeur."],
            ["Odoo", "Puissant mais complexe, souvent dependant d'un integrateur pour parametrer le SYSCOHADA.", "Natif OHADA, plus rapide a deployer pour la finance."],
            ["QuickBooks / Xero / Zoho", "Bonne UX mais decalage avec les contraintes OHADA et les experts-comptables locaux.", "La simplicite SaaS internationale avec le moteur legal local."],
            ["Solutions locales", "Conformes mais souvent vieillissantes, peu connectees et rarement IA-first.", "Conformite locale avec technologie de nouvelle generation."],
            ["Excel", "Flexible mais fragile : erreurs, versions multiples, absence d'audit et consolidation manuelle.", "Remplacer les fichiers disperses par un systeme financier fiable."],
        ],
        [3.0 * cm, 6.2 * cm, 7.4 * cm],
    ))

    story += section("Cibles Et Messages De Vente", "Adapter le discours au persona", CYAN)
    story.append(styled_table(
        ["Persona", "Douleurs principales", "Promesse commerciale"],
        [
            ["Dirigeant PME", "Pas de visibilite cash, bilan trop tardif, peur fiscale, dependance a Excel.", "Voir la sante financiere aujourd'hui : cash, marge, impayes, dettes et risques."],
            ["DAF / CFO", "Reporting manuel, donnees dispersees, consolidation lente, pression de la direction.", "Produire plus vite, fiabiliser les donnees et anticiper les besoins de tresorerie."],
            ["Expert-comptable", "Clients desorganises, pieces en retard, ressaisie, faible temps de conseil.", "Transformer le cabinet en partenaire financier augmente avec des donnees propres."],
            ["Groupe / Holding", "Filiales heterogenes, multi-devises, consolidation Excel, manque de vision groupe.", "Suivre les entites localement et piloter la performance consolidee."],
        ],
        [3.4 * cm, 6.0 * cm, 7.2 * cm],
    ))
    story.append(Spacer(1, 10))
    story.append(callout("Pitch court : SakinaFinance IA est l'ERP financier intelligent concu pour l'Afrique francophone. Il centralise comptabilite OHADA, tresorerie, facturation, paie, achats, conformite et reporting, avec un IA Advisor capable d'analyser vos chiffres et vos documents en langage naturel.", SOFT_BLUE, BLUE))

    story += section("Offres Et Tarification Recommandees", "Strategie de penetration adaptee au pouvoir d'achat local", GREEN)
    story.append(styled_table(
        ["Offre", "Cible", "Prix recommande", "Argument de vente"],
        [
            ["Startup / TPE", "Freelances, boutiques, startups", "15 000 FCFA / mois", "Le prix d'un abonnement internet pour tuer Excel."],
            ["PME", "10 a 50 employes", "49 000 FCFA / mois", "Moins cher qu'un stagiaire comptable."],
            ["Enterprise", "+50 employes, multi-sites", "149 000 FCFA / mois", "Remplace la lourdeur Sage et accelere le reporting."],
            ["Groupe", "Holdings, filiales, multi-pays", "Sur devis des 399 000 FCFA", "Rentabilise des la premiere cloture consolidee."],
        ],
        [3.2 * cm, 4.4 * cm, 3.8 * cm, 5.2 * cm],
    ))
    story.append(Spacer(1, 9))
    story.append(bullet([
        "Proposer le paiement annuel avec deux mois offerts.",
        "Accepter Mobile Money et virement bancaire, en plus du paiement carte si disponible.",
        "Creer une offre cabinet comptable avec espaces clients inclus.",
        "Ajouter un pack migration depuis Excel ou Sage.",
        "Inclure une session d'onboarding pour les plans PME, Enterprise et Groupe.",
    ]))
    story.append(callout("Point d'alignement : la page pricing actuelle du produit peut afficher des prix superieurs. Pour accelerer l'adoption, choisir clairement entre strategie premium et strategie de penetration. Pour l'Afrique francophone, la penetration est plus coherente au demarrage.", SOFT_GOLD, GOLD))

    story += section("Strategie D'Acquisition", "Comment generer les premiers clients", BLUE)
    story.append(two_col_cards([
        ("1. Cabinets comptables", "C'est le canal le plus puissant. Un cabinet convaincu peut onboarder plusieurs dizaines de PME. Offre : abonnement cabinet, espaces clients, formation, commission partenaire.", BLUE),
        ("2. LinkedIn B2B", "Cibler CEO, DG, DAF, CFO, responsables comptables et experts-comptables a Dakar, Abidjan, Douala, Cotonou, Bamako, Lome et Libreville.", CYAN),
        ("3. Webinaires terrain", "Themes : controle fiscal, tresorerie sur 6 mois, Excel vs ERP, remplacement Sage, cloture SYSCOHADA, cabinet comptable augmente.", GOLD),
        ("4. Partenariats", "Banques, fintechs, incubateurs, ordres professionnels, reseaux d'entrepreneurs et structures d'accompagnement PME.", GREEN),
    ]))
    story.append(p("<b>Sequence de demonstration ideale en 15 minutes :</b>", "H2"))
    story.append(bullet([
        "ouvrir le dashboard dirigeant : cash, CA, depenses, EBITDA ;",
        "montrer les factures en retard et les alertes ;",
        "poser une question a l'IA : 'Quelle est ma situation de tresorerie ?' ;",
        "afficher une prevision de cash ou expliquer les donnees requises ;",
        "montrer la logique comptable OHADA et les exports ;",
        "terminer par une offre d'essai ou un onboarding accompagne.",
    ]))

    story += section("Tunnel De Vente", "Transformer l'interet en abonnement", CYAN)
    story.append(styled_table(
        ["Etape", "Objectif", "Action recommandee"],
        [
            ["Acquisition", "Faire entrer le prospect dans l'univers SakinaFinance IA.", "LinkedIn, webinaires, cabinets, recommandations, contenu SEO SYSCOHADA/tresorerie."],
            ["Qualification", "Comprendre taille, logiciel actuel, role du cabinet, modules necessaires.", "Questions sur utilisateurs, entites, Sage/Excel/Odoo, factures impayees, paie, achats."],
            ["Demo", "Creer l'effet 'je me vois dedans'.", "Adapter la demo au persona : cash pour CEO, reporting pour DAF, OHADA pour comptable."],
            ["Offre", "Reduire la friction de decision.", "Plan mensuel, plan annuel, onboarding, pack migration, offre cabinet si besoin."],
            ["Activation", "Atteindre l'aha moment en moins de 30 minutes.", "Importer quelques transactions, voir le dashboard, poser une question IA, detecter un impaye."],
        ],
        [2.7 * cm, 5.1 * cm, 8.8 * cm],
    ))

    story += section("Contenus Marketing Prets A Publier", "Posts, webinaires et angles editoriaux", GREEN)
    story.append(p("<b>Piliers de contenu :</b> education financiere, conformite OHADA, productivite comptable, IA appliquee a la finance, cas metiers PME/cabinets/groupes.", "Body"))
    story.append(two_col_cards([
        ("Post LinkedIn - Excel", "Excel est pratique pour demarrer. Mais quand l'entreprise grandit, Excel devient fragile : versions multiples, erreurs de formule, absence de piste d'audit et consolidation manuelle. SakinaFinance IA remplace les fichiers disperses par une base fiable.", BLUE),
        ("Post LinkedIn - CEO", "Votre bilan annuel arrive trop tard pour piloter. Un dirigeant doit savoir aujourd'hui combien il a en cash, quelles factures sont en retard, quelle marge il realise et quels risques arrivent.", CYAN),
        ("Post LinkedIn - Cabinet", "Experts-comptables : vos clients ne manquent pas seulement de conformite, ils manquent de methode. SakinaFinance IA structure les donnees client au quotidien et libere du temps pour le conseil.", GOLD),
        ("Webinaire choc", "Comment prevoir votre tresorerie sur 6 mois sans DAF : 30 min de contenu, 10 min de demo, 10 min de questions, offre speciale valable 7 jours.", GREEN),
    ]))

    story += section("Objections Et Reponses", "Preparer les commerciaux", GOLD)
    story.append(styled_table(
        ["Objection", "Reponse recommandee"],
        [
            ["Nous utilisons deja Sage.", "Tres bien : SakinaFinance IA ne vend pas seulement de la saisie comptable, mais du pilotage, de l'analyse, de l'alerte et de la decision."],
            ["Excel nous suffit.", "Excel suffit au debut. Des que les factures, la paie, les achats, la tresorerie et la fiscalite augmentent, il devient un risque."],
            ["Notre comptable s'en occupe.", "Le comptable produit souvent une photographie passee. SakinaFinance IA donne une vision quotidienne et une base plus propre au comptable."],
            ["C'est trop cher.", "Comparer au temps perdu, aux erreurs, aux penalites, aux impayes oublies et aux mauvaises decisions de cash."],
            ["L'IA est-elle fiable ?", "L'IA aide a analyser et prioriser. Elle ne remplace pas le controle humain : les donnees et sources restent verifiables."],
        ],
        [4.2 * cm, 12.4 * cm],
    ))

    story += section("Roadmap Go-To-Market", "Plan d'action sur 6 mois", NAVY)
    story.append(styled_table(
        ["Periode", "Priorites", "Livrables"],
        [
            ["Mois 1", "Finaliser positionnement, prix, landing page, deck, demo et liste de prospects.", "Plaquette, page vente, script demo, base 50 prospects, offre cabinet."],
            ["Mois 2", "Signer 5 cabinets beta et onboarder 20 a 50 PME via ces cabinets.", "Retours terrain, objections, premiers cas d'usage, temoignages."],
            ["Mois 3", "Lancement public et campagne 'Tuez vos fichiers Excel'.", "Webinaire, LinkedIn Ads, offre annuelle, onboarding accompagne."],
            ["Mois 4-6", "Vente directe PME/ETI, force commerciale terrain et partenariats.", "Pipeline commercial, partenariats banques/fintechs/incubateurs, process de vente repete."],
        ],
        [3.0 * cm, 7.0 * cm, 6.6 * cm],
    ))

    story += section("Priorites Produit-Marketing", "Ce qu'il faut aligner avant une campagne forte", BLUE)
    story.append(bullet([
        "Clarifier le pricing public : penetration locale ou positionnement premium.",
        "Mettre en avant OHADA/SYSCOHADA comme preuve de pertinence locale.",
        "Creer une demo avec donnees realistes : ventes, depenses, impayes, cash, paie et achats.",
        "Formaliser l'offre cabinet comptable comme levier de croissance principal.",
        "Preparer les messages autour du Mobile Money en distinguant fonctionnalites disponibles et roadmap.",
        "Faire du dashboard et de l'IA Advisor les deux moments les plus memorables de la demo.",
    ]))
    story.append(callout("Conclusion commerciale : SakinaFinance IA n'est pas seulement un logiciel de comptabilite. C'est le copilote financier des entreprises africaines qui veulent piloter leur croissance avec rigueur, intelligence et confiance.", SOFT_GREEN, GREEN))

    story.append(Spacer(1, 18))
    story.append(p("Document genere pour SakinaFinance IA - support marketing, vente SaaS et strategie de penetration OHADA.", "Center"))
    return story


def main():
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.4 * cm,
        bottomMargin=2.0 * cm,
        title="SakinaFinance IA - Document Marketing SaaS",
        author="SakinaFinance",
    )
    story = build_story()
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
