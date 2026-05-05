import io
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.services.level_decider import LevelDecision, sub_level_explanation_fr, sub_level_explanation_en


CRITERION_NAMES_FR = {
    "interaction": "Interaction",
    "clarity": "Clarté du message",
    "strategies": "Stratégies de communication",
    "vocabulary": "Vocabulaire et structures",
    "fluency": "Fluidité et aisance",
    "pronunciation": "Prononciation",
}

CRITERION_NAMES_EN = {
    "interaction": "Interaction",
    "clarity": "Message Clarity",
    "strategies": "Communication Strategies",
    "vocabulary": "Vocabulary & Structures",
    "fluency": "Fluency & Ease",
    "pronunciation": "Pronunciation",
}


def _yes_no_fr(achieved: bool | None) -> str:
    if achieved is True:
        return "Oui"
    if achieved is False:
        return "Non"
    return "N/A"


def _yes_no_en(achieved: bool | None) -> str:
    if achieved is True:
        return "Yes"
    if achieved is False:
        return "No"
    return "N/A"


def generate_pdf(
    evaluation_id: str,
    decision: LevelDecision,
    criteria_results: dict,
    global_comment_fr: str,
    global_comment_en: str,
    student_name: str | None = None,
    evaluator_name: str | None = None,
    institution: str | None = None,
    evaluation_date: date | None = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], alignment=TA_CENTER, fontSize=16, spaceAfter=12)
    heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=13, spaceAfter=8)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, spaceAfter=4)
    label_style = ParagraphStyle("Label", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold")

    elements = []

    def add_section_fr():
        elements.append(Paragraph("GRILLE D'ÉVALUATION MÉTRO-LANG", title_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.darkblue))
        elements.append(Spacer(1, 0.4 * cm))

        # General information
        elements.append(Paragraph("Informations générales", heading_style))
        info_data = [
            ["Nom de l'étudiant:", student_name or "—"],
            ["Évaluateur:", evaluator_name or "—"],
            ["Institution:", institution or "—"],
            ["Date:", str(evaluation_date) if evaluation_date else "—"],
            ["Référence:", str(evaluation_id)],
        ]
        info_table = Table(info_data, colWidths=[5 * cm, 12 * cm])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.4 * cm))

        # Level
        elements.append(Paragraph("Résultat global", heading_style))
        elements.append(Paragraph(f"<b>Niveau CECR:</b> {decision.cefr_level}", body_style))
        elements.append(Paragraph(f"<b>Profil communicatif:</b> {decision.communicative_profile_fr}", body_style))
        elements.append(Spacer(1, 0.3 * cm))

        # Criteria table
        elements.append(Paragraph("Tableau des critères d'évaluation", heading_style))
        criteria_header = ["Critère", "Atteint", "Commentaire justificatif"]
        criteria_data = [criteria_header]
        for key, name in CRITERION_NAMES_FR.items():
            result = criteria_results.get(key, {})
            achieved = result.get("achieved")
            comment = result.get("comment_fr") or result.get("error", "N/A")
            criteria_data.append([name, _yes_no_fr(achieved), comment or ""])

        criteria_table = Table(criteria_data, colWidths=[4.5 * cm, 2 * cm, 10.5 * cm])
        criteria_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("WORDWRAP", (2, 1), (2, -1), True),
        ]))
        elements.append(criteria_table)
        elements.append(Spacer(1, 0.4 * cm))

        # Sub-level explanation
        elements.append(Paragraph("Attribution du sous-niveau", heading_style))
        elements.append(Paragraph(sub_level_explanation_fr(decision), body_style))
        elements.append(Spacer(1, 0.3 * cm))

        # Global comment
        elements.append(Paragraph("Commentaire global", heading_style))
        elements.append(Paragraph(global_comment_fr or "—", body_style))

    def add_section_en():
        elements.append(PageBreak())
        elements.append(Paragraph("MÉTRO-LANG EVALUATION GRID", title_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.darkblue))
        elements.append(Spacer(1, 0.4 * cm))

        elements.append(Paragraph("General Information", heading_style))
        info_data = [
            ["Student Name:", student_name or "—"],
            ["Evaluator:", evaluator_name or "—"],
            ["Institution:", institution or "—"],
            ["Date:", str(evaluation_date) if evaluation_date else "—"],
            ["Reference:", str(evaluation_id)],
        ]
        info_table = Table(info_data, colWidths=[5 * cm, 12 * cm])
        info_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.4 * cm))

        elements.append(Paragraph("Overall Result", heading_style))
        elements.append(Paragraph(f"<b>CEFR Level:</b> {decision.cefr_level}", body_style))
        elements.append(Paragraph(f"<b>Communicative Profile:</b> {decision.communicative_profile_en}", body_style))
        elements.append(Spacer(1, 0.3 * cm))

        elements.append(Paragraph("Evaluation Criteria Table", heading_style))
        criteria_header = ["Criterion", "Achieved", "Justification Comment"]
        criteria_data = [criteria_header]
        for key, name in CRITERION_NAMES_EN.items():
            result = criteria_results.get(key, {})
            achieved = result.get("achieved")
            comment = result.get("comment_en") or result.get("error", "N/A")
            criteria_data.append([name, _yes_no_en(achieved), comment or ""])

        criteria_table = Table(criteria_data, colWidths=[4.5 * cm, 2 * cm, 10.5 * cm])
        criteria_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(criteria_table)
        elements.append(Spacer(1, 0.4 * cm))

        elements.append(Paragraph("Sub-level Attribution", heading_style))
        elements.append(Paragraph(sub_level_explanation_en(decision), body_style))
        elements.append(Spacer(1, 0.3 * cm))

        elements.append(Paragraph("Global Comment", heading_style))
        elements.append(Paragraph(global_comment_en or "—", body_style))

    add_section_fr()
    add_section_en()

    doc.build(elements)
    return buffer.getvalue()
