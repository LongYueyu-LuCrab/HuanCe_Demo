from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import LabOrder, ReportAudit, TestReport
from .views import _workflow_progress_payload


class ReportReviewRoundTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='review-round')
        self.order = LabOrder.objects.create(
            order_no='REVIEW-ROUND', customer_name='Synthetic customer',
            sale_user=self.user, order_status=LabOrder.Status.REPORT_REVIEW,
        )
        self.generated = timezone.now()
        self.report = TestReport.objects.create(
            order=self.order, report_no='REPORT-ROUND',
            report_status=TestReport.Status.SALES_REVIEW,
            generated_at=self.generated, create_quality_user=self.user,
        )

    def audit(self, level, result, when):
        return ReportAudit.objects.create(
            report=self.report, audit_level=level, audit_result=result,
            audit_user=self.user, audit_time=when,
        )

    def states(self):
        return {
            step['key']: step['state']
            for step in _workflow_progress_payload(self.order)['steps']
        }

    def test_remake_does_not_reuse_previous_round_approval(self):
        self.audit(ReportAudit.Level.SALES, ReportAudit.Result.APPROVED,
                   self.generated - timedelta(minutes=2))
        self.audit(ReportAudit.Level.GENERAL_MANAGER, ReportAudit.Result.REJECTED,
                   self.generated - timedelta(minutes=1))
        states = self.states()
        self.assertEqual(states['sales_audit'], 'current')
        self.assertEqual(states['gm_audit'], 'pending')
        self.assertEqual(self.report.audits.count(), 2)

    def test_current_round_approval_is_completed(self):
        self.audit(ReportAudit.Level.SALES, ReportAudit.Result.APPROVED,
                   self.generated + timedelta(seconds=1))
        self.report.report_status = TestReport.Status.GM_REVIEW
        self.report.save()
        states = self.states()
        self.assertEqual(states['sales_audit'], 'completed')
        self.assertEqual(states['gm_audit'], 'current')

    def test_legacy_report_without_generation_time_keeps_audits(self):
        self.report.generated_at = None
        self.report.report_status = TestReport.Status.GM_REVIEW
        self.report.save()
        self.audit(ReportAudit.Level.SALES, ReportAudit.Result.APPROVED,
                   self.generated - timedelta(minutes=1))
        self.assertEqual(self.states()['sales_audit'], 'completed')
