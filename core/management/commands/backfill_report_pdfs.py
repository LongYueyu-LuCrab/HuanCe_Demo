from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import TestReport
from core.report_pdf import build_test_report_pdf


class Command(BaseCommand):
    help = 'Generate protected PDF files for historical test reports that do not have one.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Regenerate PDFs that already exist.')

    def handle(self, *args, **options):
        reports = TestReport.objects.select_related(
            'order', 'order__lead_lab_manager', 'create_quality_user'
        ).order_by('id')
        if not options['force']:
            reports = reports.filter(report_file='')

        generated = 0
        skipped = 0
        for report in reports.iterator():
            experiments = report.order.experiments.select_related('test_operator', 'schedule').order_by('create_time')
            if not experiments.exists():
                skipped += 1
                self.stdout.write(self.style.WARNING(f'Skipped {report.report_no}: no experiment records'))
                continue

            old_file_name = report.report_file.name if report.report_file else ''
            report.generated_at = timezone.now()
            pdf_content = build_test_report_pdf(report, experiments)
            filename = f'{report.report_no}-{report.report_type}.pdf'
            report.report_file.save(filename, ContentFile(pdf_content), save=False)
            report.report_file_url = f'/api/reports/{report.id}/download/'
            report.save(update_fields=['generated_at', 'report_file', 'report_file_url', 'update_time'])
            if old_file_name and old_file_name != report.report_file.name:
                report.report_file.storage.delete(old_file_name)
            generated += 1
            self.stdout.write(f'Generated {report.report_no} ({report.get_report_type_display()})')

        self.stdout.write(self.style.SUCCESS(f'PDF backfill complete: generated={generated}, skipped={skipped}'))
