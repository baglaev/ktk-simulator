from __future__ import annotations

import os
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.domain import AIErrorCard, SessionAIAnalysis


class PDFReportConfigurationError(RuntimeError):
    pass


class SessionAIAnalysisPDFBuilder:
    """Render the stable SessionAIAnalysis contract as a downloadable PDF."""

    def build(self, analysis: SessionAIAnalysis) -> bytes:
        regular_font, bold_font = _register_fonts()
        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title="КТК ЭЛОУ-АВТ - итоговый ИИ-отчет",
            author="КТК ЭЛОУ-АВТ",
            subject="Учебный постсценарный разбор",
        )
        styles = _styles(regular_font, bold_font)
        story = self._story(analysis, styles)

        def add_footer(canvas, doc) -> None:
            canvas.saveState()
            canvas.setFont(regular_font, 8)
            canvas.setFillColor(colors.HexColor("#61738A"))
            canvas.drawString(
                18 * mm,
                9 * mm,
                "КТК ЭЛОУ-АВТ | Учебный отчет",
            )
            canvas.drawRightString(
                A4[0] - 18 * mm,
                9 * mm,
                f"Страница {doc.page}",
            )
            canvas.restoreState()

        document.build(
            story,
            onFirstPage=add_footer,
            onLaterPages=add_footer,
        )
        return output.getvalue()

    def _story(self, analysis: SessionAIAnalysis, styles) -> list[object]:
        story: list[object] = [
            Paragraph("КТК ЭЛОУ-АВТ", styles["brand"]),
            Paragraph("Итоговый ИИ-отчет", styles["title"]),
            Paragraph(
                "Учебный материал. Не является производственной инструкцией.",
                styles["disclaimer"],
            ),
            Spacer(1, 7 * mm),
            self._summary_table(analysis, styles),
            Spacer(1, 6 * mm),
            Paragraph("Общий вывод", styles["heading"]),
            Paragraph(_text(analysis.summary), styles["body"]),
            Spacer(1, 5 * mm),
            Paragraph("Сильные стороны", styles["heading"]),
        ]
        story.extend(_bullets(analysis.strengths, styles))
        story.extend(
            [
                Spacer(1, 5 * mm),
                Paragraph("Разбор ошибок", styles["heading"]),
            ]
        )
        if analysis.errors:
            for error in analysis.errors:
                story.extend(self._error_card(error, styles))
        else:
            story.append(
                Paragraph(
                    "Ошибки, требующие отдельного разбора, не зафиксированы.",
                    styles["body"],
                )
            )
        story.extend(
            [
                Spacer(1, 5 * mm),
                Paragraph("Рекомендации", styles["heading"]),
            ]
        )
        story.extend(_bullets(analysis.recommendations, styles))
        story.extend(
            [
                Spacer(1, 3 * mm),
                Paragraph("Происхождение отчета", styles["heading"]),
                self._provenance_table(analysis, styles),
            ]
        )
        return story

    @staticmethod
    def _summary_table(analysis: SessionAIAnalysis, styles) -> Table:
        status_label = {
            "passed": "Пройдено",
            "passed_with_remarks": "Пройдено с замечаниями",
            "failed": "Не пройдено",
        }.get(analysis.result_status.value, analysis.result_status.value)
        table = Table(
            [
                [
                    Paragraph("Результат", styles["table_label"]),
                    Paragraph("Итоговый балл", styles["table_label"]),
                ],
                [
                    Paragraph(_text(status_label), styles["table_value"]),
                    Paragraph(
                        f"{analysis.total_score} / 100",
                        styles["score"],
                    ),
                ],
                [
                    Paragraph("Идентификатор сессии", styles["table_label"]),
                    Paragraph(
                        _text(str(analysis.session_id)),
                        styles["table_small"],
                    ),
                ],
            ],
            colWidths=[76 * mm, 82 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F2F7FC")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCEAF7")),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#A9BED2")),
                    ("INNERGRID", (0, 0), (-1, -2), 0.4, colors.HexColor("#C5D5E4")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        return table

    @staticmethod
    def _error_card(error: AIErrorCard, styles) -> list[object]:
        classification = {
            "diagnostics": "Диагностика",
            "sequence": "Последовательность",
            "safety": "Безопасность",
            "monitoring": "Контроль параметров",
            "timeliness": "Своевременность",
        }.get(error.classification, error.classification)
        status = {
            "success": "Успех",
            "warning": "Предупреждение",
            "alert": "Критично",
        }.get(error.status.value, error.status.value)
        hint_time = (
            _format_ms(error.hint_shown_at_ms)
            if error.hint_shown_at_ms is not None
            else "не показывалась"
        )
        rows = [
            [
                Paragraph(
                    _text(f"{error.order}. {classification}: {error.code}"),
                    styles["card_title"],
                )
            ],
            [
                Paragraph(
                    _text(
                        f"Статус: {status} | Обнаружено: "
                        f"{_format_ms(error.detected_at_ms)} | "
                        f"Подсказка: {hint_time}"
                    ),
                    styles["card_meta"],
                )
            ],
            [
                Paragraph(
                    f"<b>Действие:</b> {_text(error.user_action)}",
                    styles["card_body"],
                )
            ],
            [
                Paragraph(
                    f"<b>Последствие:</b> {_text(error.consequence)}",
                    styles["card_body"],
                )
            ],
            [
                Paragraph(
                    f"<b>Правильный учебный подход:</b> "
                    f"{_text(error.correct_approach)}",
                    styles["card_body"],
                )
            ],
            [
                Paragraph(
                    f"<b>Прогноз:</b> {_text(error.prediction)}",
                    styles["card_body"],
                )
            ],
        ]
        table = Table(rows, colWidths=[158 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCEAF7")),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F2F7FC")),
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#A9BED2")),
                    ("LINEBELOW", (0, 1), (-1, 1), 0.4, colors.HexColor("#C5D5E4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return [KeepTogether([table, Spacer(1, 3 * mm)])]

    @staticmethod
    def _provenance_table(analysis: SessionAIAnalysis, styles) -> Table:
        provenance = analysis.provenance
        method_label = {
            "deterministic_template": "Детерминированный шаблон",
            "deterministic_plus_llm": "Детерминированный анализ + LLM",
        }.get(provenance.method, provenance.method)
        rows = [
            ["Метод", method_label],
            ["LLM использована", "да" if provenance.llm_used else "нет"],
            ["Модель", provenance.resolved_model or "не применялась"],
            ["Оценка изменена ИИ", "нет"],
            ["Источники", ", ".join(provenance.source_refs) or "не указаны"],
        ]
        table = Table(
            [
                [
                    Paragraph(_text(label), styles["table_label"]),
                    Paragraph(_text(value), styles["table_small"]),
                ]
                for label, value in rows
            ],
            colWidths=[52 * mm, 106 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#A9BED2")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C5D5E4")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F2F7FC")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return table


def _styles(regular_font: str, bold_font: str):
    sample = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "PDFBrand",
            parent=sample["Normal"],
            fontName=bold_font,
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#1878C8"),
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "title": ParagraphStyle(
            "PDFTitle",
            parent=sample["Title"],
            fontName=bold_font,
            fontSize=22,
            leading=27,
            textColor=colors.HexColor("#0A2540"),
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "disclaimer": ParagraphStyle(
            "PDFDisclaimer",
            parent=sample["Normal"],
            fontName=regular_font,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#61738A"),
            alignment=TA_CENTER,
        ),
        "heading": ParagraphStyle(
            "PDFHeading",
            parent=sample["Heading2"],
            fontName=bold_font,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0A4E85"),
            spaceAfter=7,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "PDFBody",
            parent=sample["BodyText"],
            fontName=regular_font,
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#263746"),
            spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "PDFBullet",
            parent=sample["BodyText"],
            fontName=regular_font,
            fontSize=9.5,
            leading=14,
            leftIndent=5 * mm,
            firstLineIndent=-3 * mm,
            textColor=colors.HexColor("#263746"),
            spaceAfter=4,
        ),
        "table_label": ParagraphStyle(
            "PDFTableLabel",
            parent=sample["Normal"],
            fontName=bold_font,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#355269"),
        ),
        "table_value": ParagraphStyle(
            "PDFTableValue",
            parent=sample["Normal"],
            fontName=bold_font,
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0A2540"),
        ),
        "table_small": ParagraphStyle(
            "PDFTableSmall",
            parent=sample["Normal"],
            fontName=regular_font,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#263746"),
        ),
        "score": ParagraphStyle(
            "PDFScore",
            parent=sample["Normal"],
            fontName=bold_font,
            fontSize=16,
            leading=19,
            textColor=colors.HexColor("#1878C8"),
        ),
        "card_title": ParagraphStyle(
            "PDFCardTitle",
            parent=sample["Normal"],
            fontName=bold_font,
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#0A2540"),
        ),
        "card_meta": ParagraphStyle(
            "PDFCardMeta",
            parent=sample["Normal"],
            fontName=regular_font,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#52687A"),
        ),
        "card_body": ParagraphStyle(
            "PDFCardBody",
            parent=sample["BodyText"],
            fontName=regular_font,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#263746"),
            spaceAfter=0,
        ),
    }


def _bullets(items: list[str], styles) -> list[Paragraph]:
    if not items:
        return [Paragraph("- Не зафиксировано.", styles["bullet"])]
    return [Paragraph(f"- {_text(item)}", styles["bullet"]) for item in items]


def _text(value: object) -> str:
    normalized = (
        str(value)
        .replace("\u2011", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )
    return escape(normalized).replace("\n", "<br/>")


def _format_ms(value: int) -> str:
    total_seconds = value // 1_000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


@lru_cache(maxsize=1)
def _register_fonts() -> tuple[str, str]:
    regular_path, bold_path = _resolve_font_paths()
    regular_name = "KTKPDFRegular"
    bold_name = "KTKPDFBold"
    if regular_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(regular_name, str(regular_path)))
    if bold_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_name, str(bold_path)))
    pdfmetrics.registerFontFamily(
        "KTKPDF",
        normal=regular_name,
        bold=bold_name,
    )
    return regular_name, bold_name


def _resolve_font_paths() -> tuple[Path, Path]:
    configured_regular = os.getenv("PDF_FONT_PATH")
    configured_bold = os.getenv("PDF_FONT_BOLD_PATH")
    if configured_regular:
        regular = Path(configured_regular).expanduser()
        bold = Path(configured_bold).expanduser() if configured_bold else regular
        if regular.is_file() and bold.is_file():
            return regular, bold
        raise PDFReportConfigurationError(
            "PDF_FONT_PATH or PDF_FONT_BOLD_PATH points to a missing font"
        )

    candidates = (
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
            Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        ),
        (
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        ),
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
    )
    for regular, bold in candidates:
        if regular.is_file() and bold.is_file():
            return regular, bold
    raise PDFReportConfigurationError(
        "Unicode PDF font was not found; configure PDF_FONT_PATH and "
        "PDF_FONT_BOLD_PATH"
    )
