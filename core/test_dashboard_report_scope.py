from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .models import LabOrder, TestReport


class DashboardReportScopeTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.sales = user_model.objects.create_user(username='scope-sales', password='password123')
        self.general_manager = user_model.objects.create_user(username='scope-gm', password='password123')
        self.quality = user_model.objects.create_user(username='scope-quality', password='password123')
        self.sales.groups.add(Group.objects.get_or_create(name='销售')[0])
        self.general_manager.groups.add(Group.objects.get_or_create(name='总经理')[0])
        self.quality.groups.add(Group.objects.get_or_create(name='质量部')[0])

        self.orders = []
        for index, status in enumerate(TestReport.Status, start=1):
            order = LabOrder.objects.create(
                order_no=f'SCOPE-{index:03d}',
                customer_name='范围测试客户',
                project_name=f'报告范围测试-{index}',
                test_demand='验证仪表盘报告待办范围',
                sale_user=self.sales,
                order_status=LabOrder.Status.REPORT_REVIEW,
                workflow_version=LabOrder.WorkflowVersion.LEGACY_QUALITY,
            )
            TestReport.objects.create(
                order=order,
                report_no=f'SCOPE-RPT-{index:03d}',
                report_status=status,
            )
            self.orders.append(order)

    def dashboard(self, user):
        self.client.force_login(user)
        response = self.client.get(reverse('lims_dashboard'))
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_sales_dashboard_only_returns_sales_review_reports(self):
        data = self.dashboard(self.sales)
        self.assertEqual(data['metrics']['pending_reports'], 1)
        self.assertEqual([item['status_key'] for item in data['pending_reports']], [TestReport.Status.SALES_REVIEW])
        self.assertEqual(
            [item['order_no'] for item in data['order_groups']['pending_reports']],
            ['SCOPE-002'],
        )

    def test_general_manager_dashboard_only_returns_gm_review_reports(self):
        data = self.dashboard(self.general_manager)
        self.assertEqual(data['metrics']['pending_reports'], 1)
        self.assertEqual([item['status_key'] for item in data['pending_reports']], [TestReport.Status.GM_REVIEW])
        self.assertEqual(data['order_groups']['pending_reports'][0]['status'], '待总经理终审')

    def test_quality_dashboard_only_returns_draft_or_rejected_reports(self):
        data = self.dashboard(self.quality)
        self.assertEqual(data['metrics']['pending_reports'], 2)
        self.assertEqual(
            {item['status_key'] for item in data['pending_reports']},
            {TestReport.Status.DRAFT, TestReport.Status.REJECTED},
        )
