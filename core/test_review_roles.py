from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import LabDevice, LabOrder, SchedulePlan
from .views import _has_dual_review_pass


class ReviewRoleTests(TestCase):
    def setUp(self):
        self.users = {}
        for username, role in [('dept', '商务部'), ('sales', '销售'), ('chair', '董事长'), ('gm', '总经理'), ('lab', '苏州实验室'), ('oldbiz', '商务'), ('oldtech', '技术')]:
            user = get_user_model().objects.create_user(username)
            user.groups.add(Group.objects.get_or_create(name=role)[0])
            self.users[username] = user
        self.order = LabOrder.objects.create(order_no='ROLE-TEST', sale_user=self.users['dept'], customer_name='角色回归', test_demand='虚拟试验', workflow_version=2)
        self.other = LabOrder.objects.create(order_no='OTHER-OWNER', sale_user=self.users['sales'], workflow_version=2)
        self.device = LabDevice.objects.create(device_code='ROLE-DEVICE', device_name='测试设备', lab_type=1)
        self.routing = {'execution_routes': ['suzhou'], 'suzhou_manager_id': self.users['lab'].pk, 'lead_lab_manager_id': self.users['lab'].pk}

    def action(self, user, action, **payload):
        self.client.force_login(self.users[user])
        return self.client.post(reverse('lims_action'), {'order_no': self.order.order_no, 'action': action, **payload}, content_type='application/json')

    def approve(self, first='chair'):
        second = 'gm' if first == 'chair' else 'chair'
        for user in [first, second]:
            response = self.action(user, 'review_pass', **self.routing)
            self.assertEqual(response.status_code, 200, response.content)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, 3)

    def test_both_responsibilities_required_and_duplicate_does_not_count_twice(self):
        for _ in range(2):
            self.assertEqual(self.action('chair', 'review_pass', **self.routing).status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, 1)
        self.assertEqual(self.order.reviews.count(), 1)
        self.assertEqual(self.order.reviews.first().biz_review_user, self.users['chair'])
        self.assertIsNone(self.order.reviews.first().tech_review_user)
        self.assertFalse(self.order.schedules.exists())
        self.approve()
        self.assertEqual(self.order.reviews.get(tech_review_user__isnull=False).tech_review_user, self.users['gm'])
        self.assertEqual(self.order.schedules.get().lab_manager, self.users['lab'])

    def test_technical_then_business_also_routes(self):
        self.approve('gm')

    def test_retired_reviewers_and_department_cannot_approve(self):
        for user in ['oldbiz', 'oldtech', 'dept', 'sales']:
            for action in ['review_pass', 'review_reject']:
                with self.subTest(user=user, action=action):
                    self.assertEqual(self.action(user, action, **self.routing).status_code, 403)
        self.assertFalse(self.order.reviews.exists())

    def test_rejection_resubmission_requires_both_new_decisions(self):
        self.assertEqual(self.action('gm', 'review_pass', **self.routing).status_code, 200)
        self.assertEqual(self.action('chair', 'review_reject', reject_reason='报价需修订').status_code, 200)
        rejection = self.order.reviews.filter(review_result=False).get()
        self.assertEqual(rejection.biz_review_user, self.users['chair'])
        self.assertIsNone(rejection.tech_review_user)
        self.assertEqual(self.action('dept', 'order_update', test_demand='已修订').status_code, 200)
        self.assertEqual(self.action('chair', 'review_pass').status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, 1)
        self.assertFalse(_has_dual_review_pass(self.order))
        self.assertEqual(self.action('gm', 'review_pass', **self.routing).status_code, 200)
        self.order.refresh_from_db()
        self.assertTrue(_has_dual_review_pass(self.order))
        self.assertEqual(self.order.reviews.count(), 4)

    def test_department_all_order_query_export_but_own_sales_mutations(self):
        self.client.force_login(self.users['dept'])
        listed = self.client.get(reverse('sales_manager_orders')).json()
        self.assertEqual(listed['total'], 2)
        self.assertEqual(self.client.get(reverse('sales_manager_orders_export')).status_code, 200)
        self.assertEqual(self.client.get(reverse('order_detail', kwargs={'order_no': self.other.order_no})).status_code, 200)
        self.assertEqual(self.action('dept', 'order_update', order_no=self.other.order_no, project_name='不应修改').status_code, 403)
        self.client.force_login(self.users['sales'])
        self.assertEqual(self.client.get(reverse('sales_manager_orders')).json()['total'], 1)

    def test_department_can_schedule_other_owner_without_lab_execution_privileges(self):
        self.other.order_status = 3
        self.other.save()
        schedule = SchedulePlan.objects.create(order=self.other, test_type=1, lab_manager=self.users['lab'])
        self.client.force_login(self.users['dept'])
        availability = self.client.get(reverse('lab_device_availability'), {'schedule_id': schedule.pk, 'start_date': '2026-12-01', 'end_date': '2026-12-01'})
        self.assertEqual(availability.status_code, 200)
        payload = {'order_no': self.other.order_no, 'schedule_id': schedule.pk, 'device_id': self.device.pk, 'plan_start_time': '2026-12-01', 'plan_end_time': '2026-12-01', 'sample_arrived': True}
        self.assertEqual(self.action('dept', 'schedule_assign', **payload).status_code, 200)
        schedule.refresh_from_db()
        self.assertFalse(schedule.sample_arrived)
        self.assertEqual(schedule.scheduled_by, self.users['dept'])
        for action in ['start_test', 'sample_arrival']:
            self.assertEqual(self.action('dept', action, order_no=self.other.order_no, schedule_id=schedule.pk).status_code, 403)
        self.assertEqual(self.action('dept', 'sales_confirm', order_no=self.other.order_no).status_code, 410)

    def test_gm_routing_options_and_chairman_employee_role_whitelist(self):
        self.client.force_login(self.users['gm'])
        dashboard = self.client.get(reverse('lims_dashboard')).json()
        self.assertTrue(dashboard['routing_options']['suzhou_managers'])
        self.client.force_login(self.users['chair'])
        for role in ['商务', '技术', '商务评审', '技术评审']:
            response = self.client.post(reverse('add_employee'), {'username': 'retired', 'password': 'test-pass', 'role': role}, content_type='application/json')
            self.assertEqual(response.status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username='retired').exists())

    def test_department_can_create_order(self):
        self.client.force_login(self.users['dept'])
        response = self.client.post(reverse('create_order'), {
            'customer_name': '商务部下单测试', 'project_name': '角色下单',
            'test_requirements': '虚拟试验', 'expected_sample_arrival': '2026-12-01',
            'industry_category': 'other', 'execution_attributes': ['autonomous'],
        }, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(LabOrder.objects.filter(project_name='角色下单', sale_user=self.users['dept']).exists())

    def test_role_migration_preserves_users_and_historical_review_attribution(self):
        from importlib import import_module
        from django.apps import apps
        from .models import BusinessReview
        review = BusinessReview.objects.create(order=self.order, biz_review_user=self.users['oldbiz'], tech_review_user=self.users['oldtech'], review_result=True)
        import_module('core.migrations.0019_review_responsibilities').replace_roles(apps, None)
        self.assertFalse(Group.objects.filter(name__in=['商务', '技术']).exists())
        review.refresh_from_db()
        self.assertEqual(review.biz_review_user, self.users['oldbiz'])
        self.assertEqual(review.tech_review_user, self.users['oldtech'])
        self.assertTrue(get_user_model().objects.filter(pk=self.users['oldbiz'].pk).exists())
