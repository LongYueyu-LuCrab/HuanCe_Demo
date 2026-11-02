from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .models import Experiment, LabOrder, TestReport
from .views import _order_payload


class ReportIssueGuardTests(TestCase):
    def setUp(self):
        quality_group, _ = Group.objects.get_or_create(name='质量部')
        self.quality = get_user_model().objects.create_user(
            username='report-guard-quality', password='password123', first_name='质量测试员',
        )
        self.quality.groups.add(quality_group)
        self.order = LabOrder.objects.create(
            order_no='REPORT-GUARD-001',
            customer_name='报告防重客户',
            project_name='报告防重测试',
            test_demand='报告防重测试项目',
            order_status=LabOrder.Status.REPORT_REVIEW,
            workflow_version=LabOrder.WorkflowVersion.LEGACY_QUALITY,
        )
        self.experiment = Experiment.objects.create(
            order=self.order,
            test_item_list='报告防重实验',
            test_status=Experiment.Status.FINISHED,
            result_status=Experiment.Result.PASS,
        )
        self.report = TestReport.objects.create(
            order=self.order,
            test_record=self.experiment,
            report_no='REPORT-GUARD-001-RPT',
            report_status=TestReport.Status.APPROVED,
        )

    def test_order_payload_exposes_latest_report_state(self):
        payload = _order_payload(self.order, viewer=self.quality)
        self.assertEqual(payload['latest_report_no'], self.report.report_no)
        self.assertEqual(payload['latest_report_status_key'], TestReport.Status.APPROVED)
        self.assertEqual(payload['latest_report_status'], '审核通过待开票')

    def test_approved_report_cannot_be_issued_again(self):
        self.client.force_login(self.quality)
        response = self.client.post(
            reverse('lims_action'),
            data={
                'action': 'issue_report',
                'order_no': self.order.order_no,
                'final_conclusion': '不应重复生成',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('不能重复出具', response.json()['error'])
        self.assertEqual(self.order.reports.count(), 1)
