from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Group

from .models import Customer, LabOrder, WorkflowEvent


class LimsDashboardTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_user(
            username='tester',
            password='password123',
        )
        sales_group = Group.objects.create(name='销售')
        self.user.groups.add(sales_group)
        self.customer = Customer.objects.create(name='苏州环测检测技术有限公司')
        self.order = LabOrder.objects.create(
            order_no='TEST-001',
            customer=self.customer,
            project_name='测试订单',
            test_requirements='测试需求',
            sales_owner=self.user,
            status=LabOrder.Status.TESTING,
        )

    def test_dashboard_api_returns_lims_summary(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('lims_dashboard'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['company'], '苏州环测检测技术有限公司')
        self.assertEqual(data['metrics']['orders'], 1)
        self.assertEqual(data['metrics']['active_orders'], 1)
        self.assertEqual(len(data['recent_orders']), 1)
        self.assertEqual(data['recent_orders'][0]['order_no'], 'TEST-001')

    def test_mark_status_writes_workflow_event(self):
        self.order.mark_status(LabOrder.Status.REPORT_DRAFT, note='测试流转')

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, LabOrder.Status.REPORT_DRAFT)
        self.assertTrue(
            WorkflowEvent.objects.filter(
                order=self.order,
                from_status=LabOrder.Status.TESTING,
                to_status=LabOrder.Status.REPORT_DRAFT,
            ).exists()
        )

    def test_sales_can_create_order(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('create_order'),
            data={
                'customer_name': '新客户',
                'contact_name': '王五',
                'phone': '13800000000',
                'project_name': '新项目',
                'test_requirements': '完成可靠性检测。',
                'expected_sample_arrival': '2026-07-01',
                'expected_delivery_date': '2026-07-15',
                'quoted_amount': '12000.50',
                'is_urgent': True,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['ok'])
        created = LabOrder.objects.get(order_no=payload['order']['order_no'])
        self.assertEqual(created.sales_owner, self.user)
        self.assertEqual(created.status, LabOrder.Status.REVIEWING)
