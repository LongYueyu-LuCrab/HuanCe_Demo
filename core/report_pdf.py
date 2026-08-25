from html import escape
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import TestReport


FONT_NAME = 'STSong-Light'
pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))


def _text(value):
    if value in (None, ''):
        return '-'
    return escape(str(value)).replace('\n', '<br/>')


def _datetime(value):
    if not value:
        return '-'
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime('%Y-%m-%d %H:%M')


def _report_styles():
    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        'HuanCeBody', parent=styles['BodyText'], fontName=FONT_NAME,
        fontSize=9.5, leading=15, textColor=colors.HexColor('#243447'),
    )
    return {
        'body': base,
        'small': ParagraphStyle('HuanCeSmall', parent=base, fontSize=8, leading=12, textColor=colors.HexColor('#5f6b7a')),
        'title': ParagraphStyle('HuanCeTitle', parent=base, fontSize=20, leading=28, alignment=TA_CENTER, textColor=colors.HexColor('#102a43'), spaceAfter=4 * mm),
        'subtitle': ParagraphStyle('HuanCeSubtitle', parent=base, fontSize=11, leading=16, alignment=TA_CENTER, textColor=colors.HexColor('#486581'), spaceAfter=6 * mm),
        'section': ParagraphStyle('HuanCeSection', parent=base, fontSize=12, leading=18, textColor=colors.HexColor('#0b6b57'), spaceBefore=4 * mm, spaceAfter=2 * mm),
        'warning': ParagraphStyle('HuanCeWarning', parent=base, fontSize=8, leading=12, alignment=TA_CENTER, textColor=colors.HexColor('#c53030')),
    }


def _paragraph(value, style):
    return Paragraph(_text(value), style)


def _draw_page(canvas, document, report, styles):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor('#d9e2ec'))
    canvas.line(18 * mm, height - 16 * mm, width - 18 * mm, height - 16 * mm)
    canvas.setFont(FONT_NAME, 7.5)
    canvas.setFillColor(colors.HexColor('#7b8794'))
    canvas.drawString(18 * mm, 10 * mm, f'苏州环测检测技术有限公司  |  {report.report_no}')
    canvas.drawRightString(width - 18 * mm, 10 * mm, f'第 {document.page} 页')

    if report.report_type == TestReport.ReportType.FORMAL:
        seal_path = Path(settings.BASE_DIR) / 'core' / 'assets' / 'report_demo_seal.png'
        if seal_path.exists():
            canvas.setFillAlpha(0.14)
            canvas.drawImage(
                str(seal_path), width - 78 * mm, 22 * mm,
                width=53 * mm, height=53 * mm, mask='auto', preserveAspectRatio=True,
            )
            canvas.setFillAlpha(1)
        canvas.setFillColor(colors.HexColor('#c53030'))
        canvas.setFont(FONT_NAME, 7)
        canvas.drawRightString(width - 20 * mm, 19 * mm, '示例占位章（DEMO），不具法律效力')
    canvas.restoreState()


def build_test_report_pdf(report, experiments):
    order = report.order
    experiments = list(experiments)
    styles = _report_styles()
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=22 * mm, bottomMargin=18 * mm,
        title=f'{report.report_no} {report.get_report_type_display()}',
        author='苏州环测检测技术有限公司',
    )
    story = [
        Paragraph('苏州环测检测技术有限公司', styles['subtitle']),
        Paragraph('检测报告', styles['title']),
        Paragraph(f'{report.get_report_type_display()} · {report.report_no}', styles['subtitle']),
    ]
    if report.report_type == TestReport.ReportType.FORMAL:
        story.append(Paragraph('本报告使用“示例章 / DEMO”占位水印，正式公章素材启用前不具法律效力。', styles['warning']))
        story.append(Spacer(1, 4 * mm))

    metadata = [
        [_paragraph('委托单位', styles['body']), _paragraph(order.customer_name, styles['body']), _paragraph('订单编号', styles['body']), _paragraph(order.order_no, styles['body'])],
        [_paragraph('项目名称', styles['body']), _paragraph(order.project_name, styles['body']), _paragraph('报告版本', styles['body']), _paragraph(report.get_report_type_display(), styles['body'])],
        [_paragraph('行业属性', styles['body']), _paragraph(order.get_industry_category_display(), styles['body']), _paragraph('执行路径', styles['body']), _paragraph(order.get_execution_mode_display(), styles['body'])],
        [_paragraph('测试方法', styles['body']), _paragraph(order.test_method, styles['body']), _paragraph('测试标准', styles['body']), _paragraph(order.test_standard, styles['body'])],
        [_paragraph('主责实验室', styles['body']), _paragraph(order.lead_lab_manager.first_name or order.lead_lab_manager.username if order.lead_lab_manager else '-', styles['body']), _paragraph('生成时间', styles['body']), _paragraph(_datetime(report.generated_at or timezone.now()), styles['body'])],
    ]
    metadata_table = Table(metadata, colWidths=[24 * mm, 62 * mm, 24 * mm, 62 * mm])
    metadata_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#edf7f4')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#edf7f4')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5), ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.extend([metadata_table, Paragraph('试验数据', styles['section'])])

    experiment_rows = [[
        _paragraph('试验项目', styles['small']), _paragraph('类型', styles['small']),
        _paragraph('操作人', styles['small']), _paragraph('开始时间', styles['small']),
        _paragraph('结束时间', styles['small']), _paragraph('状态', styles['small']),
    ]]
    for experiment in experiments:
        experiment_rows.append([
            _paragraph(experiment.test_item_list, styles['small']),
            _paragraph(experiment.get_test_type_display(), styles['small']),
            _paragraph(experiment.test_operator.first_name or experiment.test_operator.username if experiment.test_operator else '-', styles['small']),
            _paragraph(_datetime(experiment.test_start_time), styles['small']),
            _paragraph(_datetime(experiment.test_end_time), styles['small']),
            _paragraph(experiment.get_test_status_display(), styles['small']),
        ])
    experiment_table = Table(experiment_rows, repeatRows=1, colWidths=[42 * mm, 25 * mm, 25 * mm, 29 * mm, 29 * mm, 22 * mm])
    experiment_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT_NAME),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dff3ed')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(experiment_table)

    for index, experiment in enumerate(experiments, start=1):
        story.extend([
            Paragraph(f'{index}. {_text(experiment.test_item_list)}', styles['section']),
            Paragraph(f'<b>原始数据：</b>{_text(experiment.test_raw_data)}', styles['body']),
            Spacer(1, 1.5 * mm),
            Paragraph(f'<b>试验结论：</b>{_text(experiment.test_conclusion_temp)}', styles['body']),
        ])

    if report.report_type != TestReport.ReportType.DATA_ONLY:
        story.extend([
            Paragraph('最终结论', styles['section']),
            Paragraph(_text(report.final_conclusion), styles['body']),
            Spacer(1, 7 * mm),
            Paragraph(f'报告出具人：{_text(report.create_quality_user.first_name or report.create_quality_user.username if report.create_quality_user else "-")}', styles['body']),
        ])
    else:
        story.append(Paragraph('仅数据版仅呈现实验基本信息与原始数据，不作为正式检测结论。', styles['warning']))

    document.build(
        story,
        onFirstPage=lambda canvas, doc: _draw_page(canvas, doc, report, styles),
        onLaterPages=lambda canvas, doc: _draw_page(canvas, doc, report, styles),
    )
    return output.getvalue()
